import caldav
from caldav.elements import dav
from caldav.lib.error import AuthorizationError as CalDAVAuthorizationError # Renamed to avoid conflict
from datetime import datetime, date, timedelta
import pytz # For timezone handling
import requests # For requests.exceptions.ConnectionError
from icalendar import Calendar # For parsing iCalendar data
import logging
import asyncio

logger = logging.getLogger(__name__)

# Custom exception for CalDAV connection errors
class CalDAVConnectionError(Exception):
    """Custom exception for errors during CalDAV server connection or authentication."""
    pass

class CalDAVService:
    """
    Service class for interacting with a CalDAV server (e.g., Nextcloud Calendar).
    It handles connection, authentication, and various calendar and task operations.
    """
    def __init__(self, url, username, password):
        """
        Initializes the CalDAVService with server credentials.

        Args:
            url (str): The base URL of the CalDAV server.
            username (str): The username for authentication.
            password (str): The password (or app password) for authentication.
        """
        self.url = url
        self.username = username
        self.password = password
        self.client = None
        self.principal = None

    async def connect(self):
        """
        Establishes a connection to the CalDAV server and retrieves the principal.
        Raises CalDAVConnectionError if connection or authentication fails.
        """
        logger.info(f"Attempting to connect to CalDAV server at {self.url} for user {self.username}...")
        try:
            self.client = caldav.DAVClient(
                url=self.url,
                username=self.username,
                password=self.password
            )
            # Wrap the synchronous call in asyncio.to_thread
            self.principal = await asyncio.to_thread(self.client.principal)
            logger.info("Successfully connected to CalDAV server and fetched principal.")
        except requests.exceptions.ConnectionError as e:
            logger.error(f"CalDAV connection failed for {self.url}: {e}")
            raise CalDAVConnectionError(f"Connection to CalDAV server failed: {e}")
        except CalDAVAuthorizationError as e:
            logger.error(f"CalDAV authentication failed for user {self.username} at {self.url}: {e}")
            raise CalDAVConnectionError(f"Authentication failed for CalDAV server: {e}")
        except Exception as e:
            logger.error(f"An unexpected error occurred during CalDAV connection for {self.url}: {e}", exc_info=True)
            raise CalDAVConnectionError(f"An unexpected error occurred during CalDAV connection: {e}")

    async def get_calendars(self):
        """
        Retrieves a list of all calendars accessible by the authenticated user.

        Returns:
            list: A list of dictionaries, where each dictionary represents a calendar
                  with 'name' (display name) and 'url'.
        """
        if not self.principal:
            await self.connect()
        logger.info("Fetching calendars...")
        # Wrap the synchronous call in asyncio.to_thread
        calendars_raw = await asyncio.to_thread(self.principal.calendars)

        calendars_list = []
        for cal_obj in calendars_raw:
            # Wrap the synchronous call in asyncio.to_thread
            display_name = await asyncio.to_thread(cal_obj.get_property, dav.DisplayName())
            calendars_list.append({"name": display_name, "url": str(cal_obj.url)})

        logger.info(f"Found {len(calendars_list)} calendars.")
        return calendars_list

    async def get_events(self, calendar_url: str, start_date: datetime = None, end_date: datetime = None):
        """
        Retrieves events from a specified calendar within a given date range.

        Args:
            calendar_url (str): The URL of the calendar to fetch events from.
            start_date (datetime, optional): The start datetime for the event search.
                                            If None, defaults to 30 days ago.
            end_date (datetime, optional): The end datetime for the event search.
                                          If None, defaults to 1 year from now.

        Returns:
            list: A list of dictionaries, each representing an event with its 'url'
                  and raw iCalendar 'data'.
        """
        if not self.principal:
            await self.connect()
        logger.info(f"Fetching events for calendar: {calendar_url}, start: {start_date}, end: {end_date}")
        
        # Get the specific calendar object by its URL
        # Wrap the synchronous call in asyncio.to_thread
        calendar_obj = await asyncio.to_thread(self.client.calendar, url=calendar_url)
        
        # Set default date ranges if not provided
        now = datetime.now(pytz.utc)
        if not start_date:
            start_date = now - timedelta(days=30) # Default: last 30 days
        if not end_date:
            end_date = now + timedelta(days=365) # Default: next year

        # Perform a date-range search for events
        # Wrap the synchronous call in asyncio.to_thread
        events_raw = await asyncio.to_thread(calendar_obj.date_search, start=start_date, end=end_date)
        
        event_list = []
        for event_obj in events_raw: # Renamed to avoid confusion if event was a var name
            event_list.append({"url": str(event_obj.url), "data": event_obj.data})
        logger.info(f"Found {len(event_list)} events for calendar: {calendar_url}.")
        return event_list

    async def create_event(self, calendar_url: str, ical_content: str):
        """
        Creates a new event in the specified calendar using iCalendar content.

        Args:
            calendar_url (str): The URL of the calendar where the event will be created.
            ical_content (str): The full iCalendar (VCS) string of the event.

        Returns:
            dict: A dictionary indicating the 'status' of the operation and the
                  'event_url' of the newly created event.
        """
        if not self.principal:
            await self.connect()
        logger.info(f"Attempting to create event in calendar: {calendar_url}")
        calendar_obj = await asyncio.to_thread(self.client.calendar, url=calendar_url)
        # Wrap the synchronous call in asyncio.to_thread
        event = await asyncio.to_thread(calendar_obj.save_event, ical=ical_content)
        logger.info(f"Successfully created event: {str(event.url)} in calendar: {calendar_url}")
        return {"status": "success", "event_url": str(event.url)}

    async def update_event(self, event_url: str, ical_content: str):
        """
        Updates an existing event with new iCalendar content.

        Args:
            event_url (str): The URL of the event to be updated.
            ical_content (str): The new full iCalendar (VCS) string for the event.

        Returns:
            dict: A dictionary indicating the 'status' of the operation and the
                  'event_url' of the updated event.
        """
        if not self.principal:
            await self.connect()
        logger.info(f"Attempting to update event at URL: {event_url}")
        event_obj = await asyncio.to_thread(self.client.event, url=event_url)
        event_obj.data = ical_content # This is a local assignment
        # Wrap the synchronous call in asyncio.to_thread
        await asyncio.to_thread(event_obj.save)
        logger.info(f"Successfully updated event: {str(event_obj.url)}") # Use event_obj.url
        return {"status": "success", "event_url": str(event_obj.url)} # Use event_obj.url

    async def delete_event(self, event_url: str):
        """
        Deletes an event from the CalDAV server.

        Args:
            event_url (str): The URL of the event to be deleted.

        Returns:
            dict: A dictionary indicating the 'status' of the operation and the
                  'event_url' that was deleted.
        """
        if not self.principal:
            await self.connect()
        logger.info(f"Attempting to delete event at URL: {event_url}")
        event_obj = await asyncio.to_thread(self.client.event, url=event_url)
        # Wrap the synchronous call in asyncio.to_thread
        await asyncio.to_thread(event_obj.delete)
        logger.info(f"Successfully deleted event: {event_url}")
        return {"status": "success", "event_url": event_url}

    # --- Task (VTODO) Specific Methods ---

    async def get_tasks(self, calendar_url: str, include_completed: bool = False):
        """
        Retrieves tasks (VTODOs) from a specified calendar.

        Args:
            calendar_url (str): The URL of the calendar to fetch tasks from.
            include_completed (bool): Whether to include completed tasks. Defaults to False.

        Returns:
            list: A list of dictionaries, each representing a task with its 'url'
                  and raw iCalendar 'data'.
        """
        if not self.principal:
            await self.connect()
        logger.info(f"Fetching tasks for calendar: {calendar_url}, include_completed: {include_completed}")
        
        # Wrap the synchronous call in asyncio.to_thread
        calendar_obj = await asyncio.to_thread(self.client.calendar, url=calendar_url)
        # Wrap the synchronous call in asyncio.to_thread
        tasks_raw = await asyncio.to_thread(calendar_obj.todos)

        task_list = []
        for task_obj in tasks_raw: # task_obj is a caldav Task object
            if not include_completed:
                try:
                    cal = Calendar.from_ical(task_obj.data)
                    is_completed = False
                    for component in cal.walk():
                        if component.name == 'VTODO':
                            status = component.get('status')
                            if status and str(status).upper() == 'COMPLETED':
                                is_completed = True
                                break # Found VTODO and it's completed
                    if is_completed:
                        continue # Skip this task
                except ValueError:
                    logger.warning(f"Could not parse task data for URL {task_obj.url}. Skipping.", exc_info=True)
                    pass # Skip tasks that can't be parsed if filtering for completed status

            task_list.append({"url": str(task_obj.url), "data": task_obj.data})
        logger.info(f"Found {len(task_list)} tasks for calendar: {calendar_url}.")
        return task_list

    async def create_task(self, calendar_url: str, ical_content: str):
        """
        Creates a new task (VTODO) in the specified calendar using iCalendar content.

        Args:
            calendar_url (str): The URL of the calendar where the task will be created.
            ical_content (str): The full iCalendar (VCS) string of the task (VTODO).

        Returns:
            dict: A dictionary indicating the 'status' of the operation and the
                  'task_url' of the newly created task.
        """
        if not self.principal:
            await self.connect()
        logger.info(f"Attempting to create task in calendar: {calendar_url}")
        calendar_obj = await asyncio.to_thread(self.client.calendar, url=calendar_url)
        # The save_todo method is typically used for VTODOs
        # Wrap the synchronous call in asyncio.to_thread
        task = await asyncio.to_thread(calendar_obj.save_todo, ical=ical_content)
        logger.info(f"Successfully created task: {str(task.url)} in calendar: {calendar_url}")
        return {"status": "success", "task_url": str(task.url)}

    async def update_task(self, task_url: str, ical_content: str):
        """
        Updates an existing task (VTODO) with new iCalendar content.

        Args:
            task_url (str): The URL of the task to be updated.
            ical_content (str): The new full iCalendar (VCS) string for the task.

        Returns:
            dict: A dictionary indicating the 'status' of the operation and the
                  'task_url' of the updated task.
        """
        if not self.principal:
            await self.connect()
        logger.info(f"Attempting to update task at URL: {task_url}")
        # Fetch the object by URL
        task_obj = await asyncio.to_thread(self.client.object_by_url, url=task_url)

        # Check if the task object was found
        if task_obj is None:
            logger.error(f"Task not found at URL: {task_url}")
            raise ValueError(f"Task not found at URL: {task_url}")

        # Check if the fetched object is a VTODO task
        # Accessing the iCalendar component name, common in caldav libraries
        if not hasattr(task_obj, 'obj') or task_obj.obj.name != "VTODO":
            logger.error(f"Object at URL {task_url} is not a VTODO task. Object: {task_obj}")
            raise ValueError(f"Object at URL {task_obj.url if hasattr(task_obj, 'url') else task_url} is not a VTODO task.")

        task_obj.data = ical_content # Local assignment
        # Wrap the synchronous call in asyncio.to_thread
        await asyncio.to_thread(task_obj.save)
        logger.info(f"Successfully updated task: {str(task_obj.url)}") # Use task_obj.url
        return {"status": "success", "task_url": str(task_obj.url)} # Use task_obj.url

    async def delete_task(self, task_url: str):
        """
        Deletes a task (VTODO) from the CalDAV server.

        Args:
            task_url (str): The URL of the task to be deleted.

        Returns:
            dict: A dictionary indicating the 'status' of the operation and the
                  'task_url' that was deleted.
        """
        if not self.principal:
            await self.connect()
        logger.info(f"Attempting to delete task at URL: {task_url}")
        # Fetch the object by URL
        task_obj = await asyncio.to_thread(self.client.object_by_url, url=task_url)

        # Check if the task object was found
        if task_obj is None:
            logger.error(f"Task not found at URL: {task_url}")
            raise ValueError(f"Task not found at URL: {task_url}")

        # Check if the fetched object is a VTODO task
        if not hasattr(task_obj, 'obj') or task_obj.obj.name != "VTODO":
            logger.error(f"Object at URL {task_url} is not a VTODO task. Object: {task_obj}")
            raise ValueError(f"Object at URL {task_obj.url if hasattr(task_obj, 'url') else task_url} is not a VTODO task.")

        # Wrap the synchronous call in asyncio.to_thread
        await asyncio.to_thread(task_obj.delete)
        logger.info(f"Successfully deleted task: {task_url}")
        return {"status": "success", "task_url": task_url}