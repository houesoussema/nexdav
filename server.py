import os
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP # Import FastMCP for building the MCP server
from caldav_service import CalDAVService, CalDAVConnectionError # Import our CalDAV service logic
import json # For parsing CALDAV_ACCOUNTS
from datetime import datetime
import pytz # Import pytz for timezone handling
from icalendar import Calendar # For iCalendar parsing
import logging

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    handlers=[logging.StreamHandler()] # Log to stdout
)
logger = logging.getLogger(__name__)

# Load environment variables from a .env file.
# This allows sensitive information (like URLs, usernames, passwords)
# to be kept out of the codebase and managed securely.
load_dotenv()

# Instantiate an MCP server client.
# This names our server, which will be visible to tools that interact with it.
mcp = FastMCP("CalDAV Nextcloud Integration")

# Initialize CalDAVService instances from CALDAV_ACCOUNTS environment variable
caldav_services_map: dict[str, CalDAVService] = {}
try:
    accounts_json = os.getenv("CALDAV_ACCOUNTS", "[]")
    accounts_config = json.loads(accounts_json)
    if not isinstance(accounts_config, list):
        logger.error("CALDAV_ACCOUNTS is not a list. Initializing with no accounts.")
        accounts_config = []

    for account in accounts_config:
        if isinstance(account, dict) and "url" in account and "username" in account and "password" in account:
            service = CalDAVService(
                url=account["url"],
                username=account["username"],
                password=account["password"]
            )
            if account["url"] in caldav_services_map:
                logger.warning(f"Duplicate CalDAV account URL found: {account['url']}. Overwriting previous entry.")
            caldav_services_map[account["url"]] = service
            logger.info(f"Successfully initialized CalDAV service for account URL: {account['url']}")
        else:
            logger.error(f"Invalid account configuration found: {account}. Skipping.")
except json.JSONDecodeError as e:
    logger.error(f"Failed to parse CALDAV_ACCOUNTS JSON: {str(e)}. Initializing with no accounts.")
    caldav_services_map = {} # Ensure it's empty on error
except Exception as e:
    logger.error(f"An unexpected error occurred during CalDAV services initialization: {str(e)}. Initializing with no accounts.")
    caldav_services_map = {} # Ensure it's empty on error

if not caldav_services_map:
    logger.warning("No CalDAV accounts configured or all configurations failed. CalDAV tools may not function as expected.")

# --- MCP Tool Definitions using @mcp.tool() decorators ---
# Each function decorated with @mcp.tool() becomes an accessible tool
# for Claude or any other MCP client. Type hints are important for MCP
# to correctly infer parameter types and provide helpful documentation.

@mcp.tool()
async def list_caldav_calendars() -> list:
    """
    Lists all available CalDAV calendars from all configured accounts.

    This tool connects to each configured CalDAV server and retrieves a list of
    calendars the authenticated user for that account has access to.
    Each calendar dictionary in the returned list will include an 'account_identifier'
    key, which is the URL of the CalDAV account it belongs to.

    Returns:
        list: A list of dictionaries, where each dictionary represents a calendar
              with 'name' (display name), 'url', and 'account_identifier'.
              Example: [{"name": "Personal Calendar", "url": "https://.../personal/", "account_identifier": "https://your-caldav-server.com/dav/"}]
              Returns an empty list if no accounts are configured or no calendars are found.
              Individual account connection errors are logged but do not stop other accounts from being processed.
    """
    logger.info("Tool 'list_caldav_calendars' called.")
    if not caldav_services_map:
        logger.warning("No CalDAV accounts configured. Returning empty list for calendars.")
        return []

    all_calendars = []
    for account_url, service_instance in caldav_services_map.items():
        try:
            logger.info(f"Fetching calendars for account: {account_url}")
            calendars = await service_instance.get_calendars()
            for calendar in calendars:
                calendar['account_identifier'] = account_url # Add account identifier
            all_calendars.extend(calendars)
            logger.info(f"Successfully listed {len(calendars)} calendars for account: {account_url}")
        except CalDAVConnectionError as e:
            logger.error(f"CalDAV connection error for account {account_url} in 'list_caldav_calendars': {str(e)}")
            # Optionally, include error information in the response if needed, for now, just log and continue.
        except Exception as e:
            logger.exception(f"An unexpected error occurred for account {account_url} in 'list_caldav_calendars'")
            # Optionally, include error information for this account.

    if not all_calendars:
        logger.info("No calendars found across all configured accounts.")
    return all_calendars


