import caldav
from caldav.elements import dav
from datetime import datetime, date, timedelta
import pytz # For timezone handling

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
        This method should be called before performing any calendar or task operations.
        """
        self.client = caldav.DAVClient(
            url=self.url,
            username=self.username,
            password=self.password
        )
        self.principal = await self.client.principal()

    async def get_calendars(self):
        """
        Retrieves a list of all calendars accessible by the authenticated user.

        Returns:
            list: A list of dictionaries, where each dictionary represents a calendar
                  with 'name' (display name) and 'url'.
        """
        if not self.principal:
            await self.connect()
        calendars = await self.principal.calendars()
        # Extract display name and URL for each calendar
        return [{"name": cal.get_property(dav.DisplayName()), "url": str(cal.url)} for cal in calendars]

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
        
        # Get the specific calendar object by its URL
        calendar = await self.client.calendar(url=calendar_url)
        
        # Set default date ranges if not provided
        now = datetime.now(pytz.utc)
        if not start_date:
            start_date = now - timedelta(days=30) # Default: last 30 days
        if not end_date:
            end_date = now + timedelta(days=365) # Default: next year

        # Perform a date-range search for events
        events = await calendar.date_search(start=start_date, end=end_date)
        
        event_list = []
        for event in events:
            event_list.append({"url": str(event.url), "data": event.data})
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
        calendar = await self.client.calendar(url=calendar_url)
        event = await calendar.save_event(ical=ical_content)
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
        event = await self.client.event(url=event_url)
        event.data = ical_content
        await event.save()
        return {"status": "success", "event_url": str(event.url)}

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
        event = await self.client.event(url=event_url)
        await event.delete()
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
        
        calendar = await self.client.calendar(url=calendar_url)
        tasks = await calendar.todos() # Get all tasks

        task_list = []
        for task in tasks:
            # You might want to parse task.data here to check completion status
            # For simplicity, we'll return all and filter later if needed,
            # or rely on the client to filter.
            if not include_completed:
                # Basic check for completion, requires parsing VTODO content for STATUS
                # This would be more robust with a vobject parser.
                if "STATUS:COMPLETED" in task.data: # Very simplistic check
                    continue
            task_list.append({"url": str(task.url), "data": task.data})
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
        calendar = await self.client.calendar(url=calendar_url)
        # The save_todo method is typically used for VTODOs
        task = await calendar.save_todo(ical=ical_content)
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
        task = await self.client.todo(url=task_url)
        task.data = ical_content
        await task.save()
        return {"status": "success", "task_url": str(task.url)}

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
        task = await self.client.todo(url=task_url)
        await task.delete()
        return {"status": "success", "task_url": task_url}