from __future__ import annotations
from pydantic import BaseModel, Field, model_validator
from pathlib import Path
from typing import List, Any
from enum import Enum
import os
from dotenv import load_dotenv

load_dotenv()

# Import after load_dotenv to ensure proper initialization
from config.subagent_config import SubAgentConfig


class ModelConfig(BaseModel):
    name: str = "z-ai/glm-4.5-air:free"
    temperature: float = Field(default=1, ge=0.0, le=2.0)
    context_window: int = 256_000


class ShellEnvironmentPolicy(BaseModel):
    ignore_default_excludes: bool = False
    exclude_patterns: list[str] = Field(
        default_factory=lambda: ["*KEY*", "*SHELL*", "*TOKEN*"]
    )
    set_vars: dict[str, str] = Field(default_factory=dict)


class MCPServerConfig(BaseModel):
    enabled: bool = True
    startup_timeout_sec: float = 10
    # stdio transport
    command: str | None = None
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)
    cwd: Path | None = None
    # http/sse transport
    url: str | None = None

    @model_validator(mode="after")
    def validate_transport(self) -> MCPServerConfig:
        has_command = self.command is not None
        has_url = self.url is not None

        if not has_command and not has_url:
            raise ValueError(
                "MCP server must have either `command` (stdio) or `url` (http/sse)"
            )
        if has_command and has_url:
            raise ValueError(
                "MCP server cannot have both `command` (stdio) and `url` (http/sse)"
            )

        return self


class ApprovalPolicy(str, Enum):
    ON_REQUEST = "on_request"
    ON_FAILURE = "on_failure"
    AUTO = "auto"
    AUTO_EDIT = "auto_edit"
    NEVER = "never"
    YOLO = "yolo"


class HookTrigger(str, Enum):
    BEFORE_AGENT = "before_agent"
    AFTER_AGENT = "after_agent"
    BEFORE_TOOL = "before_tool"
    AFTER_TOOL = "after_tool"
    ON_ERROR = "on_error"


class HookConfig(BaseModel):
    name: str
    trigger: HookTrigger
    command: str | None = None
    script: str | None = None
    timeout_sec: float = 30
    enabled: bool = True

    @model_validator(mode="after")
    def validate_hook(self) -> HookConfig:

        if self.command is None and self.script is None:
            raise ValueError("Hook must have either `command` or `script`")

        if self.timeout_sec <= 0:
            raise ValueError("Hook `timeout_sec` must be greater than 0")

        return self


class Config(BaseModel):
    model: ModelConfig = Field(default_factory=ModelConfig)
    cwd: Path = Field(default_factory=Path.cwd)

    max_turns: int = 100
    max_tool_output_tokens: int = 50_000
    allowed_tools: list[str] | None = Field(
        None,
        description="if this value is set, then only these tools will be allowed to agent",
    )

    developer_instructions: str | None = None
    user_instructions: str | None = None

    debug: bool = False
    shell_environment: ShellEnvironmentPolicy = Field(
        default_factory=ShellEnvironmentPolicy
    )

    subagents: list[SubAgentConfig] = Field(
        default_factory=list,
        description="Custom subagent definitions loaded from config.toml",
    )

    mcp_servers: dict[str, MCPServerConfig] = Field(
        default_factory=dict,
        description="MCP servers definitions",
    )

    approval: ApprovalPolicy = ApprovalPolicy.ON_REQUEST

    hooks_enabled: bool = False
    hooks: list[HookConfig] = Field(default_factory=list)

    @property
    def api_key(self) -> str | None:
        return os.getenv("API_KEY")

    @property
    def base_url(self) -> str | None:
        return os.getenv("BASE_URL")

    @property
    def model_name(self) -> str:
        return self.model.name

    @model_name.setter
    def model_name(self, value: str) -> None:
        self.model.name = value

    @property
    def temperature(self) -> float:
        return self.model.temperature

    @temperature.setter
    def temperature(self, value: float) -> None:
        self.model.temperature = value

    def validate(self) -> List[str]:
        errors: list[str] = []

        if not self.api_key:
            errors.append("API_KEY is not set")

        if not self.cwd.exists():
            errors.append(f"CWD does not exist: {self.cwd}")
        return errors

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()