@mcp.tool()
async def list_caldav_events(account_identifier: str, calendar_url: str, start_date: str = None, end_date: str = None) -> list:
    """
    Lists events from a specified CalDAV calendar of a specific account, within an optional date range.

    Args:
        account_identifier (str): The URL of the CalDAV account (serves as its identifier).
        calendar_url (str): The absolute URL of the calendar to query events from.
                            This URL can be obtained from `list_caldav_calendars` tool output.
        start_date (str, optional): The start date for the event search in 'YYYY-MM-DD' format.
                                    If not provided, defaults to 30 days ago from the current date.
        end_date (str, optional): The end date for the event search in 'YYYY-MM-DD' format.
                                  If not provided, defaults to 1 year from the current date.

    Returns:
        list: A list of dictionaries, each representing an event with its 'url'
              and raw iCalendar 'data'. The 'data' field contains the full
              iCalendar (VCS) content of the event.
              Returns an error structure if the account_identifier is invalid.
              Example: [{"url": "https://.../event1.ics", "data": "BEGIN:VCALENDAR..."}]
    """
    logger.info(f"Tool 'list_caldav_events' called for account: {account_identifier}, calendar: {calendar_url}, start: {start_date}, end: {end_date}")
    service = caldav_services_map.get(account_identifier)
    if not service:
        logger.error(f"Account identifier '{account_identifier}' not found in configured services for 'list_caldav_events'.")
        return [{"status": "error", "message": f"Account identifier '{account_identifier}' not found."}]

    s_date_obj = None
    if start_date:
        s_date_obj = datetime.strptime(start_date, '%Y-%m-%d').replace(tzinfo=pytz.UTC)

    e_date_obj = None
    if end_date:
        e_date_obj = datetime.strptime(end_date, '%Y-%m-%d').replace(tzinfo=pytz.UTC)

    try:
        result = await service.get_events(calendar_url, s_date_obj, e_date_obj)
        logger.info(f"Successfully listed events for account {account_identifier}, calendar: {calendar_url}.")
        return result
    except CalDAVConnectionError as e:
        logger.error(f"CalDAV connection error for account {account_identifier} in 'list_caldav_events' for calendar {calendar_url}: {str(e)}")
        return [{"status": "error", "message": f"CalDAV connection error for account {account_identifier}: {str(e)}"}]
    except Exception as e:
        logger.exception(f"An unexpected error occurred for account {account_identifier} in 'list_caldav_events' for calendar {calendar_url}")
        return [{"status": "error", "message": f"An unexpected error occurred for account {account_identifier}: {str(e)}"}]


@mcp.tool()
async def create_caldav_event(account_identifier: str, calendar_url: str, ical_content: str, reminder_minutes_before: int = None, reminder_description: str = None) -> dict:
    """
    Creates a new event in the specified CalDAV calendar of a specific account using iCalendar (VCS) content.

    Args:
        account_identifier (str): The URL of the CalDAV account (serves as its identifier).
        calendar_url (str): The absolute URL of the calendar where the event will be created.
        ical_content (str): The full iCalendar (VCS) string for the event.
        reminder_minutes_before (int, optional): Minutes before the event start to trigger a reminder. Defaults to None (no reminder).
        reminder_description (str, optional): Description for the reminder. Defaults to None.

    Returns:
        dict: A dictionary indicating the 'status' of the operation ('success')
              and the 'event_url' of the newly created event.
              Returns an error structure if the account_identifier is invalid.
    """
    logger.info(f"Tool 'create_caldav_event' called for account: {account_identifier}, calendar: {calendar_url}, reminder_minutes_before: {reminder_minutes_before}, reminder_description: {reminder_description} with ical_content (length: {len(ical_content)})")
    service = caldav_services_map.get(account_identifier)
    if not service:
        logger.error(f"Account identifier '{account_identifier}' not found in configured services for 'create_caldav_event'.")
        return {"status": "error", "message": f"Account identifier '{account_identifier}' not found."}

    try:
        Calendar.from_ical(ical_content) # Validate iCalendar content
    except ValueError as e:
        logger.error(f"Invalid iCalendar content for account {account_identifier} in 'create_caldav_event': {str(e)}")
        return {"status": "error", "message": f"Invalid iCalendar content: {str(e)}"}

    try:
        result = await service.create_event(
            calendar_url,
            ical_content,
            reminder_minutes_before=reminder_minutes_before,
            reminder_description=reminder_description
        )
        logger.info(f"Successfully created event for account {account_identifier}: {result.get('event_url')} in calendar: {calendar_url}")
        return result
    except CalDAVConnectionError as e:
        logger.error(f"CalDAV connection error for account {account_identifier} in 'create_caldav_event': {str(e)}")
        return {"status": "error", "message": f"CalDAV connection error for account {account_identifier}: {str(e)}"}
    except Exception as e:
        logger.exception(f"An unexpected error occurred for account {account_identifier} in 'create_caldav_event'")
        return {"status": "error", "message": f"An unexpected error occurred for account {account_identifier}: {str(e)}"}

