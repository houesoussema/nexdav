import os
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP # Import FastMCP for building the MCP server
from caldav_service import CalDAVService # Import our CalDAV service logic
from datetime import datetime

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
    return await caldav_service.get_calendars()

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
    # Convert string dates to datetime objects for the CalDAV service
    s_date_obj = datetime.strptime(start_date, '%Y-%m-%d') if start_date else None
    e_date_obj = datetime.strptime(end_date, '%Y-%m-%d') if end_date else None
    return await caldav_service.get_events(calendar_url, s_date_obj, e_date_obj)

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
    return await caldav_service.create_event(calendar_url, ical_content)

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
    return await caldav_service.update_event(event_url, ical_content)

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
    return await caldav_service.delete_event(event_url)

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
    return await caldav_service.get_tasks(calendar_url, include_completed)

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
    return await caldav_service.create_task(calendar_url, ical_content)

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
    return await caldav_service.update_task(task_url, ical_content)

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
    return await caldav_service.delete_task(task_url)


# This block ensures the MCP server starts when the script is executed directly.
# The `transport="stdio"` tells the MCP server to communicate over standard input/output,
# which is how the `mcp-superassistant-proxy` will interact with it.
if __name__ == "__main__":
    print("Starting MCP CalDAV Server...")
    mcp.run(transport="stdio")
    print("MCP CalDAV Server stopped.") # This line will typically not be reached as the server runs indefinitely