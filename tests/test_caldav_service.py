# tests/test_caldav_service.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
import pytz
from icalendar import Calendar as ICalCalendar, Event as ICalEvent, Todo as ICalTodo # For creating test ical data

# Make sure caldav_service is importable, adjust sys.path if necessary
# This might require adding the root project directory to sys.path
# For example, by having a conftest.py in tests/ with:
# import sys, os; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# For now, assume it's handled by the execution environment or PYTHONPATH.

from caldav_service import CalDAVService, CalDAVConnectionError
import caldav.lib.error # To mock caldav.lib.error.AuthorizationError
import requests.exceptions # To mock requests.exceptions.ConnectionError

# Sample iCalendar data
SAMPLE_EVENT_ICAL = """
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test Corp//NONSGML CalDAV Client//EN
BEGIN:VEVENT
UID:12345
DTSTAMP:20230101T000000Z
SUMMARY:Test Event
DTSTART:20230101T100000Z
DTEND:20230101T110000Z
END:VEVENT
END:VCALENDAR
"""

SAMPLE_TASK_ICAL_INCOMPLETE = """
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test Corp//NONSGML CalDAV Client//EN
BEGIN:VTODO
UID:task1
DTSTAMP:20230101T000000Z
SUMMARY:Incomplete Task
STATUS:NEEDS-ACTION
END:VTODO
END:VCALENDAR
"""

SAMPLE_TASK_ICAL_COMPLETED = """
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test Corp//NONSGML CalDAV Client//EN
BEGIN:VTODO
UID:task2
DTSTAMP:20230101T000000Z
SUMMARY:Completed Task
STATUS:COMPLETED
END:VTODO
END:VCALENDAR
"""


@pytest.fixture
def mock_dav_client_instance():
    mock_client = MagicMock(spec=caldav.DAVClient)
    mock_client.principal = AsyncMock()
    # Add other necessary mocked methods for caldav.DAVClient if needed by CalDAVService constructor or connect
    return mock_client

@pytest.fixture
def mock_principal():
    principal = AsyncMock()
    principal.calendars = AsyncMock(return_value=[]) # Default empty list
    return principal

@pytest.fixture
def service(mock_dav_client_instance, mock_principal):
    # Patch caldav.DAVClient to return our mock_dav_client_instance
    with patch('caldav.DAVClient', return_value=mock_dav_client_instance):
        service = CalDAVService(url="http://dummy.url", username="user", password="pass")
        # Pre-assign the mocked principal to avoid connect() actually trying to fetch it via network
        service.principal = mock_principal
        service.client = mock_dav_client_instance # Assign the client as well
        return service

@pytest.fixture # Separate fixture for testing connect() itself
def service_for_connect_test():
    service = CalDAVService(url="http://dummy.url", username="user", password="pass")
    return service


@pytest.mark.asyncio
async def test_connect_success(service_for_connect_test, mock_principal):
    with patch('caldav.DAVClient') as mock_dav_client_constructor:
        mock_client_instance = mock_dav_client_constructor.return_value
        mock_client_instance.principal = AsyncMock(return_value=mock_principal)

        await service_for_connect_test.connect()
        assert service_for_connect_test.client == mock_client_instance
        assert service_for_connect_test.principal == mock_principal
        mock_dav_client_constructor.assert_called_once_with(
            url="http://dummy.url", username="user", password="pass"
        )
        mock_client_instance.principal.assert_called_once()


@pytest.mark.asyncio
async def test_connect_connection_error(service_for_connect_test):
    with patch('caldav.DAVClient', side_effect=requests.exceptions.ConnectionError("Test connection error")):
        with pytest.raises(CalDAVConnectionError, match="Connection to CalDAV server failed"):
            await service_for_connect_test.connect()

@pytest.mark.asyncio
async def test_connect_auth_error(service_for_connect_test):
    # Mock the DAVClient constructor
    with patch('caldav.DAVClient') as mock_dav_client_constructor:
        # Make the principal() call on the instance raise AuthorizationError
        mock_client_instance = mock_dav_client_constructor.return_value
        # Corrected line: caldav.lib.error not caldav.error
        mock_client_instance.principal = AsyncMock(side_effect=caldav.lib.error.AuthorizationError("Test auth error"))

        with pytest.raises(CalDAVConnectionError, match="Authentication failed for CalDAV server"):
            await service_for_connect_test.connect()


