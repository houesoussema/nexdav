import pytest
import json
import importlib
from unittest.mock import patch, MagicMock, AsyncMock, call

# Ensure server can be imported. This might require PYTHONPATH adjustments in the execution environment.
# For this subtask, assume 'server.py' is in a location where it can be imported.
# If server.py is in the parent directory, and tests/ is a subdir,
# this might need `sys.path.append('..')` or similar, but let's try direct import first.
try:
    import server
except ImportError:
    # If direct import fails, try adjusting path if this were a local dev scenario.
    # For the tool environment, this should ideally be handled by how the sandbox is set up.
    import sys
    sys.path.append('../') # Assuming tests/ is a subdirectory of the project root
    import server


# Fixture to provide a mock CalDAVService class.
# This mock will be used to replace the actual CalDAVService class.
@pytest.fixture
def mock_caldav_service_class(mocker):
    """
    Mocks the caldav_service.CalDAVService class.
    The constructor of this mock class will return new AsyncMock instances,
    allowing us to simulate multiple CalDAVService objects.
    """
    CalDAVServiceMock = mocker.patch('caldav_service.CalDAVService', spec=True)

    # Define a side_effect function for the constructor.
    # This function will be called whenever CalDAVService() is instantiated in server.py
    def service_constructor_mock(url, username, password):
        instance = AsyncMock(spec=server.CalDAVService) # Use the actual class for spec
        instance.url = url # Store for identification
        instance.username = username
        instance.password = password # Though not used in current tests, good practice

        # Default mock methods for the instance
        instance.get_calendars = AsyncMock(return_value=[])
        instance.get_events = AsyncMock(return_value=[])
        instance.create_event = AsyncMock(return_value={})
        instance.update_event = AsyncMock(return_value={})
        instance.delete_event = AsyncMock(return_value={})
        instance.get_tasks = AsyncMock(return_value=[])
        instance.create_task = AsyncMock(return_value={})
        instance.update_task = AsyncMock(return_value={})
        instance.delete_task = AsyncMock(return_value={})
        return instance

    CalDAVServiceMock.side_effect = service_constructor_mock
    return CalDAVServiceMock


# --- Tests for caldav_services_map initialization ---

@pytest.mark.asyncio
async def test_init_valid_multiple_accounts(mock_caldav_service_class):
    accounts_data = [
        {"url": "http://caldav1.com/dav", "username": "user1", "password": "pw1"},
        {"url": "http://caldav2.com/dav", "username": "user2", "password": "pw2"},
    ]
    with patch('os.getenv') as mock_getenv:
        mock_getenv.return_value = json.dumps(accounts_data)
        importlib.reload(server) # Reload server to pick up mocked env

    assert len(server.caldav_services_map) == 2
    assert "http://caldav1.com/dav" in server.caldav_services_map
    assert "http://caldav2.com/dav" in server.caldav_services_map
    # Check if constructor was called with correct args
    mock_caldav_service_class.assert_any_call(url="http://caldav1.com/dav", username="user1", password="pw1")
    mock_caldav_service_class.assert_any_call(url="http://caldav2.com/dav", username="user2", password="pw2")

@pytest.mark.asyncio
async def test_init_empty_caldav_accounts(mock_caldav_service_class):
    with patch('os.getenv') as mock_getenv:
        mock_getenv.return_value = "[]" # Empty list
        importlib.reload(server)

    assert not server.caldav_services_map
    mock_caldav_service_class.assert_not_called()

@pytest.mark.asyncio
async def test_init_no_caldav_accounts_env_var(mock_caldav_service_class, caplog):
    # server.py defaults to "[]" if CALDAV_ACCOUNTS is not set
    with patch('os.getenv') as mock_getenv:
        def getenv_side_effect(key, default=None):
            if key == "CALDAV_ACCOUNTS":
                return None # Simulate it not being set
            return default
        mock_getenv.side_effect = getenv_side_effect
        importlib.reload(server)

    assert not server.caldav_services_map
    mock_caldav_service_class.assert_not_called()
    # A warning is logged if the map is empty after init.
    assert any("No CalDAV accounts configured" in record.message for record in caplog.records if record.levelname == "WARNING")


