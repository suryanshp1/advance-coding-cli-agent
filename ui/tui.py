from rich.console import Console
from rich.theme import Theme
from rich.rule import Rule
from rich.text import Text
from rich.panel import Panel
from rich.table import Table
from typing import Any, Tuple
from pathlib import Path
from utils.paths import display_path_rel_to_cwd
from rich import box
from rich.syntax import Syntax
from utils.text import truncate_text
from rich.console import Group
import re

AGENT_THEME = Theme(
    {
        # General
        "info": "cyan",
        "warning": "yellow",
        "error": "bright_red bold",
        "success": "green",
        "dim": "dim",
        "muted": "grey50",
        "border": "grey35",
        "highlight": "bold cyan",
        # Roles
        "user": "bright_blue bold",
        "assistant": "bright_white",
        # Tools
        "tool": "bright_magenta bold",
        "tool.read": "cyan",
        "tool.write": "yellow",
        "tool.shell": "magenta",
        "tool.network": "bright_blue",
        "tool.memory": "green",
        "tool.mcp": "bright_cyan",
        # Code / blocks
        "code": "white",
    }
)

_console: Console | None = None


def get_console() -> Console:
    """Get or create the global console instance."""
    global _console
    if _console is None:
        _console = Console(theme=AGENT_THEME, highlight=False)
    return _console


