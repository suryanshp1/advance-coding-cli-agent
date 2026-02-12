from config.config import Config
from tools.mcp.client import MCPClient, MCPToolInfo, MCPServerStatus
from typing import Any
from tools.registry import ToolRegistry
from tools.mcp.tool import MCPTool
import asyncio


class MCPManager:
    def __init__(self, config: Config) -> None:
        self.config: Config = config
        self._clients: dict[str, MCPClient] = dict()
        self._initialized: bool = False

    async def initialize(self) -> None:
        if self._initialized:
            return

        mcp_configs = self.config.mcp_servers

        if not mcp_configs:
            return

        for name, server_config in mcp_configs.items():
            if not server_config.enabled:
                continue

            self._clients[name] = MCPClient(
                name=name,
                config=server_config,
                cwd=self.config.cwd,
            )

        connection_tasks = [
            asyncio.wait_for(
                client.connect(),
                timeout=client.config.startup_timeout_sec,
            )
            for name, client in self._clients.items()
        ]

        await asyncio.gather(
            *connection_tasks,
            return_exceptions=True,
        )

        self._initialized = True

    def register_tools(self, registry: ToolRegistry) -> int:
        count = 0
        for client in self._clients.values():
            if client.status != MCPServerStatus.CONNECTED:
                continue

            for tool in client.tools:
                mcp_tool = MCPTool(
                    config=self.config,
                    client=client,
                    tool_info=tool,
                    name=f"{client.name}__{tool.name}",
                )
                registry.register_mcp_tool(mcp_tool)
                count += 1

        return count