@pytest.mark.asyncio
async def test_init_malformed_json_caldav_accounts(mock_caldav_service_class, caplog):
    with patch('os.getenv') as mock_getenv:
        mock_getenv.return_value = "this is not valid json"
        # Need to explicitly set log level for the server's logger for caplog to catch it
        server.logger.setLevel("ERROR")
        importlib.reload(server)

    assert not server.caldav_services_map
    mock_caldav_service_class.assert_not_called()
    assert any("Failed to parse CALDAV_ACCOUNTS JSON" in record.message for record in caplog.records if record.levelname == "ERROR")

@pytest.mark.asyncio
async def test_init_incomplete_account_details(mock_caldav_service_class, caplog):
    accounts_data = [
        {"url": "http://complete.com/dav", "username": "user1", "password": "pw1"},
        {"username": "user2", "password": "pw2"}, # Missing URL
        {"url": "http://incomplete3.com/dav", "password": "pw3"}, # Missing username
    ]
    with patch('os.getenv') as mock_getenv:
        mock_getenv.return_value = json.dumps(accounts_data)
        server.logger.setLevel("ERROR") # To capture error logs for invalid configs
        importlib.reload(server)

    assert len(server.caldav_services_map) == 1 # Only the complete one
    assert "http://complete.com/dav" in server.caldav_services_map
    mock_caldav_service_class.assert_called_once_with(url="http://complete.com/dav", username="user1", password="pw1")
    assert any("Invalid account configuration found" in record.message for record in caplog.records if record.levelname == "ERROR")


# --- Tests for list_caldav_calendars tool ---

@pytest.mark.asyncio
async def test_list_calendars_multiple_accounts_success(mock_caldav_service_class):
    accounts_data = [
        {"url": "http://acc1.com/dav", "username": "u1", "password": "p1"},
        {"url": "http://acc2.com/dav", "username": "u2", "password": "p2"},
    ]
    with patch('os.getenv') as mock_getenv:
        mock_getenv.return_value = json.dumps(accounts_data)
        importlib.reload(server)

    # Configure the mock instances created by server.py
    service1 = server.caldav_services_map["http://acc1.com/dav"]
    service1.get_calendars = AsyncMock(return_value=[{'name': 'Cal1 from Acc1', 'url': 'http://acc1.com/dav/cal1'}])

    service2 = server.caldav_services_map["http://acc2.com/dav"]
    service2.get_calendars = AsyncMock(return_value=[{'name': 'CalA from Acc2', 'url': 'http://acc2.com/dav/calA'}])

    result = await server.list_caldav_calendars()

    assert len(result) == 2
    assert {'name': 'Cal1 from Acc1', 'url': 'http://acc1.com/dav/cal1', 'account_identifier': 'http://acc1.com/dav'} in result
    assert {'name': 'CalA from Acc2', 'url': 'http://acc2.com/dav/calA', 'account_identifier': 'http://acc2.com/dav'} in result
    service1.get_calendars.assert_called_once()
    service2.get_calendars.assert_called_once()

@pytest.mark.asyncio
async def test_list_calendars_one_service_fails(mock_caldav_service_class, caplog):
    accounts_data = [
        {"url": "http://ok.com/dav", "username": "ok_user", "password": "p_ok"},
        {"url": "http://fail.com/dav", "username": "fail_user", "password": "p_fail"},
    ]
    with patch('os.getenv') as mock_getenv:
        mock_getenv.return_value = json.dumps(accounts_data)
        server.logger.setLevel("ERROR") # To capture CalDAVConnectionError log
        importlib.reload(server)

    service_ok = server.caldav_services_map["http://ok.com/dav"]
    service_ok.get_calendars = AsyncMock(return_value=[{'name': 'OK Cal', 'url': 'http://ok.com/dav/cal_ok'}])

    service_fail = server.caldav_services_map["http://fail.com/dav"]
    service_fail.get_calendars = AsyncMock(side_effect=server.CalDAVConnectionError("Connection failed"))

    result = await server.list_caldav_calendars()

    assert len(result) == 1 # Only calendars from the working service
    assert {'name': 'OK Cal', 'url': 'http://ok.com/dav/cal_ok', 'account_identifier': 'http://ok.com/dav'} in result
    service_ok.get_calendars.assert_called_once()
    service_fail.get_calendars.assert_called_once()
    assert any("CalDAV connection error for account http://fail.com/dav" in record.message for record in caplog.records if record.levelname == "ERROR")

