import logging
from tools.base import Tool
from typing import List, Any
from pathlib import Path
from tools.base import Tool, ToolResult, ToolInvocation
from tools.builtin import get_all_builtin_tools, ReadFileTool

logger = logging.getLogger(__name__)


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            logger.warning(
                f"Tool with name {tool.name} already registered. Overwriting."
            )

        self._tools[tool.name] = tool
        logger.debug(f"Registered tool: {tool.name}")

    def unregister(self, name: str) -> bool:
        if name not in self._tools:
            del self._tools[name]
            logger.debug(f"Unregistered tool: {name}")
            return True
        return False

    def get(self, name: str) -> Tool | None:
        if name not in self._tools:
            return None
        return self._tools.get(name)

    def get_tools(self) -> List[Tool]:
        tools: List[Tool] = []

        for tool in self._tools.values():
            tools.append(tool)
        return tools

    def get_schemas(self) -> List[dict[str, Any]]:
        return [tool.to_openai_schema() for tool in self.get_tools()]

    async def invoke(self, name: str, params: dict[str, Any], cwd: Path) -> ToolResult:
        tool = self.get(name)
        if tool is None:
            return ToolResult.error_result(
                f"Unknown tool: {name}", metadata={"tool_name": name}
            )

        validation_errors = tool.validate_params(params)
        if validation_errors:
            return ToolResult.error_result(
                f"Invalid parameters: {'; '.join(validation_errors)}",
                metadata={"tool_name": name, "validation_errors": validation_errors},
            )

        invocation = ToolInvocation(params=params, cwd=cwd)
        try:
            result = await tool.execute(invocation=invocation)
            return result
        except Exception as e:
            logger.error(f"Tool {name} execution failed: {str(e)}")
            return ToolResult.error_result(
                f"Internal error: {str(e)}",
                metadata={"tool_name": name, "error": str(e)},
            )


def create_default_registry() -> ToolRegistry:
    registry = ToolRegistry()
    for tool_class in get_all_builtin_tools():
        registry.register(tool_class())

    return registry
