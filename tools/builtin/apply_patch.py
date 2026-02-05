from tools.base import Tool, ToolKind, ToolInvocation, ToolResult, FileDiff
from pydantic import BaseModel, Field
from utils.paths import resolve_path
from pathlib import Path
from typing import List


class EditOperation(BaseModel):
    old_string: str = Field(
        ...,
        description="The exact text to find and replace. Must match exactly including whitespace and indentation.",
    )
    new_string: str = Field(
        ...,
        description="String to replace the old_string with. Can be empty to delete text.",
    )
    replace_all: bool = Field(
        False,
        description="Replace all occurrences of old_string in the file (default: false)",
    )


class ApplyPatchParams(BaseModel):
    path: str = Field(
        ...,
        description="Path to the file to edit (relative to working directory or absolute path)",
    )
    edits: List[EditOperation] = Field(
        ..., description="List of edit operations to apply sequentially to the file."
    )


class ApplyPatchTool(Tool):
    name = "apply_patch"
    description = (
        "Apply multiple search-and-replace edits to a single file in one atomic operation. "
        "Edits are applied sequentially in the order provided. If any edit fails (e.g., text not found), "
        "the entire operation is rolled back and no changes are made to the file."
    )
    kind = ToolKind.WRITE
    schema = ApplyPatchParams

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        params = ApplyPatchParams(**invocation.params)
        path = resolve_path(invocation.cwd, params.path)

        if not path.exists():
            return ToolResult.error_result(f"File not found: {path}")

        try:
            original_content = path.read_text(encoding="utf-8")
        except Exception as e:
            return ToolResult.error_result(f"Failed to read file '{path}': {e}")

        current_content = original_content
        successful_edits = 0

        for index, edit in enumerate(params.edits):
            if not edit.old_string:
                return ToolResult.error_result(
                    f"Edit #{index + 1} failed: old_string cannot be empty."
                )

            occurance_count = current_content.count(edit.old_string)

            if occurance_count == 0:
                return self._no_match_error(
                    edit.old_string, current_content, path, index + 1
                )

            if occurance_count > 1 and not edit.replace_all:
                return ToolResult.error_result(
                    f"Edit #{index + 1} failed: old_string found {occurance_count} times in current content. "
                    f"Set replace_all=true to replace all occurrences or provide more context."
                )

            if edit.replace_all:
                current_content = current_content.replace(
                    edit.old_string, edit.new_string
                )
            else:
                current_content = current_content.replace(
                    edit.old_string, edit.new_string, 1
                )

            successful_edits += 1

        if current_content == original_content:
            return ToolResult.success_result(
                f"No changes made to '{path}'. All edits resulted in identical content.",
                metadata={"path": str(path), "edits_processed": successful_edits},
            )

        try:
            path.write_text(current_content, encoding="utf-8")
        except Exception as e:
            return ToolResult.error_result(f"Failed to write changes to '{path}': {e}")

        return ToolResult.success_result(
            f"Successfully applied {successful_edits} edits to '{path}'.",
            diff=FileDiff(
                path=path,
                old_content=original_content,
                new_content=current_content,
            ),
            metadata={
                "path": str(path),
                "edits_applied": successful_edits,
            },
        )

    def _no_match_error(
        self, old_string: str, content: str, path: Path, edit_index: int
    ) -> ToolResult:
        lines = content.splitlines()

        partial_matches = []
        search_terms = old_string.split()[:5]

        if search_terms:
            first_term = search_terms[0]
            for i, line in enumerate(lines, 1):
                if first_term in line:
                    partial_matches.append((i, line.strip()[:80]))
                    if len(partial_matches) >= 3:
                        break

        error_msg = (
            f"Edit #{edit_index} failed: old_string not found in current file content."
        )

        if partial_matches:
            error_msg += "\n\nPossible similar lines in current state:"
            for line_num, line_preview in partial_matches:
                error_msg += f"\n  Line {line_num}: {line_preview}"
            error_msg += "\n\nMake sure old_string matches exactly (including whitespace and indentation)."
        else:
            error_msg += (
                "\nMake sure the text matches exactly, including:\n"
                "- All whitespace and indentation\n"
                "- Line breaks\n"
                "- Any invisible characters"
            )

        return ToolResult.error_result(error_msg)