@mcp.tool()
async def update_caldav_event(account_identifier: str, event_url: str, ical_content: str = None, reminder_minutes_before: int = None, reminder_description: str = None) -> dict:
    """
    Updates an existing CalDAV event in a specific account with new iCalendar content and/or reminder settings.

    Args:
        account_identifier (str): The URL of the CalDAV account (serves as its identifier).
        event_url (str): The absolute URL of the event to be updated.
        ical_content (str, optional): The new full iCalendar (VCS) string for the event.
                                      If None, only reminder settings will be updated based on existing event data.
        reminder_minutes_before (int, optional): Minutes before the event start to trigger a reminder.
                                                 Set to 0 or None to remove existing reminders. Defaults to None.
        reminder_description (str, optional): Description for the reminder. Defaults to None.


    Returns:
        dict: A dictionary indicating the 'status' of the operation ('success')
              and the 'event_url' of the updated event.
              Returns an error structure if the account_identifier is invalid.
    """
    logger.info(f"Tool 'update_caldav_event' called for account: {account_identifier}, event: {event_url}, reminder_minutes_before: {reminder_minutes_before}, reminder_description: {reminder_description} with ical_content (length: {len(ical_content) if ical_content else 'None'})")
    service = caldav_services_map.get(account_identifier)
    if not service:
        logger.error(f"Account identifier '{account_identifier}' not found in configured services for 'update_caldav_event'.")
        return {"status": "error", "message": f"Account identifier '{account_identifier}' not found."}

    if ical_content: # Validate iCalendar content only if provided
        try:
            Calendar.from_ical(ical_content)
        except ValueError as e:
            logger.error(f"Invalid iCalendar content for account {account_identifier} in 'update_caldav_event' for event {event_url}: {str(e)}")
            return {"status": "error", "message": f"Invalid iCalendar content: {str(e)}"}

    try:
        result = await service.update_event(
            event_url,
            ical_content=ical_content,
            reminder_minutes_before=reminder_minutes_before,
            reminder_description=reminder_description
        )
        logger.info(f"Successfully updated event for account {account_identifier}: {result.get('event_url')}")
        return result
    except CalDAVConnectionError as e:
        logger.error(f"CalDAV connection error for account {account_identifier} in 'update_caldav_event' for event {event_url}: {str(e)}")
        return {"status": "error", "message": f"CalDAV connection error for account {account_identifier}: {str(e)}"}
    except Exception as e:
        logger.exception(f"An unexpected error occurred for account {account_identifier} in 'update_caldav_event' for event {event_url}")
        return {"status": "error", "message": f"An unexpected error occurred for account {account_identifier}: {str(e)}"}