@pytest.mark.asyncio
async def test_list_calendars_no_accounts_configured(mock_caldav_service_class):
    with patch('os.getenv') as mock_getenv:
        mock_getenv.return_value = "[]"
        importlib.reload(server)

    result = await server.list_caldav_calendars()
    assert result == []

# --- Tests for tools like list_caldav_events ---

@pytest.mark.asyncio
async def test_list_events_valid_account(mock_caldav_service_class):
    account_url = "http://caldav.test/dav"
    calendar_url_to_test = f"{account_url}/cal1"

    with patch('os.getenv') as mock_getenv:
        mock_getenv.return_value = json.dumps([{"url": account_url, "username": "user", "password": "pw"}])
        importlib.reload(server)

    mocked_service = server.caldav_services_map[account_url]
    expected_events = [{"summary": "Test Event", "url": f"{calendar_url_to_test}/event1.ics"}]
    mocked_service.get_events = AsyncMock(return_value=expected_events)

    start_date_str = "2024-01-01"
    end_date_str = "2024-01-31"

    # Convert string dates to datetime objects for assertion, as server.py does this conversion
    from datetime import datetime
    import pytz
    s_date_obj = datetime.strptime(start_date_str, '%Y-%m-%d').replace(tzinfo=pytz.UTC)
    e_date_obj = datetime.strptime(end_date_str, '%Y-%m-%d').replace(tzinfo=pytz.UTC)


    result = await server.list_caldav_events(
        account_identifier=account_url,
        calendar_url=calendar_url_to_test,
        start_date=start_date_str,
        end_date=end_date_str
    )

    assert result == expected_events
    mocked_service.get_events.assert_called_once_with(calendar_url_to_test, s_date_obj, e_date_obj)

@pytest.mark.asyncio
async def test_list_events_invalid_account(mock_caldav_service_class):
    with patch('os.getenv') as mock_getenv:
        mock_getenv.return_value = json.dumps([{"url": "http://real.account/dav", "username": "user", "password": "pw"}])
        importlib.reload(server)

    result = await server.list_caldav_events(account_identifier="http://fake.account/dav", calendar_url="http://fake.account/dav/cal1")

    expected_error = [{"status": "error", "message": "Account identifier 'http://fake.account/dav' not found."}]
    assert result == expected_error

    # Ensure no service's get_events was called
    if server.caldav_services_map: # It will have one entry
        real_service = server.caldav_services_map["http://real.account/dav"]
        real_service.get_events.assert_not_called()


@pytest.mark.asyncio
async def test_list_events_no_accounts_configured(mock_caldav_service_class):
    with patch('os.getenv') as mock_getenv:
        mock_getenv.return_value = "[]"
        importlib.reload(server)

    # Attempt to call list_events, it should fail because account_identifier won't be found
    result = await server.list_caldav_events(account_identifier="http://any.account/dav", calendar_url="http://any.account/dav/cal1")
    expected_error = [{"status": "error", "message": "Account identifier 'http://any.account/dav' not found."}]
    assert result == expected_error

# --- Tests for tools like create_caldav_event ---

