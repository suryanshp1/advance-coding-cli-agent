import asyncio
import click
from typing import Any
from agent.agent import Agent
from ui.tui import TUI
import sys
from agent.events import AgentEventType
from ui.tui import get_console
from pathlib import Path
from config.loader import load_config
from config.config import Config

console = get_console()


class CLI:
    def __init__(self):
        self.agent: Agent | None = None
        self.tui = TUI(console=console)
        self.config = Config()

    async def run_single(self, message: str) -> str | None:
        async with Agent() as agent:
            self.agent = agent
            return await self._process_message(message)

    async def run_interactive(self) -> str | None:
        self.tui.print_welcome(
            "AI Coding Agent",
            [
                f"model: {self.config.model_name}",
                f"cwd: {Path.cwd()}",
                "commands: /exit /help /config /approval /model",
            ],
        )
        async with Agent() as agent:
            self.agent = agent

            while True:
                try:
                    message = console.input("\n[user]>[/user] ").strip()
                    if not message:
                        continue
                    if message == "/exit":
                        break
                    await self._process_message(message)
                except KeyboardInterrupt:
                    console.print("\n[dim]Use /exit to quit.[/dim]")
                except EOFError:
                    break

        console.print("\n[dim]Goodbye![/dim]")

    def _get_tool_kind(self, tool_name: str) -> str | None:
        tool = self.agent.tool_registry.get(tool_name)
        if not tool:
            return None
        return tool.kind.value

    async def _process_message(self, message: str) -> str | None:
        if not self.agent:
            return None

        assistant_streaming = False

        final_response: str | None = None

        async for event in self.agent.run(message):
            if event.type == AgentEventType.TEXT_DELTA:
                content = event.data.get("content", "")
                if not assistant_streaming:
                    self.tui.begin_assistant()
                    assistant_streaming = True
                self.tui.stream_assistant_delta(content)
            elif event.type == AgentEventType.TEXT_COMPLETE:
                final_response = event.data.get("content", "")
                if assistant_streaming:
                    self.tui.end_assistant()
                    assistant_streaming = False
            elif event.type == AgentEventType.AGENT_ERROR:
                error = event.data.get("error", "Unknown error")
                console.print(f"\n[error]Error: {error}[/error]")
            elif event.type == AgentEventType.TOOL_CALL_START:
                tool_name = event.data.get("name", "unknown")
                tool_kind = self._get_tool_kind(tool_name)
                self.tui.tool_call_start(
                    event.data.get("call_id", ""),
                    tool_name,
                    tool_kind,
                    event.data.get("arguments", {}),
                )
            elif event.type == AgentEventType.TOOL_CALL_COMPLETE:
                tool_name = event.data.get("name", "unknown")
                tool_kind = self._get_tool_kind(tool_name)
                self.tui.tool_call_complete(
                    event.data.get("call_id", ""),
                    tool_name,
                    tool_kind,
                    event.data.get("success", False),
                    event.data.get("output", ""),
                    event.data.get("error", None),
                    event.data.get("metadata", None),
                    event.data.get("truncated", False),
                )

        return final_response


@click.command()
@click.argument("prompt", required=False)
@click.option(
    "--cwd",
    "-c",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    default=Path.cwd(),
    help="Current working directory",
)
def main(prompt: str | None = None, cwd: Path | None = None):
    
    try:
        config = load_config(cwd=cwd)
    except ConfigError as e:
        console.print(f"[error]Error: {e}[/error]")
        sys.exit(1)
    
    # messages=[
    #     {"role": "user", "content": prompt}
    # ]

    errors = config.validate()
    if errors:
        for error in errors:
            console.print(f"[error]{error}[/error]")
        sys.exit(1)
    
    cli = CLI()
    
    if prompt:
        result = asyncio.run(cli.run_single(prompt))
        if result is None:
            sys.exit(1)
    else:
        asyncio.run(cli.run_interactive())


if __name__ == "__main__":
    main()
