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

## Detailed Installation Guide (for Beginners)

This guide will walk you through setting up the MCP CalDAV Nextcloud Integration Server on your computer.

**Part 1: Prerequisites (Things you need first)**

1.  **Install Python (if you don't have it):**
    *   This server needs Python to run. Version 3.9 or newer is recommended.
    *   **How to check if you have Python:** Open your terminal (Command Prompt on Windows, Terminal on macOS/Linux) and type `python --version` or `python3 --version`. If you see a version like "Python 3.9.x", you're good.
    *   **How to install Python:** If you don't have it, download it from the official Python website: [https://www.python.org/downloads/](https://www.python.org/downloads/). Make sure to check the box that says "Add Python to PATH" during installation on Windows.

2.  **Access to a Nextcloud Instance:**
    *   You need a Nextcloud account with a calendar you want to connect to.
    *   You'll also need an "App Password" from Nextcloud for better security.
        *   Log into your Nextcloud.
        *   Go to Settings -> Security.
        *   Under "App passwords" or "Devices & sessions", create a new app password (e.g., name it `mcp-caldav-server`). Note this password down securely; you'll need it soon.

**Part 2: Setting up the Server Code**

1.  **Get the Server Code:**
    *   **If it's a Git repository (e.g., from GitHub):**
        *   You'll need Git installed. If you don't have it, search "install git" for your operating system.
        *   Open your terminal.
        *   Navigate to where you want to store the server (e.g., `cd Documents`).
        *   Clone the repository: `git clone <repository_url>` (replace `<repository_url>` with the actual URL of this project).
        *   Change into the new directory: `cd mcp-caldav-server` (or the actual folder name of the project).
    *   **If you have the files directly (e.g., downloaded as a ZIP):**
        *   Create a new folder for the server (e.g., `my-mcp-caldav-server`).
        *   Extract/copy all the server files (`.py` files, `requirements.txt`, `README.md`, etc.) into this folder.
        *   Open your terminal and navigate into this folder: `cd path/to/your/my-mcp-caldav-server`.

2.  **Create a Virtual Environment (Highly Recommended):**
    *   A virtual environment keeps the server's Python packages separate from other Python projects on your system, preventing conflicts.
    *   In your terminal, from inside the server's project folder:
        *   Run: `python -m venv venv` (or `python3 -m venv venv` if `python` points to an older version).
        *   This creates a `venv` folder inside your project.
    *   **Activate the virtual environment:**
        *   **On Windows (Command Prompt/PowerShell):** `venv\Scripts\activate`
        *   **On macOS/Linux (bash/zsh):** `source venv/bin/activate`
        *   You should see `(venv)` at the beginning of your terminal prompt. If you do, it's active!
    *   *Remember: You need to activate the virtual environment every time you open a new terminal to work on this project.*

3.  **Install Required Python Packages:**
    *   Make sure your virtual environment is active (`(venv)` should be in your prompt).
    *   In the terminal, from the project folder, run:
        `pip install -r requirements.txt`
    *   This command reads the `requirements.txt` file and installs all the necessary Python libraries for the server to run.
    *   **For development or running local tests (optional but good practice):**
        *   Also install development dependencies: `pip install -r requirements-dev.txt`
        *   This installs tools like `pytest` for running tests and `mcp[cli]` for using `mcp dev`.

4.  **Configure Environment Variables (Your Server Settings):**
    *   The server needs your Nextcloud URL, username, and the app password you created. This is stored in a file named `.env`.
    *   Find the file named `.env.example` in the project folder.
    *   **Copy `.env.example` to a new file named `.env`:**
        *   In your terminal (from the project folder):
            *   **Windows:** `copy .env.example .env`
            *   **macOS/Linux:** `cp .env.example .env`
    *   **Edit the `.env` file:** Open the newly created `.env` file with a plain text editor (like Notepad on Windows, TextEdit on Mac (in plain text mode), VS Code, Sublime Text, nano, vim).
        *   **`CALDAV_URL`**:
            *   This is usually `https://YOUR_NEXTCLOUD_DOMAIN/remote.php/dav/calendars/YOUR_USERNAME/`
            *   Replace `YOUR_NEXTCLOUD_DOMAIN` with your Nextcloud's web address (e.g., `cloud.example.com`).
            *   Replace `YOUR_USERNAME` with your actual Nextcloud username.
            *   **Example:** `CALDAV_URL="https://cloud.example.com/remote.php/dav/calendars/myuser/"`
        *   **`CALDAV_USERNAME`**:
            *   Your Nextcloud username.
            *   **Example:** `CALDAV_USERNAME="myuser"`
        *   **`CALDAV_PASSWORD`**:
            *   The **App Password** you generated in Nextcloud (from Part 1, Step 2). Do NOT use your main Nextcloud password here if you created an app password.
            *   **Example:** `CALDAV_PASSWORD="yourGeneratedAppPasswordHere"`
    *   Save and close the `.env` file. This file is ignored by Git (if you're using Git), so your credentials stay private.

**Part 3: Running and Testing the Server (Locally)**

1.  **Ensure your virtual environment is active.** (See Part 2, Step 2).
2.  **Start the Server for Development/Testing:**
    *   In your terminal, from the project folder, run:
        `mcp dev server.py`
    *   This command (part of `mcp[cli]` which you installed via `requirements-dev.txt`) will start the MCP server.
    *   You should see log messages in the terminal, including something like `INFO - __main__ - Starting MCP CalDAV Server...`.
    *   The server might also print a URL for an "MCP Inspector" (e.g., `http://localhost:62700/inspector/`). You can open this URL in your web browser to see the available tools and test them.
3.  **Stopping the Server:**
    *   Press `Ctrl+C` in the terminal where the server is running.

**Part 4: Integrating with an MCP Client (e.g., MCP SuperAssistant Proxy)**

*   This server is designed to be used by an MCP client application. The section "Integrate with MCP SuperAssistant Proxy" below provides details on how to configure your client to use this server. You'll typically need to provide the absolute path to your `server.py` file and the environment variables from your `.env` file in the client's configuration.

**Troubleshooting Common Issues:**

*   **`ModuleNotFoundError: No module named 'caldav'` (or similar for other packages like `icalendar`, `dotenv`):**
    *   **Is your virtual environment active?** You should see `(venv)` at the start of your terminal prompt. If not, activate it (see Part 2, Step 2).
    *   **Did you install dependencies?** Ensure you ran `pip install -r requirements.txt` successfully *while the virtual environment was active*.
    *   Try running `pip install -r requirements.txt` again just in case.
*   **`python: command not found`, `pip: command not found`, `git: command not found`:**
    *   These commands mean the respective program is not installed or not found in your system's PATH.
        *   For `python` or `pip`: Python might not be installed correctly or not added to your system's PATH. Revisit Part 1, Step 1.
        *   For `git`: You may need to install Git. Search online for "install git" for your operating system.
*   **`mcp: command not found`:**
    *   Ensure you ran `pip install -r requirements-dev.txt` (which includes `mcp[cli]`) while your virtual environment was active.
    *   If `mcp` is installed but still not found, sometimes you might need to run it as `python -m mcp dev server.py`.
*   **Connection Errors in Server Logs (e.g., "CalDAV connection error"):**
    *   **Double-check your `.env` file:** Carefully verify your `CALDAV_URL`, `CALDAV_USERNAME`, and `CALDAV_PASSWORD`. Typos are common!
    *   **Is your Nextcloud instance running and accessible?** Try opening your Nextcloud in a web browser.
    *   **App Password Correct?** Ensure the password in `.env` is the app password, not your main Nextcloud password.
    *   **URL Format:** Make sure the `CALDAV_URL` ends with a `/` and includes your username in the path as per the example.

## Integrate with MCP SuperAssistant Proxy
To make your new CalDAV server available to Claude, you need to configure your `mcp-superassistant-proxy` (or similar proxy setup).

1.  **Locate your proxy's configuration file.** This is often named `claude.json` or similar.
2.  **Add a new entry** under the `mcpServers` section for your `caldav-nextcloud` server.
    Ensure the `command` points to `python` and `args` points to the absolute path of your `server.py` file. The `env` section should mirror the variables in your `.env` file.

        {
          "mcpServers": {
            "brave-search": {
              "command": "npx",
              "args": ["-y", "@modelcontextprotocol/server-brave-search"],
              "env": {
                "BRAVE_API_KEY": ""
              }
            },
            "caldav-nextcloud": {
              "command": "python",
              "args": ["/absolute/path/to/your/mcp-caldav-server/server.py"],
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