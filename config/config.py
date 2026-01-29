from pydantic import BaseModel, Field
from pathlib import Path
from typing import List
import os
from dotenv import load_dotenv

load_dotenv()


class ModelConfig(BaseModel):
    name: str = "z-ai/glm-4.5-air:free"
    temperature: float = Field(default=1, ge=0.0, le=2.0)
    context_window: int = 256_000


class Config(BaseModel):
    model: ModelConfig = Field(default_factory=ModelConfig)
    cwd: Path = Field(default_factory=Path.cwd)

    max_turns: int = 100
    max_tool_output_tokens: int = 50_000

    developer_instructions: str | None = None
    user_instructions: str | None = None

    debug: bool = False

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