@mcp.tool()
async def delete_caldav_event(account_identifier: str, event_url: str) -> dict:
    """
    Deletes an event from a specific CalDAV account's server.

    Args:
        account_identifier (str): The URL of the CalDAV account (serves as its identifier).
        event_url (str): The absolute URL of the event to be deleted.

    Returns:
        dict: A dictionary indicating the 'status' of the operation ('success')
              and the 'event_url' that was deleted.
              Returns an error structure if the account_identifier is invalid.
    """
    logger.info(f"Tool 'delete_caldav_event' called for account: {account_identifier}, event: {event_url}")
    service = caldav_services_map.get(account_identifier)
    if not service:
        logger.error(f"Account identifier '{account_identifier}' not found in configured services for 'delete_caldav_event'.")
        return {"status": "error", "message": f"Account identifier '{account_identifier}' not found."}

    try:
        result = await service.delete_event(event_url)
        logger.info(f"Successfully deleted event for account {account_identifier}: {event_url}")
        return result
    except CalDAVConnectionError as e:
        logger.error(f"CalDAV connection error for account {account_identifier} in 'delete_caldav_event' for event {event_url}: {str(e)}")
        return {"status": "error", "message": f"CalDAV connection error for account {account_identifier}: {str(e)}"}
    except Exception as e:
        logger.exception(f"An unexpected error occurred for account {account_identifier} in 'delete_caldav_event' for event {event_url}")
        return {"status": "error", "message": f"An unexpected error occurred for account {account_identifier}: {str(e)}"}

# --- New Task (VTODO) Specific MCP Tools ---

@mcp.tool()
async def list_caldav_tasks(account_identifier: str, calendar_url: str, include_completed: bool = False) -> list:
    """
    Lists tasks (VTODOs) from a specified CalDAV calendar of a specific account.

    Args:
        account_identifier (str): The URL of the CalDAV account (serves as its identifier).
        calendar_url (str): The absolute URL of the calendar to query tasks from.
        include_completed (bool, optional): If True, completed tasks will be included. Defaults to False.

    Returns:
        list: A list of dictionaries, each representing a task with 'url' and 'data'.
              Returns an error structure if the account_identifier is invalid.
    """
    logger.info(f"Tool 'list_caldav_tasks' called for account: {account_identifier}, calendar: {calendar_url}, include_completed: {include_completed}")
    service = caldav_services_map.get(account_identifier)
    if not service:
        logger.error(f"Account identifier '{account_identifier}' not found for 'list_caldav_tasks'.")
        return [{"status": "error", "message": f"Account identifier '{account_identifier}' not found."}]

    try:
        result = await service.get_tasks(calendar_url, include_completed)
        logger.info(f"Successfully listed tasks for account {account_identifier}, calendar: {calendar_url}.")
        return result
    except CalDAVConnectionError as e:
        logger.error(f"CalDAV connection error for account {account_identifier} in 'list_caldav_tasks' for calendar {calendar_url}: {str(e)}")
        return [{"status": "error", "message": f"CalDAV connection error for account {account_identifier}: {str(e)}"}]
    except Exception as e:
        logger.exception(f"An unexpected error for account {account_identifier} in 'list_caldav_tasks' for calendar {calendar_url}")
        return [{"status": "error", "message": f"An unexpected error for account {account_identifier}: {str(e)}"}]


@mcp.tool()
async def create_caldav_task(account_identifier: str, calendar_url: str, ical_content: str) -> dict:
    """
    Creates a new task (VTODO) in a specified CalDAV calendar of a specific account.

    Args:
        account_identifier (str): The URL of the CalDAV account (serves as its identifier).
        calendar_url (str): The URL of the calendar where the task will be created.
        ical_content (str): The iCalendar (VCS) string for the task.

    Returns:
        dict: Status of operation and 'task_url' of the new task.
              Returns an error structure if the account_identifier is invalid.
    """
    logger.info(f"Tool 'create_caldav_task' called for account: {account_identifier}, calendar: {calendar_url} with ical_content (length: {len(ical_content)})")
    service = caldav_services_map.get(account_identifier)
    if not service:
        logger.error(f"Account identifier '{account_identifier}' not found for 'create_caldav_task'.")
        return {"status": "error", "message": f"Account identifier '{account_identifier}' not found."}

    try:
        Calendar.from_ical(ical_content) # Validate iCalendar content
    except ValueError as e:
        logger.error(f"Invalid iCalendar content for account {account_identifier} in 'create_caldav_task': {str(e)}")
        return {"status": "error", "message": f"Invalid iCalendar content: {str(e)}"}

    try:
        result = await service.create_task(calendar_url, ical_content)
        logger.info(f"Successfully created task for account {account_identifier}: {result.get('task_url')} in calendar: {calendar_url}")
        return result
    except CalDAVConnectionError as e:
        logger.error(f"CalDAV connection error for account {account_identifier} in 'create_caldav_task': {str(e)}")
        return {"status": "error", "message": f"CalDAV connection error for account {account_identifier}: {str(e)}"}
    except Exception as e:
        logger.exception(f"An unexpected error for account {account_identifier} in 'create_caldav_task'")
        return {"status": "error", "message": f"An unexpected error for account {account_identifier}: {str(e)}"}