@pytest.mark.asyncio
async def test_create_event_valid_account(mock_caldav_service_class):
    account_url = "http://caldav.test/dav"
    calendar_url_to_test = f"{account_url}/cal1"
    ical_content = "BEGIN:VCALENDAR..."

    with patch('os.getenv') as mock_getenv:
        mock_getenv.return_value = json.dumps([{"url": account_url, "username": "user", "password": "pw"}])
        importlib.reload(server)

    mocked_service = server.caldav_services_map[account_url]
    expected_response = {"status": "success", "event_url": f"{calendar_url_to_test}/newevent.ics"}
    mocked_service.create_event = AsyncMock(return_value=expected_response)

    # Mock icalendar.Calendar.from_ical to prevent actual parsing
    with patch('icalendar.Calendar.from_ical') as mock_from_ical:
        mock_from_ical.return_value = MagicMock() # Just needs to not raise error

        result = await server.create_caldav_event(
            account_identifier=account_url,
            calendar_url=calendar_url_to_test,
            ical_content=ical_content
        )

    assert result == expected_response
    mocked_service.create_event.assert_called_once_with(
        calendar_url_to_test,
        ical_content,
        reminder_minutes_before=None, # Default if not provided
        reminder_description=None   # Default if not provided
    )
    mock_from_ical.assert_called_once_with(ical_content)


@pytest.mark.asyncio
async def test_create_event_invalid_account(mock_caldav_service_class):
    with patch('os.getenv') as mock_getenv:
        mock_getenv.return_value = json.dumps([{"url": "http://real.account/dav", "username": "user", "password": "pw"}])
        importlib.reload(server)

    result = await server.create_caldav_event(
        account_identifier="http://fake.account/dav",
        calendar_url="http://fake.account/dav/cal1",
        ical_content="BEGIN:VCALENDAR..."
    )

    expected_error = {"status": "error", "message": "Account identifier 'http://fake.account/dav' not found."}
    assert result == expected_error

    if server.caldav_services_map:
        real_service = server.caldav_services_map["http://real.account/dav"]
        real_service.create_event.assert_not_called()

@pytest.mark.asyncio
async def test_create_event_with_reminder_params(mock_caldav_service_class):
    account_url = "http://caldav.test/dav"
    calendar_url_to_test = f"{account_url}/cal1"
    ical_content = "BEGIN:VCALENDAR..."
    reminder_minutes = 30
    reminder_desc = "Test Reminder"

    with patch('os.getenv') as mock_getenv:
        mock_getenv.return_value = json.dumps([{"url": account_url, "username": "user", "password": "pw"}])
        importlib.reload(server)

    mocked_service = server.caldav_services_map[account_url]
    expected_response = {"status": "success", "event_url": f"{calendar_url_to_test}/newevent_reminder.ics"}
    mocked_service.create_event = AsyncMock(return_value=expected_response)

    with patch('icalendar.Calendar.from_ical') as mock_from_ical:
        mock_from_ical.return_value = MagicMock()

        result = await server.create_caldav_event(
            account_identifier=account_url,
            calendar_url=calendar_url_to_test,
            ical_content=ical_content,
            reminder_minutes_before=reminder_minutes,
            reminder_description=reminder_desc
        )

    assert result == expected_response
    mocked_service.create_event.assert_called_once_with(
        calendar_url_to_test,
        ical_content,
        reminder_minutes_before=reminder_minutes,
        reminder_description=reminder_desc
    )
    mock_from_ical.assert_called_once_with(ical_content)


# --- Tests for update_caldav_event ---

@pytest.mark.asyncio
async def test_update_event_valid_account(mock_caldav_service_class):
    account_url = "http://caldav.test/dav"
    event_url_to_test = f"{account_url}/cal1/event1.ics"
    ical_content = "BEGIN:VCALENDAR..."

    with patch('os.getenv') as mock_getenv:
        mock_getenv.return_value = json.dumps([{"url": account_url, "username": "user", "password": "pw"}])
        importlib.reload(server)

    mocked_service = server.caldav_services_map[account_url]
    expected_response = {"status": "success", "event_url": event_url_to_test}
    mocked_service.update_event = AsyncMock(return_value=expected_response)

    with patch('icalendar.Calendar.from_ical') as mock_from_ical:
        mock_from_ical.return_value = MagicMock()

        result = await server.update_caldav_event(
            account_identifier=account_url,
            event_url=event_url_to_test,
            ical_content=ical_content
        )

    assert result == expected_response
    mocked_service.update_event.assert_called_once_with(
        event_url_to_test,
        ical_content=ical_content,
        reminder_minutes_before=None, # Default
        reminder_description=None   # Default
    )
    mock_from_ical.assert_called_once_with(ical_content)


