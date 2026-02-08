from tools.base import Tool, ToolInvocation, ToolKind, ToolResult
from pydantic import BaseModel, Field
from utils.paths import resolve_path, is_binary_file
from pathlib import Path
from typing import List
import re
import os


class GlobParams(BaseModel):
    pattern: str = Field(..., description="Glob pattern to match")
    path: str = Field(
        ".",
        description="directory path to search in (default: current directory)",
    )


class GlobTool(Tool):
    name = "glob"
    description = (
        "Find files matching a glob pattern. Support ** for recursive matching."
    )
    kind = ToolKind.READ
    schema = GlobParams

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        params = GlobParams(**invocation.params)
        search_path = resolve_path(invocation.cwd, params.path)

        if not search_path.exists() or not search_path.is_dir():
            return ToolResult.error_result(f"Directory does not exists: {search_path}")

        try:
            matches = list(search_path.glob(params.pattern))
            matches = [p for p in matches if p.is_file()]
        except Exception as e:
            return ToolResult.error_result(f"Error searching: {str(e)}")

        output_lines = []

        for file_path in matches[:1000]:
            try:
                rel_path = file_path.relative_to(invocation.cwd)
            except Exception as e:
                rel_path = file_path

            output_lines.append(str(rel_path))
            
        if len(matches) > 1000:
            output_lines.append("... (limited to 1000 results)")
        return ToolResult.success_result(
            "\n".join(output_lines),
            metadata={
                "path": str(search_path),
                "matches": len(matches),
            },
        )