@pytest.mark.asyncio
async def test_get_calendars_success(service, mock_principal):
    mock_cal1 = MagicMock()
    mock_cal1.get_property = MagicMock(return_value="Personal")
    mock_cal1.url = "http://dummy.url/cal1"

    mock_cal2 = MagicMock()
    mock_cal2.get_property = MagicMock(return_value="Work")
    mock_cal2.url = "http://dummy.url/cal2"

    mock_principal.calendars = AsyncMock(return_value=[mock_cal1, mock_cal2])

    calendars = await service.get_calendars()
    assert len(calendars) == 2
    assert {"name": "Personal", "url": "http://dummy.url/cal1"} in calendars
    assert {"name": "Work", "url": "http://dummy.url/cal2"} in calendars
    mock_principal.calendars.assert_called_once()

@pytest.mark.asyncio
async def test_get_calendars_connect_implicit_call(service_for_connect_test, mock_principal):
    # Test that connect() is called if principal is not set
    service_for_connect_test.principal = None # Ensure principal is not set initially
    with patch('caldav.DAVClient') as mock_dav_client_constructor:
        mock_client_instance = mock_dav_client_constructor.return_value
        mock_client_instance.principal = AsyncMock(return_value=mock_principal)
        mock_principal.calendars = AsyncMock(return_value=[]) # Ensure calendars() can be called

        await service_for_connect_test.get_calendars()
        mock_client_instance.principal.assert_called_once() # connect was called
        mock_principal.calendars.assert_called_once()


@pytest.mark.asyncio
async def test_get_events_success(service, mock_dav_client_instance):
    calendar_url = "http://dummy.url/cal1"
    mock_calendar_obj = AsyncMock()
    mock_dav_client_instance.calendar = AsyncMock(return_value=mock_calendar_obj)

    mock_event1 = MagicMock()
    mock_event1.url = "http://dummy.url/cal1/event1.ics"
    mock_event1.data = SAMPLE_EVENT_ICAL
    mock_calendar_obj.date_search = AsyncMock(return_value=[mock_event1])

    start_date = datetime(2023, 1, 1, tzinfo=pytz.utc)
    end_date = datetime(2023, 1, 31, tzinfo=pytz.utc)

    events = await service.get_events(calendar_url, start_date, end_date)

    assert len(events) == 1
    assert events[0]["url"] == "http://dummy.url/cal1/event1.ics"
    assert events[0]["data"] == SAMPLE_EVENT_ICAL
    mock_dav_client_instance.calendar.assert_called_once_with(url=calendar_url)
    # Corrected: date_search arguments are start and end, not a dict
    mock_calendar_obj.date_search.assert_called_once_with(start=start_date, end=end_date)

@pytest.mark.asyncio
async def test_get_events_default_dates(service, mock_dav_client_instance):
    calendar_url = "http://dummy.url/cal1"
    mock_calendar_obj = AsyncMock()
    mock_dav_client_instance.calendar = AsyncMock(return_value=mock_calendar_obj)
    mock_calendar_obj.date_search = AsyncMock(return_value=[]) # No events needed for this test

    await service.get_events(calendar_url) # Call with default dates

    mock_calendar_obj.date_search.assert_called_once()
    # Corrected: Access positional or keyword arguments based on how they are passed.
    # Assuming they are passed as keyword arguments `start` and `end` to date_search.
    # If date_search is called like date_search(start=X, end=Y), then args[0] would be empty, and args[1] (kwargs) would have them.
    # If date_search is called like date_search(X, Y), then args[0][0] is start, args[0][1] is end.
    # The actual implementation CalDAVService.get_events calls it as calendar.date_search(start=start_date, end=end_date)
    called_args_kwargs = mock_calendar_obj.date_search.call_args.kwargs

    assert isinstance(called_args_kwargs['start'], datetime)
    assert isinstance(called_args_kwargs['end'], datetime)
    # Default start is 30 days ago, end is 1 year from now.
    # Allow a small delta for the time 'now' is calculated.
    assert (datetime.now(pytz.utc) - timedelta(days=30) - called_args_kwargs['start']).total_seconds() < 5
    assert (datetime.now(pytz.utc) + timedelta(days=365) - called_args_kwargs['end']).total_seconds() < 5


