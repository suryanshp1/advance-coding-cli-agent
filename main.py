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
from config.config import Config, ApprovalPolicy
from utils.errors import ConfigError
from agent.persistence import PersistenceManager, SessionSnapshot
from agent.session import Session

console = get_console()


class CLI:
    def __init__(self, config: Config):
        self.agent: Agent | None = None
        self.tui = TUI(config=config, console=console)
        self.config = config

    async def run_single(self, message: str) -> str | None:
        async with Agent(config=self.config) as agent:
            self.agent = agent
            return await self._process_message(message)

    async def run_interactive(self) -> str | None:
        self.tui.print_welcome(
            "AI Coding Agent",
            [
                f"model: {self.config.model_name}",
                f"cwd: {self.config.cwd}",
                "commands: /exit /help /config /approval /model",
            ],
        )
        async with Agent(
            config=self.config,
            confirmation_callback=self.tui.handle_confirmation,
        ) as agent:
            self.agent = agent

            while True:
                try:
                    user_input = console.input("\n[user]>[/user] ").strip()
                    if not user_input:
                        continue
                    if user_input.startswith("/"):
                        should_continue = await self._handle_command(user_input)
                        if not should_continue:
                            break
                        continue

                    await self._process_message(user_input)
                except KeyboardInterrupt:
                    console.print("\n[dim]Use /exit to quit.[/dim]")
                except EOFError:
                    break

        console.print("\n[dim]Goodbye![/dim]")

    def _get_tool_kind(self, tool_name: str) -> str | None:
        tool = self.agent.session.tool_registry.get(tool_name)
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
                    event.data.get("error"),
                    event.data.get("metadata"),
                    event.data.get("diff"),
                    event.data.get("truncated", False),
                    event.data.get("exit_code"),
                )

        return final_response

    async def _handle_command(self, command: str) -> bool:
        cmd = command.lower().strip()
        parts = command.split(maxsplit=1)
        cmd_name = parts[0]
        cmd_args = parts[1] if len(parts) > 1 else ""

        if cmd_name in ("/exit", "/quit", "/q"):
            return False
        elif command in ("/help", "/h"):
            self.tui.show_help()
        elif command == "/clear":
            self.agent.session.context_manager.clear()
            self.agent.session.loop_detector.clear()
            console.print("[success]Conversation cleared.[/success]")
        elif command == "/config":
            console.print("\n[bold]Current Configuration[/bold]")
            console.print(f"  Model: {self.config.model_name}")
            console.print(f"  Temperature: {self.config.temperature}")
            console.print(f"  Approval: {self.config.approval.value}")
            console.print(f"  Working Dir: {self.config.cwd}")
            console.print(f"  Max Turns: {self.config.max_turns}")
            console.print(f"  Hooks Enabled: {self.config.hooks_enabled}")
        elif cmd_name == "/model":
            if cmd_args:
                self.config.model_name = cmd_args
                console.print(
                    f"[success]Model changed to {self.config.model_name}[/success]"
                )
            else:
                console.print(f"[info]Current model: {self.config.model_name}[/info]")
        elif cmd_name == "/approval":
            if cmd_args:
                try:
                    approval = ApprovalPolicy(cmd_args)
                    self.config.approval = approval
                    console.print(
                        f"[success]Approval policy changed to {self.config.approval.value}[/success]"
                    )
                except:
                    console.print(f"[error]Invalid approval policy: {cmd_args}[/error]")
                    console.print(
                        "Valid policies are: ",
                        [policy.value for policy in ApprovalPolicy],
                    )
            else:
                console.print(
                    f"[info]Current approval policy: {self.config.approval.value}[/info]"
                )
        elif cmd_name == "/temperature":
            if cmd_args:
                self.config.temperature = float(cmd_args)
                console.print(
                    f"[success]Temperature changed to {self.config.temperature}[/success]"
                )
            else:
                console.print(
                    f"[info]Current temperature: {self.config.temperature}[/info]"
                )
        elif cmd_name == "/max_turns":
            if cmd_args:
                self.config.max_turns = int(cmd_args)
                console.print(
                    f"[success]Max turns changed to {self.config.max_turns}[/success]"
                )
            else:
                console.print(
                    f"[info]Current max turns: {self.config.max_turns}[/info]"
                )
        elif cmd_name == "/hooks":
            if cmd_args:
                self.config.hooks_enabled = cmd_args.lower() in ("true", "1", "t")
                console.print(
                    f"[success]Hooks enabled: {self.config.hooks_enabled}[/success]"
                )
            else:
                console.print(
                    f"[info]Current hooks enabled: {self.config.hooks_enabled}[/info]"
                )
        elif cmd_name == "/stats":
            stats = self.agent.session.get_stats()
            console.print(f"[bold]Session Stats[/bold]")
            console.print(f"  Turn Count: {stats['turn_count']}")
            console.print(f"  Message Count: {stats['message_count']}")
            console.print(f"  Token Usage: {stats['token_usage']}")
            console.print(f"  Tools Count: {stats['tools_count']}")
            console.print(f"  MCP Tools Count: {stats['mcp_tools_count']}")
            console.print(f"  Session ID: {stats['session_id']}")
            console.print(f"  Created At: {stats['created_at']}")
            console.print(f"  Updated At: {stats['updated_at']}")
        elif cmd_name == "/tools":
            tools = self.agent.session.tool_registry.get_tools()
            console.print(f"[bold]Tools ({len(tools)})[/bold]")
            for tool in tools:
                console.print(f"  • {tool.name}: {tool.description}\n")
        elif cmd_name == "/mcp":
            mcp_servers = self.agent.session.mcp_manager.get_all_servers
            console.print(f"[bold]MCP Servers ({len(mcp_servers)})[/bold]")
            for server in mcp_servers:
                status_color = "green" if server["status"] == "connected" else "red"
                console.print(
                    f"  • {server['name']}: [{status_color}]{server['status']}[/{status_color}]: {server['tools_count']} tools\n"
                )
        elif cmd_name == "/save":
            persistence_manager = PersistenceManager()
            session_snapshot = SessionSnapshot(
                session_id=self.agent.session.session_id,
                created_at=self.agent.session.created_at,
                updated_at=self.agent.session.updated_at,
                turn_count=self.agent.session.turn_count,
                messages=self.agent.session.context_manager.get_messages(),
                total_usage=self.agent.session.context_manager.total_token_usage,
            )
            persistence_manager.save_session(session_snapshot)
            console.print(
                f"[success]Session saved: {session_snapshot.session_id}[/success]"
            )
        elif cmd_name == "/sessions":
            persistence_manager = PersistenceManager()
            sessions = persistence_manager.list_sessions()
            console.print(f"[bold]Saved sessions ({len(sessions)})[/bold]")
            for session in sessions:
                console.print(f"  • {session}")
        elif cmd_name == "/resume":
            if not cmd_args:
                console.print("[error]Session ID is required[/error]")
                console.print("Usage: /resume <session_id>")
                return False

            persistence_manager = PersistenceManager()
            session_snapshot = persistence_manager.load_session(cmd_args)
            if not session_snapshot:
                console.print("[error]Session not found[/error]")
            else:

                session = Session(
                    config=self.config,
                )
                await session.initialize()
                session.session_id = session_snapshot.session_id
                session.created_at = session_snapshot.created_at
                session.updated_at = session_snapshot.updated_at
                session.turn_count = session_snapshot.turn_count
                session.context_manager.total_token_usage = session_snapshot.total_usage
                for msg in session_snapshot.messages:
                    if msg.get("role") == "system":
                        continue
                    elif msg.get("role") == "user":
                        session.context_manager.add_user_message(msg.get("content", ""))
                    elif msg.get("role") == "assistant":
                        session.context_manager.add_assistant_message(
                            msg.get("content", ""), msg.get("tool_calls", [])
                        )
                    elif msg.get("role") == "tool":
                        session.context_manager.add_tool_result(
                            msg.get("tool_call_id", ""), msg.get("content", "")
                        )

                await self.agent.session.llm_client.close()
                await self.agent.session.mcp_manager.shutdown()
                self.agent.session = session

                console.print(
                    f"[success]Session resumed: {session_snapshot.session_id}[/success]"
                )

        elif cmd_name == "/checkpoint":
            persistence_manager = PersistenceManager()
            session_snapshot = SessionSnapshot(
                session_id=self.agent.session.session_id,
                created_at=self.agent.session.created_at,
                updated_at=self.agent.session.updated_at,
                turn_count=self.agent.session.turn_count,
                messages=self.agent.session.context_manager.get_messages(),
                total_usage=self.agent.session.context_manager.total_token_usage,
            )
            checkpoint_id = persistence_manager.save_checkpoint(session_snapshot)
            console.print(f"[success]Checkpoint created: {checkpoint_id}[/success]")
        elif cmd_name == "/checkpoints":
            persistence_manager = PersistenceManager()
            checkpoints = persistence_manager.list_checkpoints(self.agent.session.session_id)
            console.print(f"[bold]Checkpoints ({len(checkpoints)})[/bold]")
            for checkpoint in checkpoints:
                console.print(f"  • {checkpoint}")

        elif cmd_name == "/restore":
            persistence_manager = PersistenceManager()
            if not cmd_args:
                console.print("[error]Checkpoint ID is required[/error]")
                console.print("Usage: /restore <checkpoint_id>")
                return False
            session_snapshot = persistence_manager.load_checkpoint(cmd_args)
            if not session_snapshot:
                console.print("[error]Checkpoint not found[/error]")
            else:
                session = Session(
                    config=self.config,
                )
                await session.initialize()
                session.session_id = session_snapshot.session_id
                session.created_at = session_snapshot.created_at
                session.updated_at = session_snapshot.updated_at
                session.turn_count = session_snapshot.turn_count
                session.context_manager.total_token_usage = session_snapshot.total_usage
                for msg in session_snapshot.messages:
                    if msg.get("role") == "system":
                        continue
                    elif msg.get("role") == "user":
                        session.context_manager.add_user_message(msg.get("content", ""))
                    elif msg.get("role") == "assistant":
                        session.context_manager.add_assistant_message(
                            msg.get("content", ""), msg.get("tool_calls", [])
                        )
                    elif msg.get("role") == "tool":
                        session.context_manager.add_tool_result(
                            msg.get("tool_call_id", ""), msg.get("content", "")
                        )

                await self.agent.session.llm_client.close()
                await self.agent.session.mcp_manager.shutdown()
                self.agent.session = session

                console.print(
                    f"[success]Checkpoint restored: {cmd_args}[/success]"
                )

        else:
            console.print(f"[error]Unknown command: {cmd_name}[/error]")

        return True


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

    errors = config.validate()
    if errors:
        for error in errors:
            console.print(f"[error]{error}[/error]")
        sys.exit(1)

    cli = CLI(config=config)

    if prompt:
        result = asyncio.run(cli.run_single(prompt))
        if result is None:
            sys.exit(1)
    else:
        asyncio.run(cli.run_interactive())


if __name__ == "__main__":
    main()
