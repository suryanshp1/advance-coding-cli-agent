from tools.builtin.read_file import ReadFileTool
from tools.builtin.write_file import WriteFileTool
from tools.base import Tool

__all__ = [
    "ReadFileTool",
    "WriteFileTool",
]


def get_all_builtin_tools() -> list[type[Tool]]:
    return [
        ReadFileTool,
        WriteFileTool,
    ]
