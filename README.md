# AI Coding Agent

A powerful, terminal-based AI coding assistant designed to help developers write, debug, and understand code more efficiently. Built with Python, it offers both an interactive TUI (Terminal User Interface) and a single-command CLI mode.

## Features

-   **Interactive TUI**: A rich, interactive terminal interface for continuous pair programming sessions.
-   **CLI Mode**: Execute single instructions directly from the command line.
-   **Tool Integration**: Capable of reading files, listing directories, and executing other agentic actions (extensible).
-   **Configurable**: Easy configuration via environment variables and TOML files.

## Installation

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

## Configuration

1.  **Set up environment variables:**
    Copy the example environment file to `.env`:
    ```bash
    cp .example.env .env
    ```

2.  **Edit `.env`:**
    Open `.env` and add your LLM API credentials:
    ```ini
    API_KEY=your_api_key_here
    BASE_URL=https://openrouter.ai/api/v1  # or your preferred provider
    ```

## Usage

### Interactive Mode
To start an interactive session with the agent:
```bash
python main.py
```
This will launch the TUI where you can chat with the agent, ask questions, and request code changes.

### Single Command Mode
To run a specific prompt and exit:
```bash
python main.py "Analyze the current directory and list all Python files"
```

## Project Structure

-   `agent/`: Core agent logic and event handling.
-   `client/`: LLM client implementation.
-   `config/`: Configuration loading and validation.
-   `context/`: Context management for the agent.
-   `tools/`: Built-in tools (file operations, etc.).
-   `ui/`: TUI implementation using `rich`.
-   `utils/`: Helper utilities.
-   `main.py`: Entry point for the application.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
