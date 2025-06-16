# MCP CalDAV Nextcloud Integration Server

**Note on Formatting:** Due to a technical limitation with writing files containing markdown code blocks via this interface, the code examples below are formatted using simple indentation or as plain text instead of fenced code blocks (e.g., ```bash). You can manually add the ```language fences back into the `README.md` file after it's created if desired.

This project provides an MCP (Model Context Protocol) server that enables Claude or any other MCP-compatible client to interact with your CalDAV calendar, specifically designed for Nextcloud Calendar integration.

## Table of Contents
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Setup Instructions](#setup-instructions)
  - [1. Clone the Repository (if applicable)](#1-clone-the-repository-if-applicable)
  - [2. Create and Configure Environment Variables](#2-create-and-configure-environment-variables)
  - [3. Install Dependencies](#3-install-dependencies)
  - [4. Test the MCP Server (Optional)](#4-test-the-mcp-server-optional)
  - [5. Integrate with MCP SuperAssistant Proxy](#5-integrate-with-mcp-superassistant-proxy)
- [Usage with Claude](#usage-with-claude)
- [Tools Exposed](#tools-exposed)
- [API Documentation](#api-documentation)
- [Project Structure](#project-structure)
- [Contributing](#contributing)
- [License](#license)

## Features
- **List Calendars:** Retrieve a list of all available calendars for the configured user.
- **Multi-Account Support:** Configure and use multiple CalDAV accounts simultaneously.
- **List Events:** Fetch events from a specified calendar within a given date range.
- **Create Event:** Add new events to a calendar using iCalendar (VCS) content.
- **Update Event:** Modify existing events by providing new iCalendar content.
- **Delete Event:** Remove events from a calendar.
- **List Tasks:** Fetch tasks from a specified calendar, with an option to include completed tasks. (Accurately filters completed tasks by parsing iCalendar data).
- **Create Task:** Add new tasks to a calendar using iCalendar (VTODO) content.
- **Update Task:** Modify existing tasks by providing new iCalendar (VTODO) content.
- **Delete Task:** Remove tasks from a calendar.
- **Error Handling:**
    - Reports CalDAV connection and authentication failures.
    - Validates iCalendar content for create/update operations and reports parsing errors.
    - Errors are generally returned as JSON objects (e.g., `{"status": "error", "message": "..."}`).

## Prerequisites
Before you begin, ensure you have the following:
- Python 3.9+ installed.
- `pip` (Python package installer).
- Access to a Nextcloud instance with a calendar configured.
- An "App password" generated in your Nextcloud security settings for better security (recommended over your main password).
- The `mcp-superassistant-proxy` (or similar MCP client) configured and running.

## Setup Instructions

### 1. Clone the Repository (if applicable)
If you received this project as a Git repository, clone it to your local machine:
    git clone https://github.com/your-repo/mcp-caldav-server.git
    cd mcp-caldav-server
If you manually created the files, navigate to the `mcp-caldav-server` directory.

### 2. Create and Configure Environment Variables
Sensitive information like your CalDAV URL, username, and password should not be committed directly into your code. This project uses `python-dotenv` to load these from a `.env` file.

1.  **Create `.env` file:** Copy the provided `.env.example` to `.env` in the root of the project directory:
        cp .env.example .env
2.  **Edit `.env`:** Open the newly created `.env` file and fill in your actual CalDAV account details.
        The `CALDAV_ACCOUNTS` variable should be a JSON string representing a list of account objects. Each object in the list must have `url`, `username`, and `password` keys.

        # .env
        # Define CalDAV accounts as a JSON string.
        # Each object in the list should have "url", "username", and "password".
        # Example for two accounts:
        # CALDAV_ACCOUNTS='[
        #   {"url": "https://your-nextcloud-instance.com/remote.php/dav/calendars/YOUR_USERNAME/", "username": "your_nextcloud_username", "password": "your_nextcloud_app_password"},
        #   {"url": "https://another-caldav-server.com/dav/principals/users/another_user/", "username": "another_user", "password": "another_password"}
        # ]'
        CALDAV_ACCOUNTS='[{"url": "https://your-nextcloud-instance.com/remote.php/dav/calendars/YOUR_USERNAME/", "username": "your_nextcloud_username", "password": "your_nextcloud_app_password"}]'

    *   **`CALDAV_ACCOUNTS`**: A JSON string list. Each item needs:
        *   `"url"`: The base CalDAV URL for the account (e.g., Nextcloud's primary CalDAV URL, often ending with `/dav/calendars/YOUR_USERNAME/` or similar).
        *   `"username"`: The username for that CalDAV account.
        *   `"password"`: The password (preferably an app-specific password) for that account.

### 3. Install Dependencies
Navigate to the project directory and install the required Python packages:
    pip install -r requirements.txt

### 4. Test the MCP Server (Optional)
You can test the MCP server locally using the `mcp` CLI tool (installed via `mcp[cli]`):
    mcp dev server.py
This command will start the MCP server and usually open a web-based MCP Inspector in your browser, where you can see the exposed tools and even try invoking them. Check your terminal for the URL to the inspector.

### 5. Integrate with MCP SuperAssistant Proxy
To make your new CalDAV server available to Claude, you need to configure your `mcp-superassistant-proxy` (or similar proxy setup).

1.  **Locate your proxy's configuration file.** This is often named `claude.json` or similar.
2.  **Add a new entry** under the `mcpServers` section for your `caldav-nextcloud` server.
    Ensure the `command` points to `python` and `args` points to the absolute path of your `server.py` file. The `env` section should mirror the variables in your `.env` file.

        {
          "mcpServers": {
            "nexdav-mcp": {
              "command": "python",
              "args": ["/absolute/path/to/your/mcp-caldav-server/server.py"], // Adjusted path for clarity
              "env": {
                "CALDAV_ACCOUNTS": "[{\"url\": \"https://your-nextcloud-instance.com/remote.php/dav/calendars/YOUR_USERNAME/\", \"username\": \"your_nextcloud_username\", \"password\": \"your_nextcloud_app_password\"}]"
              }
            }
          }
        }
    **IMPORTANT:** Replace `/absolute/path/to/your/mcp-caldav-server/server.py` with the actual full path where you have placed the `server.py` file on your system (e.g., `C:\\path\\to\\your\\mcp-caldav-server\\server.py` for Windows).

3.  **Restart your `mcp-superassistant-proxy`** (and potentially Claude Desktop) for the changes to take effect.

## Usage with Claude
Once integrated, Claude will be able to discover and use the tools provided by this MCP server. You can instruct Claude to:
- "List my CalDAV calendars."
- "Show me events in my 'Personal Calendar' for next week."
- "Create an event called 'Team Meeting' tomorrow at 10 AM in my 'Work Calendar'."
- "Delete the event at [event URL]."
- "List my tasks from the 'Work Tasks' calendar."
- "Create a task called 'Submit report' in my 'Work Tasks' calendar due next Friday."
- "Mark task [task URL] as completed."

*(Note: Claude's ability to interpret natural language into iCalendar content for creating/updating events/tasks will depend on Claude's own capabilities and how it's prompted. You might need to provide specific details or even raw iCalendar strings depending on the complexity.)*

## Tools Exposed

The following tools are exposed by this MCP server. All tools include improved error handling for CalDAV server connection issues and will return an error message if the server cannot be reached or authentication fails. Errors related to invalid input (like malformed iCalendar data) are also reported.

-   `caldav-nextcloud.list_caldav_calendars()`
    -   Retrieves a list of all calendars accessible to the configured CalDAV accounts. Each calendar object returned will include an `account_identifier` field, which is the URL of the account the calendar belongs to. This identifier is crucial for subsequent operations.
-   `caldav-nextcloud.list_caldav_events(account_identifier: str, calendar_url: str, start_date: str = None, end_date: str = None)`
    -   Lists events from a specific calendar of a specific account. Uses the `account_identifier` (obtained from `list_caldav_calendars`) to select the CalDAV account. Dates should be 'YYYY-MM-DD' and are treated as UTC.
-   `caldav-nextcloud.create_caldav_event(account_identifier: str, calendar_url: str, ical_content: str)`
    -   Creates a new event in a specific calendar of a specific account. Uses `account_identifier`. Validates `ical_content`.
-   `caldav-nextcloud.update_caldav_event(account_identifier: str, event_url: str, ical_content: str)`
    -   Updates an existing event in a specific account. Uses `account_identifier`. Validates `ical_content`.
-   `caldav-nextcloud.delete_caldav_event(account_identifier: str, event_url: str)`
    -   Deletes an event from a specific account by its URL. Uses `account_identifier`.
-   `caldav-nextcloud.list_caldav_tasks(account_identifier: str, calendar_url: str, include_completed: bool = False)`
    -   Lists tasks (VTODOs) from a specific calendar of a specific account. Uses `account_identifier`. `include_completed` is optional.
-   `caldav-nextcloud.create_caldav_task(account_identifier: str, calendar_url: str, ical_content: str)`
    -   Creates a new task in a specific account. Uses `account_identifier`. Validates `ical_content`.
-   `caldav-nextcloud.update_caldav_task(account_identifier: str, task_url: str, ical_content: str)`
    -   Updates an existing task in a specific account. Uses `account_identifier`. Validates `ical_content`.
-   `caldav-nextcloud.delete_caldav_task(account_identifier: str, task_url: str)`
    -   Deletes a task from a specific account by its URL. Uses `account_identifier`.

## API Documentation

### Overview
This API provides a way for MCP (Model Context Protocol) clients, such as Claude, to interact with a CalDAV server, with a specific focus on Nextcloud Calendar integration. It allows for managing calendar events and tasks. The API is structured around a set of tools (endpoints) that perform specific actions like listing calendars, creating events, or deleting tasks.

### Authentication
Authentication with the CalDAV server(s) is handled via the `CALDAV_ACCOUNTS` environment variable loaded by the server at startup.
-   `CALDAV_ACCOUNTS`: This is a JSON string representing a list of account objects. Each object in the list must define:
    -   `"url"`: The base URL of the CalDAV server for that account (e.g., `https://your-nextcloud-instance.com/remote.php/dav/calendars/YOUR_USERNAME/`).
    -   `"username"`: The CalDAV username for that account.
    -   `"password"`: The CalDAV password (or app-specific password) for that account.

    Example structure for `CALDAV_ACCOUNTS` in your `.env` file:
        CALDAV_ACCOUNTS='[
          {"url": "https://primary-caldav.example.com/dav/", "username": "user1", "password": "password1"},
          {"url": "https://secondary-caldav.example.org/dav/users/user2/", "username": "user2", "password": "password2"}
        ]'

It is **strongly recommended** to use an "App Password" (if your CalDAV provider supports it, like Nextcloud) for the password field of each account. This enhances security by limiting the scope of the password and allowing it to be revoked independently.

Refer to the "Setup Instructions" section for details on configuring the `.env` file.

### Error Handling
The API uses a consistent JSON format for error responses:

    {
        "status": "error",
        "message": "A descriptive error message..."
    }

Common error types include:

-   **`CalDAVConnectionError`**: Issues connecting to the CalDAV server or authentication failures (e.g., incorrect URL, username, or password).
    Example:
        {
            "status": "error",
            "message": "CalDAV connection error: Authentication failed for user your_username"
        }
    *(Note: For `list_caldav_calendars`, `list_caldav_events`, and `list_caldav_tasks` which return a list, the error might be wrapped in a list: `[{"status": "error", "message": "..."}]`)*

-   **`ValueError`**: Typically occurs when invalid iCalendar content is provided to create or update operations.
    Example:
        {
            "status": "error",
            "message": "Invalid iCalendar content: The VCALENDAR component was not found."
        }

-   **Generic Unexpected Errors**: For any other server-side issues.
    Example:
        {
            "status": "error",
            "message": "An unexpected error occurred: details of the error"
        }

### Endpoints (Tools)

#### `caldav-nextcloud.list_caldav_calendars()`
-   **Description:** Retrieves a list of all calendars accessible to the configured CalDAV accounts. This is typically the first call an MCP client would make to discover available calendars and their `account_identifier`.
-   **MCP Tool Name:** `caldav-nextcloud.list_caldav_calendars`
-   **Parameters:** None.
-   **Successful Response:** A list of JSON objects, where each object represents a calendar. Each calendar object now includes an `account_identifier` field, which is the URL of the CalDAV account it belongs to. This identifier is required for all other operations.
    Example:
        [
            {
                "name": "Personal",
                "url": "https://your-nextcloud.com/remote.php/dav/calendars/username/personal/",
                "account_identifier": "https://your-nextcloud.com/remote.php/dav/calendars/YOUR_USERNAME/"
            },
            {
                "name": "Work",
                "url": "https://your-nextcloud.com/remote.php/dav/calendars/username/work_calendar/",
                "account_identifier": "https://your-nextcloud.com/remote.php/dav/calendars/YOUR_USERNAME/"
            },
            {
                "name": "User2 Calendar",
                "url": "https://another-caldav-server.com/dav/principals/users/another_user/calendar1/",
                "account_identifier": "https://another-caldav-server.com/dav/principals/users/another_user/"
            }
        ]
-   **Error Responses:** Refer to the general "Error Handling" section for connection errors. If individual accounts fail, errors are logged, and calendars from accessible accounts are returned. If all accounts fail or none are configured, an empty list may be returned or an error if appropriate.
-   **Example Usage (Conceptual):** An MCP client calls this tool to get a list of all calendars from all accounts. The user might then be prompted to choose a calendar, and the client would store its `url` and `account_identifier` for subsequent operations.

#### `caldav-nextcloud.list_caldav_events()`
-   **Description:** Fetches events from a specified calendar of a specific account, within an optional date range. If no date range is provided, it defaults to fetching events from 30 days ago to 1 year from the current date.
-   **MCP Tool Name:** `caldav-nextcloud.list_caldav_events`
-   **Parameters:**
    -   `account_identifier` (str): The URL of the CalDAV account this calendar belongs to. Obtained from `list_caldav_calendars` output.
    -   `calendar_url` (str): The absolute URL of the calendar to query. This URL is obtained from the `list_caldav_calendars` tool.
    -   `start_date` (str, optional): The start date for filtering events, in 'YYYY-MM-DD' format (e.g., "2023-01-01"). Dates are treated as UTC. Defaults to 30 days ago if not provided.
    -   `end_date` (str, optional): The end date for filtering events, in 'YYYY-MM-DD' format (e.g., "2023-12-31"). Dates are treated as UTC. Defaults to 1 year from the current date if not provided.
-   **Successful Response:** A list of JSON objects, where each object represents an event and contains its URL and raw iCalendar data.
    Example:
        [
            {
                "url": "https://your-nextcloud.com/remote.php/dav/calendars/username/personal/event1.ics",
                "data": "BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//Nextcloud Tasks v0.9.5\r\nBEGIN:VEVENT\r\nUID:unique-id-123\r\nSUMMARY:Team Meeting\r\nDTSTART;VALUE=DATE-TIME:20240315T100000Z\r\nDTEND;VALUE=DATE-TIME:20240315T110000Z\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n"
            }
        ]
-   **Error Responses:** Refer to the general "Error Handling" section for connection errors. The error response will be a list containing a single error object.
-   **Example Usage (Conceptual):** After selecting a calendar, an MCP client uses this tool to list events for "next week" by providing the calendar's URL and calculated `start_date` and `end_date` for the upcoming week.

#### `caldav-nextcloud.create_caldav_event()`
-   **Description:** Creates a new event in a specified calendar of a specific account, using a full iCalendar (VCS) string. The server validates the iCalendar content before processing.
-   **MCP Tool Name:** `caldav-nextcloud.create_caldav_event`
-   **Parameters:**
    -   `account_identifier` (str): The URL of the CalDAV account.
    -   `calendar_url` (str): The absolute URL of the calendar where the event will be created.
    -   `ical_content` (str): The full iCalendar string for the event. This should be a complete `BEGIN:VCALENDAR ... END:VCALENDAR` block containing one `VEVENT`.
        Example iCalendar content:
            BEGIN:VCALENDAR
            VERSION:2.0
            PRODID:-//MyClient//EN
            BEGIN:VEVENT
            UID:event-uid-@example.com
            SUMMARY:Doctor Appointment
            DTSTAMP:20240310T120000Z
            DTSTART:20240320T140000Z
            DTEND:20240320T150000Z
            END:VEVENT
            END:VCALENDAR
-   **Successful Response:** A JSON object indicating success and providing the URL of the newly created event.
    Example:
        {
            "status": "success",
            "event_url": "https://your-nextcloud.com/remote.php/dav/calendars/username/personal/new_event_random_id.ics"
        }
-   **Error Responses:**
    -   "Invalid iCalendar content": If the provided `ical_content` is malformed or not parsable.
    -   Refer to the general "Error Handling" section for connection errors.
-   **Example Usage (Conceptual):** An MCP client, after being asked to "Create an event for a 'Project Deadline' on March 25th, 2024, all day", would construct the appropriate `ical_content` and call this tool with the target calendar's URL.

#### `caldav-nextcloud.update_caldav_event()`
-   **Description:** Updates an existing event identified by its URL, within a specific account. The provided iCalendar content completely replaces the existing event data.
-   **MCP Tool Name:** `caldav-nextcloud.update_caldav_event`
-   **Parameters:**
    -   `account_identifier` (str): The URL of the CalDAV account.
    -   `event_url` (str): The absolute URL of the event to be updated. This is obtained from `list_caldav_events`.
    -   `ical_content` (str): The new, full iCalendar string for the event.
-   **Successful Response:** A JSON object indicating success and providing the URL of the updated event (usually the same as the input `event_url`).
    Example:
        {
            "status": "success",
            "event_url": "https://your-nextcloud.com/remote.php/dav/calendars/username/personal/event1.ics"
        }
-   **Error Responses:**
    -   "Invalid iCalendar content": If the provided `ical_content` is malformed.
    -   Refer to the general "Error Handling" section for connection errors.
-   **Example Usage (Conceptual):** If a user wants to reschedule an event, the MCP client would first fetch the event's current `ical_content` (or just its URL), allow modifications (e.g., changing `DTSTART`/`DTEND`), and then submit the updated `ical_content` to this tool along with the event's URL.

#### `caldav-nextcloud.delete_caldav_event()`
-   **Description:** Deletes an event from a specific account's CalDAV server, identified by its URL.
-   **MCP Tool Name:** `caldav-nextcloud.delete_caldav_event`
-   **Parameters:**
    -   `account_identifier` (str): The URL of the CalDAV account.
    -   `event_url` (str): The absolute URL of the event to be deleted.
-   **Successful Response:** A JSON object indicating success and echoing the URL of the deleted event.
    Example:
        {
            "status": "success",
            "event_url": "https://your-nextcloud.com/remote.php/dav/calendars/username/personal/event_to_delete.ics"
        }
-   **Error Responses:** Refer to the general "Error Handling" section for connection errors.
-   **Example Usage (Conceptual):** User asks to "delete the 'Team Meeting' event". The MCP client, having previously listed events and identified the URL for 'Team Meeting', calls this tool with that URL.

#### `caldav-nextcloud.list_caldav_tasks()`
-   **Description:** Fetches tasks (VTODO components) from a specified calendar of a specific account. It can optionally include completed tasks. The server parses iCalendar data to accurately filter tasks by their completion status.
-   **MCP Tool Name:** `caldav-nextcloud.list_caldav_tasks`
-   **Parameters:**
    -   `account_identifier` (str): The URL of the CalDAV account.
    -   `calendar_url` (str): The absolute URL of the calendar to query.
    -   `include_completed` (bool, optional): If `True`, completed tasks are included. Defaults to `False` (only incomplete tasks are returned).
-   **Successful Response:** A list of JSON objects, where each object represents a task with its URL and raw iCalendar data (which includes a VTODO component).
    Example:
        [
            {
                "url": "https://your-nextcloud.com/remote.php/dav/calendars/username/tasks_calendar/task1.ics",
                "data": "BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//Nextcloud Tasks v0.9.5\r\nBEGIN:VTODO\r\nUID:unique-task-id-456\r\nSUMMARY:Submit Report\r\nDUE;VALUE=DATE:20240320\r\nSTATUS:NEEDS-ACTION\r\nEND:VTODO\r\nEND:VCALENDAR\r\n"
            }
        ]
-   **Error Responses:** Refer to the general "Error Handling" section for connection errors. The error response will be a list containing a single error object.
-   **Example Usage (Conceptual):** An MCP client is asked to "Show my current tasks from the 'Work Tasks' calendar". It calls this tool with the calendar's URL and `include_completed=False`.

#### `caldav-nextcloud.create_caldav_task()`
-   **Description:** Creates a new task in a specified calendar of a specific account, using a full iCalendar string. The iCalendar content must contain a VTODO component.
-   **MCP Tool Name:** `caldav-nextcloud.create_caldav_task`
-   **Parameters:**
    -   `account_identifier` (str): The URL of the CalDAV account.
    -   `calendar_url` (str): The absolute URL of the calendar where the task will be created.
    -   `ical_content` (str): The full iCalendar string for the task. This should be a complete `BEGIN:VCALENDAR ... END:VCALENDAR` block containing one `VTODO`.
        Example iCalendar content for a task:
            BEGIN:VCALENDAR
            VERSION:2.0
            PRODID:-//MyClient//EN
            BEGIN:VTODO
            UID:task-uid-@example.com
            SUMMARY:Follow up on email
            DUE;VALUE=DATE:20240322
            STATUS:NEEDS-ACTION
            END:VTODO
            END:VCALENDAR
-   **Successful Response:** A JSON object indicating success and providing the URL of the newly created task.
    Example:
        {
            "status": "success",
            "task_url": "https://your-nextcloud.com/remote.php/dav/calendars/username/tasks_calendar/new_task_xyz.ics"
        }
-   **Error Responses:**
    -   "Invalid iCalendar content": If the provided `ical_content` is malformed or does not represent a valid task.
    -   Refer to the general "Error Handling" section for connection errors.
-   **Example Usage (Conceptual):** User says, "Create a task to 'Buy groceries' due this Friday." The MCP client constructs the VTODO `ical_content` and calls this tool with the appropriate calendar URL.

#### `caldav-nextcloud.update_caldav_task()`
-   **Description:** Updates an existing task identified by its URL, within a specific account. The provided iCalendar content (containing a VTODO) completely replaces the existing task data. This can be used to mark tasks as complete, change due dates, etc.
-   **MCP Tool Name:** `caldav-nextcloud.update_caldav_task`
-   **Parameters:**
    -   `account_identifier` (str): The URL of the CalDAV account.
    -   `task_url` (str): The absolute URL of the task to be updated.
    -   `ical_content` (str): The new, full iCalendar string for the task. To mark a task as complete, the `STATUS:COMPLETED` and `COMPLETED:YYYYMMDDTHHMMSSZ` properties should be set in the VTODO component.
        Example iCalendar for a completed task:
            BEGIN:VCALENDAR
            VERSION:2.0
            PRODID:-//MyClient//EN
            BEGIN:VTODO
            UID:task-uid-@example.com
            SUMMARY:Follow up on email
            DUE;VALUE=DATE:20240322
            STATUS:COMPLETED
            COMPLETED:20240311T100000Z
            END:VTODO
            END:VCALENDAR
-   **Successful Response:** A JSON object indicating success and providing the URL of the updated task.
    Example:
        {
            "status": "success",
            "task_url": "https://your-nextcloud.com/remote.php/dav/calendars/username/tasks_calendar/task1.ics"
        }
-   **Error Responses:**
    -   "Invalid iCalendar content": If the `ical_content` is malformed.
    -   Refer to the general "Error Handling" section for connection errors.
-   **Example Usage (Conceptual):** To mark a task as completed, the MCP client fetches the task's URL, then constructs a new `ical_content` with `STATUS:COMPLETED` and a `COMPLETED` timestamp, and calls this tool.

#### `caldav-nextcloud.delete_caldav_task()`
-   **Description:** Deletes a task from a specific account's CalDAV server, identified by its URL.
-   **MCP Tool Name:** `caldav-nextcloud.delete_caldav_task`
-   **Parameters:**
    -   `account_identifier` (str): The URL of the CalDAV account.
    -   `task_url` (str): The absolute URL of the task to be deleted.
-   **Successful Response:** A JSON object indicating success and echoing the URL of the deleted task.
    Example:
        {
            "status": "success",
            "task_url": "https://your-nextcloud.com/remote.php/dav/calendars/username/tasks_calendar/task_to_delete.ics"
        }
-   **Error Responses:** Refer to the general "Error Handling" section for connection errors.
-   **Example Usage (Conceptual):** User asks to "delete the task 'Submit Report'". The MCP client, having identified the task's URL, calls this tool.

## Project Structure

    mcp-caldav-server/
    ├── .env                  # Your actual environment variables (ignored by git)
    ├── .env.example          # Example environment variables for setup
    ├── caldav_service.py     # Core logic for CalDAV interactions using the 'caldav' library
    ├── server.py             # Main MCP server entry point and tool definitions using FastMCP
    ├── requirements.txt      # Python dependencies for the project
    └── README.md             # This documentation file

## Logging
The server uses Python's built-in `logging` module to record its operations.
-   **Output:** By default, logs are output to standard output (stdout).
-   **Level:** The default logging level is `INFO`. This includes informational messages about tool calls, successful operations, and errors.
-   **Format:** Log messages typically include a timestamp, log level, logger name (module), and the message itself (e.g., `2023-10-27 10:00:00,123 - INFO - server - Tool 'list_caldav_calendars' called.`).
-   **Purpose:** These logs are helpful for monitoring server activity, debugging, and diagnosing issues. For critical errors, stack trace information is also logged.

## Contributing
Contributions are welcome! Please feel free to open issues or submit pull requests.

## License
This project is open-sourced under the [MIT License](LICENSE). (You might want to create a LICENSE file if you are making this a public repo.)