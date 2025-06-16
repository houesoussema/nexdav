import os
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP # Import FastMCP for building the MCP server
from caldav_service import CalDAVService, CalDAVConnectionError # Import our CalDAV service logic
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

# Initialize CalDAVService with credentials retrieved from environment variables.
# It's crucial that CALDAV_URL, CALDAV_USERNAME, and CALDAV_PASSWORD are set
# in the .env file or as system environment variables.
caldav_service = CalDAVService(
    url=os.getenv("CALDAV_URL"),
    username=os.getenv("CALDAV_USERNAME"),
    password=os.getenv("CALDAV_PASSWORD")
)

# --- MCP Tool Definitions using @mcp.tool() decorators ---
# Each function decorated with @mcp.tool() becomes an accessible tool
# for Claude or any other MCP client. Type hints are important for MCP
# to correctly infer parameter types and provide helpful documentation.

@mcp.tool()
async def list_caldav_calendars() -> list:
    """
    Lists all available CalDAV calendars for the configured user.

    This tool connects to the CalDAV server and retrieves a list of all
    calendars the authenticated user has access to.

    Returns:
        list: A list of dictionaries, where each dictionary represents a calendar
              with 'name' (display name) and 'url'.
              Example: [{"name": "Personal Calendar", "url": "https://.../calendars/user/personal/"}]
    """
    logger.info("Tool 'list_caldav_calendars' called.")
    try:
        result = await caldav_service.get_calendars()
        logger.info("Successfully listed CalDAV calendars.")
        return result
    except CalDAVConnectionError as e:
        logger.error(f"CalDAV connection error in 'list_caldav_calendars': {str(e)}")
        return [{"status": "error", "message": f"CalDAV connection error: {str(e)}"}] # Adjusted to return list as per type hint
    except Exception as e:
        logger.exception("An unexpected error occurred in 'list_caldav_calendars'")
        return [{"status": "error", "message": f"An unexpected error occurred: {str(e)}"}]


@mcp.tool()
async def list_caldav_events(calendar_url: str, start_date: str = None, end_date: str = None) -> list:
    """
    Lists events from a specified CalDAV calendar within an optional date range.

    Args:
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
              Example: [{"url": "https://.../event1.ics", "data": "BEGIN:VCALENDAR..."}]
    """
    logger.info(f"Tool 'list_caldav_events' called for calendar: {calendar_url}, start: {start_date}, end: {end_date}")
    # Convert string dates to datetime objects for the CalDAV service
    s_date_obj = None
    if start_date:
        s_date_obj = datetime.strptime(start_date, '%Y-%m-%d').replace(tzinfo=pytz.UTC)

    e_date_obj = None
    if end_date:
        e_date_obj = datetime.strptime(end_date, '%Y-%m-%d').replace(tzinfo=pytz.UTC)

    try:
        result = await caldav_service.get_events(calendar_url, s_date_obj, e_date_obj)
        logger.info(f"Successfully listed events for calendar: {calendar_url}.")
        return result
    except CalDAVConnectionError as e:
        logger.error(f"CalDAV connection error in 'list_caldav_events' for calendar {calendar_url}: {str(e)}")
        return [{"status": "error", "message": f"CalDAV connection error: {str(e)}"}] # Adjusted for list type hint
    except Exception as e:
        logger.exception(f"An unexpected error occurred in 'list_caldav_events' for calendar {calendar_url}")
        return [{"status": "error", "message": f"An unexpected error occurred: {str(e)}"}]


@mcp.tool()
async def create_caldav_event(calendar_url: str, ical_content: str) -> dict:
    """
    Creates a new event in the specified CalDAV calendar using iCalendar (VCS) content.

    This tool expects the event details to be provided as a complete iCalendar string.
    Tools like Claude would typically construct this iCalendar string based on user input.

    Args:
        calendar_url (str): The absolute URL of the calendar where the event will be created.
                            This URL can be obtained from `list_caldav_calendars` tool output.
        ical_content (str): The full iCalendar (VCS) string for the event.
                            Example: "BEGIN:VCALENDAR...BEGIN:VEVENT...END:VEVENT...END:VCALENDAR"

    Returns:
        dict: A dictionary indicating the 'status' of the operation ('success')
              and the 'event_url' of the newly created event.
              Example: {"status": "success", "event_url": "https://.../new_event.ics"}
    """
    logger.info(f"Tool 'create_caldav_event' called for calendar: {calendar_url} with ical_content (length: {len(ical_content)})")
    try:
        Calendar.from_ical(ical_content) # Validate iCalendar content
    except ValueError as e: # Specific exception for icalendar parsing errors
        logger.error(f"Invalid iCalendar content in 'create_caldav_event': {str(e)}")
        return {"status": "error", "message": f"Invalid iCalendar content: {str(e)}"}

    try:
        result = await caldav_service.create_event(calendar_url, ical_content)
        logger.info(f"Successfully created event: {result.get('event_url')} in calendar: {calendar_url}")
        return result
    except CalDAVConnectionError as e:
        logger.error(f"CalDAV connection error in 'create_caldav_event': {str(e)}")
        return {"status": "error", "message": f"CalDAV connection error: {str(e)}"}
    except Exception as e:
        logger.exception("An unexpected error occurred in 'create_caldav_event'")
        return {"status": "error", "message": f"An unexpected error occurred: {str(e)}"}

