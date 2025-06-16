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
- [Project Structure](#project-structure)
- [Contributing](#contributing)
- [License](#license)

## Features
- **List Calendars:** Retrieve a list of all available calendars for the configured user.
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
2.  **Edit `.env`:** Open the newly created `.env` file and fill in your actual Nextcloud CalDAV credentials:
        # .env
        CALDAV_URL="https://your-nextcloud-instance.com/remote.php/dav/calendars/YOUR_USERNAME/"
        CALDAV_USERNAME="your_nextcloud_username"
        CALDAV_PASSWORD="your_nextcloud_app_password"
    *   **`CALDAV_URL`**: This is the base URL for your CalDAV calendar. You can usually find this in your Nextcloud Calendar settings (e.g., under "CalDAV primary URL" or "WebDAV / CalDAV"). Remember to include your username in the path as shown in the example.
    *   **`CALDAV_USERNAME`**: Your Nextcloud login username.
    *   **`CALDAV_PASSWORD`**: **Strongly recommended:** Use an "App password" generated in your Nextcloud user security settings. This limits the scope of the password and can be revoked independently.

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
              "args": ["C:/MCP/Servers/Dev/nexdav/server.py"],
              "env": {
                "CALDAV_URL": "https://your-nextcloud-instance.com/remote.php/dav/calendars/YOUR_USERNAME/",
                "CALDAV_USERNAME": "your_nextcloud_username",
                "CALDAV_PASSWORD": "your_nextcloud_app_password"
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
    -   Lists all calendars accessible to the configured user.
-   `caldav-nextcloud.list_caldav_events(calendar_url: str, start_date: str = None, end_date: str = None)`
    -   Lists events from a specific calendar. Dates should be 'YYYY-MM-DD'. Input dates are treated as UTC.
-   `caldav-nextcloud.create_caldav_event(calendar_url: str, ical_content: str)`
    -   Creates a new event with a full iCalendar string. Validates the provided `ical_content`. Returns an error if the content is not parsable.
-   `caldav-nextcloud.update_caldav_event(event_url: str, ical_content: str)`
    -   Updates an existing event with a full iCalendar string. Validates the provided `ical_content`. Returns an error if the content is not parsable.
-   `caldav-nextcloud.delete_caldav_event(event_url: str)`
    -   Deletes an event by its URL.
-   `caldav-nextcloud.list_caldav_tasks(calendar_url: str, include_completed: bool = False)`
    -   Lists tasks (VTODOs) from a specific calendar. `include_completed` is optional. Uses iCalendar parsing for accurate status filtering.
-   `caldav-nextcloud.create_caldav_task(calendar_url: str, ical_content: str)`
    -   Creates a new task with a full iCalendar string (VTODO). Validates the provided `ical_content`. Returns an error if the content is not parsable.
-   `caldav-nextcloud.update_caldav_task(task_url: str, ical_content: str)`
    -   Updates an existing task with a full iCalendar string (VTODO). Validates the provided `ical_content`. Returns an error if the content is not parsable.
-   `caldav-nextcloud.delete_caldav_task(task_url: str)`
    -   Deletes a task by its URL.

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