import logging
from tools.base import Tool
from typing import List, Any
from pathlib import Path
from tools.base import Tool, ToolResult, ToolInvocation
from tools.builtin import get_all_builtin_tools, ReadFileTool
from tools.subagents import get_default_subagent_definitions, SubAgentTool
from config.config import Config
from hooks.hook_system import HookSystem
from safety.approval import ApprovalManager, ApprovalContext, ApprovalDecision

logger = logging.getLogger(__name__)


class ToolRegistry:
    def __init__(self, config: Config):
        self._tools: dict[str, Tool] = {}
        self._mcp_tools: dict[str, Tool] = {}
        self.config = config

    @property
    def tool_count(self) -> int:
        return len(self._tools)

    @property
    def mcp_tool_count(self) -> int:
        return len(self._mcp_tools)

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            logger.warning(
                f"Tool with name {tool.name} already registered. Overwriting."
            )

        self._tools[tool.name] = tool
        logger.debug(f"Registered tool: {tool.name}")

    def register_mcp_tool(self, tool: Tool) -> None:
        self._mcp_tools[tool.name] = tool
        logger.debug(f"Registered MCP tool: {tool.name}")

    def unregister(self, name: str) -> bool:
        if name not in self._tools:
            del self._tools[name]
            logger.debug(f"Unregistered tool: {name}")
            return True
        return False

    def get(self, name: str) -> Tool | None:
        if name not in self._tools and name not in self._mcp_tools:
            return None

        if name in self._tools:
            return self._tools.get(name)

        elif name in self._mcp_tools:
            return self._mcp_tools.get(name)

        return None

    def get_tools(self) -> List[Tool]:
        tools: List[Tool] = []

        for tool in self._tools.values():
            tools.append(tool)

        for tool in self._mcp_tools.values():
            tools.append(tool)

        if self.config.allowed_tools is not None:
            allowed_set = set(self.config.allowed_tools)
            tools = [tool for tool in tools if tool.name in allowed_set]

        return tools

    def get_schemas(self) -> List[dict[str, Any]]:
        return [tool.to_openai_schema() for tool in self.get_tools()]

    async def invoke(
        self,
        name: str,
        params: dict[str, Any],
        cwd: Path,
        hook_system: HookSystem,
        approval_manager: ApprovalManager | None = None,
    ) -> ToolResult:
        tool = self.get(name)
        if tool is None:
            result = ToolResult.error_result(
                f"Unknown tool: {name}", metadata={"tool_name": name}
            )

            await hook_system.trigger_after_tool(name, params, result)

            return result

        validation_errors = tool.validate_params(params)
        if validation_errors:
            result = ToolResult.error_result(
                f"Invalid parameters: {'; '.join(validation_errors)}",
                metadata={"tool_name": name, "validation_errors": validation_errors},
            )

        await hook_system.trigger_before_tool(name, params)

        invocation = ToolInvocation(params=params, cwd=cwd)
        if approval_manager:
            confirmation = await tool.get_confirmation(invocation)
            if confirmation:
                context = ApprovalContext(
                    tool_name=name,
                    params=params,
                    is_mutating=tool.is_mutating(params=params),
                    is_dangerous=confirmation.is_dangerous,
                    affected_paths=confirmation.affected_paths,
                    command=confirmation.command,
                )
                decision = await approval_manager.check_approval(context=context)
                if decision == ApprovalDecision.REJECTED:
                    result = ToolResult.error_result(
                        f"Operation denied by safety policy: {decision.reason}",
                        metadata={"tool_name": name, "reason": decision.reason},
                    )

                    await hook_system.trigger_after_tool(name, params, result)

                    return result

                elif decision == ApprovalDecision.NEEDS_CONFIRMATION:
                    approve = approval_manager.request_confirmation(
                        confirmation=confirmation
                    )
                    if not approve:
                        result = ToolResult.error_result(
                            "User rejected the operation",
                            metadata={"tool_name": name},
                        )

                        await hook_system.trigger_after_tool(name, params, result)

                        return result

        try:
            result = await tool.execute(invocation=invocation)
        except Exception as e:
            logger.error(f"Tool {name} execution failed: {str(e)}")
            result = ToolResult.error_result(
                f"Internal error: {str(e)}",
                metadata={"tool_name": name, "error": str(e)},
            )

        await hook_system.trigger_after_tool(name, params, result)

        return result


def create_default_registry(config: Config) -> ToolRegistry:
    """Create and populate the default tool registry with built-in tools and subagents

    Args:
        config: Configuration object containing tool settings and custom subagents

    Returns:
        ToolRegistry: Fully populated registry with built-in and custom tools
    """
    registry = ToolRegistry(config=config)

    # Register all built-in tools (file operations, shell commands, etc.)
    for tool_class in get_all_builtin_tools():
        registry.register(tool_class(config=config))

    # Register default (hardcoded) subagents for backward compatibility
    for subagent_def in get_default_subagent_definitions():
        registry.register(SubAgentTool(config=config, definition=subagent_def))

    # Register custom subagents from config.toml
    for subagent_config in config.subagents:
        try:
            definition = subagent_config.to_definition()
            registry.register(SubAgentTool(config=config, definition=definition))
            logger.info(f"Registered custom subagent: subagent_{definition.name}")
        except Exception as e:
            logger.error(
                f"Failed to register custom subagent '{subagent_config.name}': {e}"
            )
            # Continue loading other subagents - don't let one failure break everything

    return registry