@mcp.tool()
async def update_caldav_event(event_url: str, ical_content: str) -> dict:
    """
    Updates an existing CalDAV event with new iCalendar content.

    The event is identified by its unique URL. The provided iCalendar content
    will completely replace the existing event data.

    Args:
        event_url (str): The absolute URL of the event to be updated.
                         This URL can be obtained from `list_caldav_events` tool output.
        ical_content (str): The new full iCalendar (VCS) string for the event.

    Returns:
        dict: A dictionary indicating the 'status' of the operation ('success')
              and the 'event_url' of the updated event.
              Example: {"status": "success", "event_url": "https://.../updated_event.ics"}
    """
    logger.info(f"Tool 'update_caldav_event' called for event: {event_url} with ical_content (length: {len(ical_content)})")
    try:
        Calendar.from_ical(ical_content) # Validate iCalendar content
    except ValueError as e: # Specific exception for icalendar parsing errors
        logger.error(f"Invalid iCalendar content in 'update_caldav_event' for event {event_url}: {str(e)}")
        return {"status": "error", "message": f"Invalid iCalendar content: {str(e)}"}

    try:
        result = await caldav_service.update_event(event_url, ical_content)
        logger.info(f"Successfully updated event: {result.get('event_url')}")
        return result
    except CalDAVConnectionError as e:
        logger.error(f"CalDAV connection error in 'update_caldav_event' for event {event_url}: {str(e)}")
        return {"status": "error", "message": f"CalDAV connection error: {str(e)}"}
    except Exception as e:
        logger.exception(f"An unexpected error occurred in 'update_caldav_event' for event {event_url}")
        return {"status": "error", "message": f"An unexpected error occurred: {str(e)}"}

@mcp.tool()
async def delete_caldav_event(event_url: str) -> dict:
    """
    Deletes an event from the CalDAV server.

    The event to be deleted is identified by its unique URL.

    Args:
        event_url (str): The absolute URL of the event to be deleted.
                         This URL can be obtained from `list_caldav_events` tool output.

    Returns:
        dict: A dictionary indicating the 'status' of the operation ('success')
              and the 'event_url' that was deleted.
              Example: {"status": "success", "event_url": "https://.../deleted_event.ics"}
    """
    logger.info(f"Tool 'delete_caldav_event' called for event: {event_url}")
    try:
        result = await caldav_service.delete_event(event_url)
        logger.info(f"Successfully deleted event: {event_url}")
        return result
    except CalDAVConnectionError as e:
        logger.error(f"CalDAV connection error in 'delete_caldav_event' for event {event_url}: {str(e)}")
        return {"status": "error", "message": f"CalDAV connection error: {str(e)}"}
    except Exception as e:
        logger.exception(f"An unexpected error occurred in 'delete_caldav_event' for event {event_url}")
        return {"status": "error", "message": f"An unexpected error occurred: {str(e)}"}

# --- New Task (VTODO) Specific MCP Tools ---

@mcp.tool()
async def list_caldav_tasks(calendar_url: str, include_completed: bool = False) -> list:
    """
    Lists tasks (VTODOs) from a specified CalDAV calendar.

    Args:
        calendar_url (str): The absolute URL of the calendar to query tasks from.
                            This URL can be obtained from `list_caldav_calendars` tool output.
        include_completed (bool, optional): If True, completed tasks will be included in the results.
                                            Defaults to False (only incomplete tasks).

    Returns:
        list: A list of dictionaries, each representing a task with its 'url'
              and raw iCalendar 'data'. The 'data' field contains the full
              iCalendar (VCS) content of the task.
              Example: [{"url": "https://.../task1.ics", "data": "BEGIN:VCALENDAR...BEGIN:VTODO..."}]
    """
    logger.info(f"Tool 'list_caldav_tasks' called for calendar: {calendar_url}, include_completed: {include_completed}")
    try:
        result = await caldav_service.get_tasks(calendar_url, include_completed)
        logger.info(f"Successfully listed tasks for calendar: {calendar_url}.")
        return result
    except CalDAVConnectionError as e:
        logger.error(f"CalDAV connection error in 'list_caldav_tasks' for calendar {calendar_url}: {str(e)}")
        return [{"status": "error", "message": f"CalDAV connection error: {str(e)}"}] # Adjusted for list type hint
    except Exception as e:
        logger.exception(f"An unexpected error occurred in 'list_caldav_tasks' for calendar {calendar_url}")
        return [{"status": "error", "message": f"An unexpected error occurred: {str(e)}"}]


