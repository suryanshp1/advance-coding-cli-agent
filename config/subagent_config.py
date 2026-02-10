"""Configuration model for custom subagents defined in config.toml"""

from pydantic import BaseModel, Field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tools.subagents import SubAgentDefinition


class SubAgentConfig(BaseModel):
    """Configuration model for a custom subagent defined in config.toml
    
    This model validates and parses subagent definitions from TOML configuration
    files, ensuring type safety and proper validation before runtime usage.
    
    Attributes:
        name: Unique identifier for the subagent (used as tool name suffix)
        description: Human-readable description of the subagent's purpose
        goal_prompt: System prompt that defines the subagent's role and behavior
        allowed_tools: Optional whitelist of tool names the subagent can use
        max_turns: Maximum number of conversation turns (1-100)
        timeout_seconds: Execution timeout in seconds (1.0-3600.0)
    """
    
    name: str = Field(
        ...,
        description="Unique identifier for the subagent",
        min_length=1,
        max_length=50,
        pattern=r"^[a-z][a-z0-9_]*$"  # Snake_case naming convention
    )
    description: str = Field(
        ...,
        description="Human-readable description of what the subagent does",
        min_length=10,
        max_length=500
    )
    goal_prompt: str = Field(
        ...,
        description="System prompt defining the subagent's role and behavior",
        min_length=20
    )
    allowed_tools: list[str] | None = Field(
        None,
        description="Whitelist of tool names the subagent can use (None = all tools allowed)"
    )
    max_turns: int = Field(
        20,
        ge=1,
        le=100,
        description="Maximum conversation turns for the subagent"
    )
    timeout_seconds: float = Field(
        600.0,
        ge=1.0,
        le=3600.0,
        description="Execution timeout in seconds"
    )
    
    def to_definition(self) -> "SubAgentDefinition":
        """Convert config model to SubAgentDefinition dataclass
        
        Returns:
            SubAgentDefinition: Runtime definition object for subagent registration
        """
        from tools.subagents import SubAgentDefinition
        
        return SubAgentDefinition(
            name=self.name,
            description=self.description,
            goal_prompt=self.goal_prompt,
            allowed_tools=self.allowed_tools,
            max_turns=self.max_turns,
            timeout_seconds=self.timeout_seconds
        )
    
    class Config:
        """Pydantic configuration"""
        json_schema_extra = {
            "example": {
                "name": "security_auditor",
                "description": "Analyzes code for security vulnerabilities and generates reports",
                "goal_prompt": "You are a security auditing specialist...",
                "allowed_tools": ["read_file", "grep", "list_dir"],
                "max_turns": 15,
                "timeout_seconds": 450.0
            }
        }
