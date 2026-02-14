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

    @property
    def get_all_servers(self) -> list[dict[str, Any]]:
        return [
            {
                "name": client.name,
                "status": client.status.value,
                "tools_count": len(client.tools),
            }
            for client in self._clients.values()
        ]

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

        results = await asyncio.gather(
            *connection_tasks,
            return_exceptions=True,
        )

        for result in results:
            if isinstance(result, Exception):
                print(f"MCP Connection Error: {result}")

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

    async def shutdown(self) -> None:
        disconnect_tasks = [client.disconnect() for client in self._clients.values()]
        await asyncio.gather(*disconnect_tasks, return_exceptions=True)
        self._clients.clear()
        self._initialized = False
