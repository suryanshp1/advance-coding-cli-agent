from config.config import Config
from client.llm_client import LLMClient
from context.contextmanager import ContextManager
from tools.registry import create_default_registry
from datetime import datetime
import uuid


class Session:
    def __init__(self, config: Config):
        self.config = config
        self.llm_client = LLMClient(config=config)
        self.context_manager = ContextManager()
        self.tool_registry = create_default_registry(config=config)
        self.session_id = str(uuid.uuid4())
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

        self.turn_count = 0

    def increment_turns(self) -> int:
        self.turn_count += 1
        self.updated_at = datetime.now()

        return self.turn_count