@mcp.tool()
async def update_caldav_task(account_identifier: str, task_url: str, ical_content: str) -> dict:
    """
    Updates an existing CalDAV task (VTODO) in a specific account.

    Args:
        account_identifier (str): The URL of the CalDAV account (serves as its identifier).
        task_url (str): The URL of the task to be updated.
        ical_content (str): The new iCalendar (VCS) string for the task.

    Returns:
        dict: Status of operation and 'task_url' of the updated task.
              Returns an error structure if the account_identifier is invalid.
    """
    logger.info(f"Tool 'update_caldav_task' called for account: {account_identifier}, task: {task_url} with ical_content (length: {len(ical_content)})")
    service = caldav_services_map.get(account_identifier)
    if not service:
        logger.error(f"Account identifier '{account_identifier}' not found for 'update_caldav_task'.")
        return {"status": "error", "message": f"Account identifier '{account_identifier}' not found."}

    try:
        Calendar.from_ical(ical_content) # Validate iCalendar content
    except ValueError as e:
        logger.error(f"Invalid iCalendar content for account {account_identifier} in 'update_caldav_task' for task {task_url}: {str(e)}")
        return {"status": "error", "message": f"Invalid iCalendar content: {str(e)}"}

    try:
        result = await service.update_task(task_url, ical_content)
        logger.info(f"Successfully updated task for account {account_identifier}: {result.get('task_url')}")
        return result
    except CalDAVConnectionError as e:
        logger.error(f"CalDAV connection error for account {account_identifier} in 'update_caldav_task' for task {task_url}: {str(e)}")
        return {"status": "error", "message": f"CalDAV connection error for account {account_identifier}: {str(e)}"}
    except Exception as e:
        logger.exception(f"An unexpected error for account {account_identifier} in 'update_caldav_task' for task {task_url}")
        return {"status": "error", "message": f"An unexpected error for account {account_identifier}: {str(e)}"}

@mcp.tool()
async def delete_caldav_task(account_identifier: str, task_url: str) -> dict:
    """
    Deletes a task (VTODO) from a specific CalDAV account's server.

    Args:
        account_identifier (str): The URL of the CalDAV account (serves as its identifier).
        task_url (str): The URL of the task to be deleted.

    Returns:
        dict: Status of operation and 'task_url' that was deleted.
              Returns an error structure if the account_identifier is invalid.
    """
    logger.info(f"Tool 'delete_caldav_task' called for account: {account_identifier}, task: {task_url}")
    service = caldav_services_map.get(account_identifier)
    if not service:
        logger.error(f"Account identifier '{account_identifier}' not found for 'delete_caldav_task'.")
        return {"status": "error", "message": f"Account identifier '{account_identifier}' not found."}

    try:
        result = await service.delete_task(task_url)
        logger.info(f"Successfully deleted task for account {account_identifier}: {task_url}")
        return result
    except CalDAVConnectionError as e:
        logger.error(f"CalDAV connection error for account {account_identifier} in 'delete_caldav_task' for task {task_url}: {str(e)}")
        return {"status": "error", "message": f"CalDAV connection error for account {account_identifier}: {str(e)}"}
    except Exception as e:
        logger.exception(f"An unexpected error for account {account_identifier} in 'delete_caldav_task' for task {task_url}")
        return {"status": "error", "message": f"An unexpected error for account {account_identifier}: {str(e)}"}


# This block ensures the MCP server starts when the script is executed directly.
# The `transport="stdio"` tells the MCP server to communicate over standard input/output,
# which is how the `mcp-superassistant-proxy` will interact with it.
if __name__ == "__main__":
    logger.info("Starting MCP CalDAV Server...")
    mcp.run(transport="stdio")
    logger.info("MCP CalDAV Server stopped.") # This line will typically not be reached as the server runs indefinitely