@pytest.mark.asyncio
async def test_create_event_success(service, mock_dav_client_instance):
    calendar_url = "http://dummy.url/cal1"
    mock_calendar_obj = AsyncMock()
    mock_dav_client_instance.calendar = AsyncMock(return_value=mock_calendar_obj)

    mock_saved_event = MagicMock()
    mock_saved_event.url = "http://dummy.url/cal1/newevent.ics"
    mock_calendar_obj.save_event = AsyncMock(return_value=mock_saved_event)

    result = await service.create_event(calendar_url, SAMPLE_EVENT_ICAL)

    assert result["status"] == "success"
    assert result["event_url"] == "http://dummy.url/cal1/newevent.ics"
    mock_calendar_obj.save_event.assert_called_once_with(ical=SAMPLE_EVENT_ICAL)


@pytest.mark.asyncio
async def test_update_event_success(service, mock_dav_client_instance):
    event_url = "http://dummy.url/cal1/event1.ics"
    mock_event_obj = AsyncMock(spec=caldav.objects.Event) # Use spec for caldav.objects.Event
    mock_event_obj.url = event_url # Ensure the mock event has a URL
    mock_event_obj.save = AsyncMock() # Mock the save method
    mock_dav_client_instance.event = AsyncMock(return_value=mock_event_obj)

    new_ical_content = SAMPLE_EVENT_ICAL.replace("Test Event", "Updated Test Event")
    result = await service.update_event(event_url, new_ical_content)

    assert result["status"] == "success"
    assert result["event_url"] == event_url
    mock_dav_client_instance.event.assert_called_once_with(url=event_url)
    assert mock_event_obj.data == new_ical_content # Check data was assigned
    mock_event_obj.save.assert_called_once()


@pytest.mark.asyncio
async def test_delete_event_success(service, mock_dav_client_instance):
    event_url = "http://dummy.url/cal1/event1.ics"
    mock_event_obj = AsyncMock(spec=caldav.objects.Event)
    mock_event_obj.delete = AsyncMock()
    mock_dav_client_instance.event = AsyncMock(return_value=mock_event_obj)

    result = await service.delete_event(event_url)

    assert result["status"] == "success"
    assert result["event_url"] == event_url
    mock_dav_client_instance.event.assert_called_once_with(url=event_url)
    mock_event_obj.delete.assert_called_once()

# --- Task Tests ---
@pytest.mark.asyncio
async def test_get_tasks_success_incomplete_only(service, mock_dav_client_instance):
    calendar_url = "http://dummy.url/cal1"
    mock_calendar_obj = AsyncMock() # Renamed to avoid conflict
    mock_dav_client_instance.calendar = AsyncMock(return_value=mock_calendar_obj)

    mock_task_incomplete = MagicMock(spec=caldav.objects.Todo) # Use spec for caldav.objects.Todo
    mock_task_incomplete.url = "http://dummy.url/cal1/task1.ics"
    mock_task_incomplete.data = SAMPLE_TASK_ICAL_INCOMPLETE

    mock_task_completed = MagicMock(spec=caldav.objects.Todo)
    mock_task_completed.url = "http://dummy.url/cal1/task2.ics"
    mock_task_completed.data = SAMPLE_TASK_ICAL_COMPLETED

    mock_calendar_obj.todos = AsyncMock(return_value=[mock_task_incomplete, mock_task_completed])

    tasks = await service.get_tasks(calendar_url, include_completed=False)

    assert len(tasks) == 1
    assert tasks[0]["url"] == "http://dummy.url/cal1/task1.ics"
    assert tasks[0]["data"] == SAMPLE_TASK_ICAL_INCOMPLETE
    mock_dav_client_instance.calendar.assert_called_once_with(url=calendar_url)
    mock_calendar_obj.todos.assert_called_once()

@pytest.mark.asyncio
async def test_get_tasks_include_completed(service, mock_dav_client_instance):
    calendar_url = "http://dummy.url/cal1"
    mock_calendar_obj = AsyncMock()
    mock_dav_client_instance.calendar = AsyncMock(return_value=mock_calendar_obj)

    mock_task_incomplete = MagicMock(spec=caldav.objects.Todo)
    mock_task_incomplete.url = "http://dummy.url/cal1/task1.ics"
    mock_task_incomplete.data = SAMPLE_TASK_ICAL_INCOMPLETE

    mock_task_completed = MagicMock(spec=caldav.objects.Todo)
    mock_task_completed.url = "http://dummy.url/cal1/task2.ics"
    mock_task_completed.data = SAMPLE_TASK_ICAL_COMPLETED

    mock_calendar_obj.todos = AsyncMock(return_value=[mock_task_incomplete, mock_task_completed])

    tasks = await service.get_tasks(calendar_url, include_completed=True)

    assert len(tasks) == 2
    urls = [t["url"] for t in tasks]
    assert "http://dummy.url/cal1/task1.ics" in urls
    assert "http://dummy.url/cal1/task2.ics" in urls