@pytest.mark.asyncio
async def test_update_event_with_reminder_params(mock_caldav_service_class):
    account_url = "http://caldav.test/dav"
    event_url_to_test = f"{account_url}/cal1/event1.ics"
    ical_content = "BEGIN:VCALENDAR..." # Can be None if only updating reminder
    reminder_minutes = 60
    reminder_desc = "Updated Reminder"

    with patch('os.getenv') as mock_getenv:
        mock_getenv.return_value = json.dumps([{"url": account_url, "username": "user", "password": "pw"}])
        importlib.reload(server)

    mocked_service = server.caldav_services_map[account_url]
    expected_response = {"status": "success", "event_url": event_url_to_test}
    mocked_service.update_event = AsyncMock(return_value=expected_response)

    # Test with ical_content provided
    with patch('icalendar.Calendar.from_ical') as mock_from_ical:
        mock_from_ical.return_value = MagicMock()
        result = await server.update_caldav_event(
            account_identifier=account_url,
            event_url=event_url_to_test,
            ical_content=ical_content,
            reminder_minutes_before=reminder_minutes,
            reminder_description=reminder_desc
        )
    assert result == expected_response
    mocked_service.update_event.assert_called_once_with(
        event_url_to_test,
        ical_content=ical_content,
        reminder_minutes_before=reminder_minutes,
        reminder_description=reminder_desc
    )
    mock_from_ical.assert_called_once_with(ical_content)

    # Test with ical_content as None (only updating reminder)
    mocked_service.update_event.reset_mock() # Reset call count for next assertion
    with patch('icalendar.Calendar.from_ical') as mock_from_ical_none: # New mock for this call
        result_reminder_only = await server.update_caldav_event(
            account_identifier=account_url,
            event_url=event_url_to_test,
            ical_content=None, # Testing this case
            reminder_minutes_before=reminder_minutes,
            reminder_description=reminder_desc
        )
    assert result_reminder_only == expected_response
    mocked_service.update_event.assert_called_once_with(
        event_url_to_test,
        ical_content=None,
        reminder_minutes_before=reminder_minutes,
        reminder_description=reminder_desc
    )
    mock_from_ical_none.assert_not_called() # Should not be called if ical_content is None


# --- Tests for task-related tools like list_caldav_tasks ---

@pytest.mark.asyncio
async def test_list_tasks_valid_account(mock_caldav_service_class):
    account_url = "http://caldav.tasks/dav"
    calendar_url_to_test = f"{account_url}/tasks_cal"

    with patch('os.getenv') as mock_getenv:
        mock_getenv.return_value = json.dumps([{"url": account_url, "username": "task_user", "password": "tpw"}])
        importlib.reload(server)

    mocked_service = server.caldav_services_map[account_url]
    expected_tasks = [{"summary": "Test Task", "url": f"{calendar_url_to_test}/task1.ics"}]
    mocked_service.get_tasks = AsyncMock(return_value=expected_tasks)

    result = await server.list_caldav_tasks(
        account_identifier=account_url,
        calendar_url=calendar_url_to_test,
        include_completed=True
    )

    assert result == expected_tasks
    mocked_service.get_tasks.assert_called_once_with(calendar_url_to_test, True)


@pytest.mark.asyncio
async def test_list_tasks_invalid_account(mock_caldav_service_class):
    with patch('os.getenv') as mock_getenv:
        mock_getenv.return_value = json.dumps([{"url": "http://real.tasks/dav", "username": "user", "password": "pw"}])
        importlib.reload(server)

    result = await server.list_caldav_tasks(
        account_identifier="http://fake.tasks/dav",
        calendar_url="http://fake.tasks/dav/cal1"
    )

    expected_error = [{"status": "error", "message": "Account identifier 'http://fake.tasks/dav' not found."}]
    assert result == expected_error

    if server.caldav_services_map:
        real_service = server.caldav_services_map["http://real.tasks/dav"]
        real_service.get_tasks.assert_not_called()
