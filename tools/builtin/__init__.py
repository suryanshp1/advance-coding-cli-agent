from tools.builtin.read_file import ReadFileTool
from tools.builtin.write_file import WriteFileTool
from tools.builtin.edit_file import EditTool
from tools.builtin.apply_patch import ApplyPatchTool
from tools.builtin.shell import ShellTool
from tools.builtin.list_dir import ListDirTool
from tools.builtin.grep import GrepTool
from tools.base import Tool

__all__ = [
    "ReadFileTool",
    "WriteFileTool",
    "EditTool",
    "ApplyPatchTool",
    "ShellTool",
    "ListDirTool",
    "GrepTool",
]


def get_all_builtin_tools() -> list[type[Tool]]:
    return [
        ReadFileTool,
        WriteFileTool,
        EditTool,
        ApplyPatchTool,
        ShellTool,
        ListDirTool,
        GrepTool,
    ]