@pytest.mark.asyncio
async def test_get_tasks_parsing_error_skip(service, mock_dav_client_instance):
    calendar_url = "http://dummy.url/cal1"
    mock_calendar_obj = AsyncMock()
    mock_dav_client_instance.calendar = AsyncMock(return_value=mock_calendar_obj)

    mock_task_valid = MagicMock(spec=caldav.objects.Todo)
    mock_task_valid.url = "http://dummy.url/cal1/task_valid.ics"
    mock_task_valid.data = SAMPLE_TASK_ICAL_INCOMPLETE # Valid

    mock_task_invalid_data = MagicMock(spec=caldav.objects.Todo)
    mock_task_invalid_data.url = "http://dummy.url/cal1/task_invalid.ics"
    mock_task_invalid_data.data = "BEGIN:VCALENDAR...INVALID_DATA...END:VCALENDAR" # Malformed

    mock_calendar_obj.todos = AsyncMock(return_value=[mock_task_valid, mock_task_invalid_data])

    # When include_completed=False, parsing is attempted. Invalid task should be skipped.
    tasks = await service.get_tasks(calendar_url, include_completed=False)
    assert len(tasks) == 1
    assert tasks[0]["url"] == "http://dummy.url/cal1/task_valid.ics"

@pytest.mark.asyncio
async def test_create_task_success(service, mock_dav_client_instance):
    calendar_url = "http://dummy.url/cal1"
    mock_calendar_obj = AsyncMock()
    mock_dav_client_instance.calendar = AsyncMock(return_value=mock_calendar_obj)

    mock_saved_task = MagicMock(spec=caldav.objects.Todo)
    mock_saved_task.url = "http://dummy.url/cal1/newtask.ics"
    mock_calendar_obj.save_todo = AsyncMock(return_value=mock_saved_task) # save_todo for tasks

    result = await service.create_task(calendar_url, SAMPLE_TASK_ICAL_INCOMPLETE)

    assert result["status"] == "success"
    assert result["task_url"] == "http://dummy.url/cal1/newtask.ics"
    mock_calendar_obj.save_todo.assert_called_once_with(ical=SAMPLE_TASK_ICAL_INCOMPLETE)


@pytest.mark.asyncio
async def test_update_task_success(service, mock_dav_client_instance):
    task_url = "http://dummy.url/cal1/task1.ics"
    # Ensure the mock_task_obj has a .data attribute that can be set
    mock_task_obj = AsyncMock(spec=caldav.objects.Todo)
    mock_task_obj.url = task_url # Set the URL attribute for the mock
    mock_task_obj.save = AsyncMock()
    mock_dav_client_instance.todo = AsyncMock(return_value=mock_task_obj) # client.todo() for tasks

    new_ical_content = SAMPLE_TASK_ICAL_INCOMPLETE.replace("Incomplete Task", "Updated Incomplete Task")
    result = await service.update_task(task_url, new_ical_content)

    assert result["status"] == "success"
    assert result["task_url"] == task_url
    mock_dav_client_instance.todo.assert_called_once_with(url=task_url)
    assert mock_task_obj.data == new_ical_content
    mock_task_obj.save.assert_called_once()


@pytest.mark.asyncio
async def test_delete_task_success(service, mock_dav_client_instance):
    task_url = "http://dummy.url/cal1/task1.ics"
    mock_task_obj = AsyncMock(spec=caldav.objects.Todo)
    mock_task_obj.delete = AsyncMock()
    mock_dav_client_instance.todo = AsyncMock(return_value=mock_task_obj)

    result = await service.delete_task(task_url)

    assert result["status"] == "success"
    assert result["task_url"] == task_url
    mock_dav_client_instance.todo.assert_called_once_with(url=task_url)
    mock_task_obj.delete.assert_called_once()
