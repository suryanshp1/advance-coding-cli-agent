# AI Coding Agent

A powerful, terminal-based AI coding assistant designed to help developers write, debug, and understand code more efficiently. Built with Python, it offers both an interactive TUI (Terminal User Interface) and a single-command CLI mode.

## Features

-   **Interactive TUI**: A rich, interactive terminal interface for continuous pair programming sessions.
-   **CLI Mode**: Execute single instructions directly from the command line.
-   **Tool Integration**: Built-in tools for file operations, web search, and shell execution.
-   **MCP Support**: Implements the **Model Context Protocol (MCP)**, allowing connection to external MCP servers to extend capabilities.
-   **Lifecycle Hooks**: Define custom commands or scripts to run before/after the agent or specific tools (e.g., auto-formatting, linting).
-   **Custom Subagents**: configure specialized AI subagents for distinct tasks (e.g., "Security Auditor", "Test Generator").
-   **Configurable**: Flexible configuration via `.env` (credentials) and `config.toml` (behavior).
-   **Safety Modes**: Verified execution with multiple approval policies (Auto, On Request, etc.).

## Installation

### Prerequisites
-   Python 3.10+
-   Git

### Steps

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/yourusername/coding-agent-py.git
    cd coding-agent-py
    ```

2.  **Create a virtual environment:**
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate  # On Windows: .venv\Scripts\activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Install the project in editable mode (optional but recommended):**
    ```bash
    pip install -e .
    ```

## Configuration

The agent uses a combination of environment variables for credentials and TOML files for behavioral configuration.

### 1. Credentials (`.env`)
Create a `.env` file in the project root:

```bash
cp .example.env .env
```

Edit `.env` to add your LLM provider details:
```ini
API_KEY=your_api_key_here
BASE_URL=https://openrouter.ai/api/v1  # or https://api.openai.com/v1
```

### 2. Behavior (`config.toml`)
The agent looks for `config.toml` in:
-   Global: User config directory (e.g., `~/.config/ai-agent/config.toml`)
-   Project: `.ai-agent/config.toml` in your current working directory.

**Example `config.toml`:**

```toml
[model]
name = "claude-3-5-sonnet-20240620"
temperature = 0.0
context_window = 200000

# Approval Policy: on_request, auto, never, yolo
approval = "on_request" 

[shell_environment]
# secure environment variables for shell tools
exclude_patterns = ["*TOKEN*", "*KEY*"]

[[mcp_servers]]
# Example: Connect to a local MCP server
name = "filesystem-server"
command = "npx"
args = ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/allowed/dir"]
```

## Usage

### Interactive Mode (TUI)
Start the interactive session:
```bash
python main.py
```
This launches the TUI where you can chat with the agent, view tool outputs, and manage the session.

### Single Command Mode (CLI)
Run a specific task and exit:
```bash
python main.py "Refactor utility.py to use type hints"
```

### Developer Instructions
Create an `agent.md` file in your directory to provide custom context or instructions that the agent will always read on startup.

## Tools

The agent comes with a suite of built-in tools:

-   **File Operations**: `read_file`, `write_file`, `edit_file`, `list_dir`, `delete_file`.
-   **Search**: `grep` (text search), `glob` (file pattern match).
-   **Web**: `web_search` (Search engine), `web_fetch` (Read URL content).
-   **Shell**: `run_command` (Execute shell commands).
-   **Memory**: `todo` (Manage a task list).

## Advanced Features

### Model Context Protocol (MCP)
Support for MCP allows you to connect the agent to external data sources and tools standard to the MCP ecosystem. Define servers in `config.toml`.

### Lifecycle Hooks
Automate workflows by triggering commands at specific events.

**Example in `config.toml`:**
```toml
[[hooks]]
name = "pre-commit-check"
trigger = "after_agent"
command = "pre-commit run --all-files"
```

### Subagents
Define specialized personas in `config.toml`.

```toml
[[subagents]]
name = "qa_engineer"
description = "Writes comprehensive unit tests"
model = "gpt-4o"
system_prompt = "You are an expert QA engineer..."
allowed_tools = ["read_file", "write_file", "run_command"]
```

Invoke them in the chat:
> "Ask the qa_engineer to write tests for this module."

## Project Structure

-   `main.py`: Entry point.
-   `agent/`: Core logic (Agent, Session, Event Loop).
-   `config/`: Configuration loading (Env & TOML).
-   `tools/`: Built-in tools implementation.
-   `client/`: LLM API client.
-   `ui/`: Terminal User Interface (Rich-based).

## License

MIT License. See [LICENSE](LICENSE) for details.
