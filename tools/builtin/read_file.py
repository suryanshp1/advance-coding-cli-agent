from pydantic import BaseModel, Field
from typing import List
from tools.base import Tool, ToolKind, ToolInvocation, ToolResult
from utils.paths import resolve_path, is_binary_file
from utils.text import count_tokens, truncate_text
from config.config import Config


class ReadFileParams(BaseModel):
    path: str = Field(
        ...,
        description="Path to the file to read (relative to working directory or absolute path)",
    )

    offset: int = Field(
        1,
        ge=1,
        description="Number of lines to skip from the start of the file(1-Based). Defaults to 1.",
    )

    limit: int | None = Field(
        None,
        ge=1,
        description="Maximum number of lines to read from the file. Defaults to None (read entire file).",
    )


class ReadFileTool(Tool):
    name = "read_file"
    description = (
        "Read the contents of a text file. Returns the file content with line numbers. "
        "For large files, use offset and limit to read specific portions. "
        "Cannot read binary files (images, executables, etc.)."
    )
    kind = ToolKind.READ
    schema = ReadFileParams

    MAX_FILE_SIZE = 10 * 1024 * 1024
    MAX_OUTPUT_TOKENS = 25000

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        params = ReadFileParams(**invocation.params)
        path = resolve_path(invocation.cwd, params.path)

        if not path.exists():
            return ToolResult.error_result(
                f"File not found: {path}",
            )

        if not path.is_file():
            return ToolResult.error_result(
                f"Path is not a file: {path}",
            )

        file_size = path.stat().st_size
        if file_size > self.MAX_FILE_SIZE:
            return ToolResult.error_result(
                f"File is too large: {file_size / (1024 * 1024):.2f} MB for {path}",
                f"Maximum is {self.MAX_FILE_SIZE / (1024 * 1024):.0f} MB",
            )

        if is_binary_file(path):
            return ToolResult.error_result(
                f"Cannot read binary file: {path.name}",
                "This tool only reads text files.",
            )

        try:
            try:
                content = path.read_text(encoding="utf-8")
            except UnicodeDecodeError as e:
                content = path.read_text(encoding="latin-1")

            lines = content.splitlines()
            total_lines = len(lines)

            if total_lines == 0:
                return ToolResult.success_result(
                    f"File is empty: {path}", metadata={"lines": 0}
                )

            start_idx = max(0, params.offset - 1)
            end_idx = None

            if params.limit is not None:
                end_idx = min(start_idx + params.limit, total_lines)
            else:
                end_idx = total_lines

            selected_lines = lines[start_idx:end_idx]
            formatted_lines = []

            for i, line in enumerate(selected_lines, start=start_idx + 1):
                formatted_lines.append(f"{i:6}|{line}")

            output = "\n".join(formatted_lines)

            token_count = count_tokens(output)

            truncated = False
            if token_count > self.MAX_OUTPUT_TOKENS:
                output = truncate_text(
                    output,
                    Config().model_name,
                    self.MAX_OUTPUT_TOKENS,
                    suffix=f"\n...[TRUNCATED {total_lines} LINES]...",
                )
                truncated = True

            metadata_lines = []
            if start_idx > 0 or end_idx < total_lines:
                metadata_lines.append(
                    f"Showing lines {start_idx+1} to {end_idx} of {total_lines}"
                )

            if metadata_lines:
                header = " | ".join(metadata_lines) + "\n\n"
                output = header + output

            return ToolResult.success_result(
                output,
                truncated=truncated,
                metadata={
                    "path": str(path),
                    "total_lines": total_lines,
                    "shown_start": start_idx + 1,
                    "shown_end": end_idx,
                },
            )
        except Exception as e:
            return ToolResult.error_result(
                f"Failed to read file: {path}",
                str(e),
            )
