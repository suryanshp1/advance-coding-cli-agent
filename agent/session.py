from config.config import Config
from client.llm_client import LLMClient
from context.contextmanager import ContextManager
from tools.registry import create_default_registry
from datetime import datetime
from config.loader import get_data_dir
from tools.base import Tool
import json
import uuid


class Session:
    def __init__(self, config: Config):
        self.config = config
        self.llm_client = LLMClient(config=config)
        self.tool_registry = create_default_registry(config=config)
        self.context_manager = ContextManager(
            config=config,
            user_memory=self._load_memory(),
            tools=self.tool_registry.get_tools(),
        )
        self.session_id = str(uuid.uuid4())
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

        self.turn_count = 0

    def _load_memory(self) -> str | None:
        data_dir = get_data_dir()
        data_dir.mkdir(parents=True, exist_ok=True)
        path = data_dir / "user_memory.json"
        if not path.exists():
            return None

        try:
            content = path.read_text(encoding="utf-8")
            data = json.loads(content)
            entries = data.get("entries")
            if not entries:
                return None
            lines = ["User preferences and notes:"]
            for key, value in entries.items():
                lines.append(f"- {key}: {value}")

            return "\n".join(lines)

        except json.JSONDecodeError as e:
            return None
        except (OSError, IOError) as e:
            return None
        except Exception as e:
            return None

    def increment_turns(self) -> int:
        self.turn_count += 1
        self.updated_at = datetime.now()

        return self.turn_count