class TUI:
    def __init__(self, console: Console | None = None) -> None:
        self.console = console or get_console()
        self._assitant_stream_open = False
        self._tool_args_by_call_id: dict[str, dict[str, Any]] = {}
        self.cwd = Path.cwd()

    def begin_assistant(self) -> None:
        self.console.print()
        self.console.print(Rule(Text("Assistant", style="assistant")))
        self._assitant_stream_open = True

    def end_assistant(self) -> None:
        if self._assitant_stream_open:
            self.console.print()
        self._assitant_stream_open = False

    def stream_assistant_delta(self, content: str) -> None:
        self.console.print(content, end="", markup=False)

    def _ordered_args(
        self, tool_name: str, args: dict[str, Any]
    ) -> list[tuple[str, Any]]:
        _PREFERRED_ORDER = {
            "read_file": ["path", "offset", "limit"],
        }

        preferred_order = _PREFERRED_ORDER.get(tool_name, [])
        ordered: list[Tuple[str, Any]] = []
        seen = set()

        for key in preferred_order:
            if key in args:
                ordered.append((key, args[key]))
                seen.add(key)

        remaining_key = set(args.keys()) - seen
        ordered.extend((key, args[key]) for key in remaining_key)

        return ordered

    def _render_args_table(self, tool_name: str, args: dict[str, Any]) -> Table:
        table = Table.grid(padding=(0, 1))
        table.add_column(style="muted", justify="right", no_wrap=True)
        table.add_column(style="code", overflow="fold")
        for key, value in self._ordered_args(tool_name, args):
            table.add_row(key, str(value))
        return table

    def tool_call_start(
        self, call_id: str, name: str, tool_kind: str | None, arguments: dict[str, Any]
    ) -> None:
        self._tool_args_by_call_id[call_id] = arguments
        border_style = f"tool.{tool_kind}" if tool_kind else "tool"
        title = Text.assemble(
            ("⏺ ", "muted"),
            (name, "tool"),
            ("  ", "muted"),
            (f"#{call_id[:8]}", "muted"),
        )

        display_args = dict(arguments)
        for key in ("path", "cwd"):
            val = display_args.get(key)
            if isinstance(val, str) and self.cwd:
                display_args[key] = str(display_path_rel_to_cwd(val, self.cwd))

        panel = Panel(
            (
                self._render_args_table(name, display_args)
                if display_args
                else Text("(no arguments)", style="muted")
            ),
            title=title,
            padding=(1, 2),
            box=box.ROUNDED,
            border_style=border_style,
            subtitle=Text("running...", style="muted"),
            title_align="left",
            subtitle_align="right",
        )
        self.console.print()
        self.console.print(panel)

    def _extract_read_file_code(self, text: str) -> Tuple[int, str] | None:
        """
        Extracts the line range and code from a read_file tool call output.
        Showing lines x -y of z\n\n1 def main()
        """
        body = text
        header_match = re.match(r"^Showing lines (\d+)-(\d+) of (\d+)\n\n", text)
        if header_match:
            body = text[header_match.end() :]

        code_lines: list[str] = []
        start_line: int | None = None

        for line in body.splitlines():
            line_match = re.match(r"^\s*(\d+)\|(.*)$", line)
            if not line_match:
                return None

            line_no = int(line_match.group(1))
            if start_line is None:
                start_line = line_no
            code_lines.append(line_match.group(2))

        if start_line is None:
            return None

        return start_line, "\n".join(code_lines)

    def _guess_language(self, path: str | None) -> str:
        if not path:
            return "text"
        suffix = Path(path).suffix.lower()
        return {
            ".py": "python",
            ".js": "javascript",
            ".jsx": "jsx",
            ".ts": "typescript",
            ".tsx": "tsx",
            ".json": "json",
            ".toml": "toml",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".md": "markdown",
            ".sh": "bash",
            ".bash": "bash",
            ".zsh": "bash",
            ".rs": "rust",
            ".go": "go",
            ".java": "java",
            ".kt": "kotlin",
            ".swift": "swift",
            ".c": "c",
            ".h": "c",
            ".cpp": "cpp",
            ".hpp": "cpp",
            ".css": "css",
            ".html": "html",
            ".xml": "xml",
            ".sql": "sql",
        }.get(suffix, "text")

    def print_welcome(self, title: str, lines: list[str]) -> None:
        body = "\n".join(lines)
        self.console.print(
            Panel(
                Text(body, style="code"),
                title=Text(title, style="highlight"),
                title_align="left",
                border_style="border",
                box=box.ROUNDED,
                padding=(1, 2),
            )
        )

    def tool_call_complete(
        self,
        call_id: str,
        name: str,
        tool_kind: str | None,
        success: bool,
        output: str,
        error: str | None,
        metadata: dict[str, Any] | None,
        truncated: bool,
    ) -> None:
        border_style = f"tool.{tool_kind}" if tool_kind else "tool"
        status_icon = "✓" if success else "✗"
        status_style = "success" if success else "error"

        title = Text.assemble(
            (f"{status_icon} ", status_style),
            (name, "tool"),
            ("  ", "muted"),
            (f"#{call_id[:8]}", "muted"),
        )

        primary_path = None
        blocks = []
        if isinstance(metadata, dict) and isinstance(metadata.get("path"), str):
            primary_path = metadata["path"]

        if name == "read_file" and success:
            if primary_path:
                extracted = self._extract_read_file_code(output)
                if extracted:
                    start_line, code = extracted
                shown_start = None
                shown_end = None
                total_lines = None

                shown_start = metadata.get("shown_start")
                shown_end = metadata.get("shown_end")
                total_lines = metadata.get("total_lines")
                programming_language = self._guess_language(path=primary_path)

                header_parts = [display_path_rel_to_cwd(primary_path, self.cwd)]
                header_parts.append(" • ")

                if shown_start and shown_end and total_lines:
                    header_parts.append(
                        f"lines {shown_start}-{shown_end} of {total_lines}"
                    )

                header = "".join(header_parts)
                blocks.append(Text(header, style="muted"))
                blocks.append(
                    Syntax(
                        code,
                        programming_language,
                        theme="monokai",
                        line_numbers=True,
                        start_line=start_line,
                        word_wrap=False,
                    )
                )
            else:
                output_display = truncate_text(output, "", 240)
                blocks.append(
                    output_display,
                    "text",
                    theme="monokai",
                    word_wrap=False,
                )

        if truncated:
            blocks.append(Text("note: tool output was truncated", style="warning"))

        panel = Panel(
            Group(
                *blocks,
            ),
            title=title,
            padding=(1, 2),
            box=box.ROUNDED,
            border_style=border_style,
            subtitle=Text("done" if success else "failed", style=status_style),
            title_align="left",
            subtitle_align="right",
        )
        self.console.print()
        self.console.print(panel)