@mcp.tool()
async def create_caldav_task(calendar_url: str, ical_content: str) -> dict:
    """
    Creates a new task (VTODO) in the specified CalDAV calendar using iCalendar (VCS) content.

    This tool expects the task details to be provided as a complete iCalendar string
    containing a VTODO component.

    Args:
        calendar_url (str): The absolute URL of the calendar where the task will be created.
                            This URL can be obtained from `list_caldav_calendars` tool output.
        ical_content (str): The full iCalendar (VCS) string for the task.
                            Example: "BEGIN:VCALENDAR...BEGIN:VTODO...END:VTODO...END:VCALENDAR"

    Returns:
        dict: A dictionary indicating the 'status' of the operation ('success')
              and the 'task_url' of the newly created task.
              Example: {"status": "success", "task_url": "https://.../new_task.ics"}
    """
    logger.info(f"Tool 'create_caldav_task' called for calendar: {calendar_url} with ical_content (length: {len(ical_content)})")
    try:
        Calendar.from_ical(ical_content) # Validate iCalendar content
    except ValueError as e: # Specific exception for icalendar parsing errors
        logger.error(f"Invalid iCalendar content in 'create_caldav_task': {str(e)}")
        return {"status": "error", "message": f"Invalid iCalendar content: {str(e)}"}

    try:
        result = await caldav_service.create_task(calendar_url, ical_content)
        logger.info(f"Successfully created task: {result.get('task_url')} in calendar: {calendar_url}")
        return result
    except CalDAVConnectionError as e:
        logger.error(f"CalDAV connection error in 'create_caldav_task': {str(e)}")
        return {"status": "error", "message": f"CalDAV connection error: {str(e)}"}
    except Exception as e:
        logger.exception("An unexpected error occurred in 'create_caldav_task'")
        return {"status": "error", "message": f"An unexpected error occurred: {str(e)}"}

@mcp.tool()
async def update_caldav_task(task_url: str, ical_content: str) -> dict:
    """
    Updates an existing CalDAV task (VTODO) with new iCalendar content.

    The task is identified by its unique URL. The provided iCalendar content
    will completely replace the existing task data.

    Args:
        task_url (str): The absolute URL of the task to be updated.
                        This URL can be obtained from `list_caldav_tasks` tool output.
        ical_content (str): The new full iCalendar (VCS) string for the task.

    Returns:
        dict: A dictionary indicating the 'status' of the operation ('success')
              and the 'task_url' of the updated task.
              Example: {"status": "success", "task_url": "https://.../updated_task.ics"}
    """
    logger.info(f"Tool 'update_caldav_task' called for task: {task_url} with ical_content (length: {len(ical_content)})")
    try:
        Calendar.from_ical(ical_content) # Validate iCalendar content
    except ValueError as e: # Specific exception for icalendar parsing errors
        logger.error(f"Invalid iCalendar content in 'update_caldav_task' for task {task_url}: {str(e)}")
        return {"status": "error", "message": f"Invalid iCalendar content: {str(e)}"}

    try:
        result = await caldav_service.update_task(task_url, ical_content)
        logger.info(f"Successfully updated task: {result.get('task_url')}")
        return result
    except CalDAVConnectionError as e:
        logger.error(f"CalDAV connection error in 'update_caldav_task' for task {task_url}: {str(e)}")
        return {"status": "error", "message": f"CalDAV connection error: {str(e)}"}
    except Exception as e:
        logger.exception(f"An unexpected error occurred in 'update_caldav_task' for task {task_url}")
        return {"status": "error", "message": f"An unexpected error occurred: {str(e)}"}

@mcp.tool()
async def delete_caldav_task(task_url: str) -> dict:
    """
    Deletes a task (VTODO) from the CalDAV server.

    The task to be deleted is identified by its unique URL.

    Args:
        task_url (str): The absolute URL of the task to be deleted.
                        This URL can be obtained from `list_caldav_tasks` tool output.

    Returns:
        dict: A dictionary indicating the 'status' of the operation ('success')
              and the 'task_url' that was deleted.
              Example: {"status": "success", "task_url": "https://.../deleted_task.ics"}
    """
    logger.info(f"Tool 'delete_caldav_task' called for task: {task_url}")
    try:
        result = await caldav_service.delete_task(task_url)
        logger.info(f"Successfully deleted task: {task_url}")
        return result
    except CalDAVConnectionError as e:
        logger.error(f"CalDAV connection error in 'delete_caldav_task' for task {task_url}: {str(e)}")
        return {"status": "error", "message": f"CalDAV connection error: {str(e)}"}
    except Exception as e:
        logger.exception(f"An unexpected error occurred in 'delete_caldav_task' for task {task_url}")
        return {"status": "error", "message": f"An unexpected error occurred: {str(e)}"}


# This block ensures the MCP server starts when the script is executed directly.
# The `transport="stdio"` tells the MCP server to communicate over standard input/output,
# which is how the `mcp-superassistant-proxy` will interact with it.
if __name__ == "__main__":
    logger.info("Starting MCP CalDAV Server...")
    mcp.run(transport="stdio")
    logger.info("MCP CalDAV Server stopped.") # This line will typically not be reached as the server runs indefinitely