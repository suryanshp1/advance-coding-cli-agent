from __future__ import annotations
from config.loader import get_data_dir
from dataclasses import dataclass
from datetime import datetime
from client.response import TokenUsage
import os
import json
from typing import Any


@dataclass
class SessionSnapshot:
    session_id: str
    created_at: datetime
    updated_at: datetime
    turn_count: int
    messages: list[dict[str, Any]]
    total_usage: TokenUsage

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "turn_count": self.turn_count,
            "messages": self.messages,
            "total_usage": self.total_usage.__dict__,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SessionSnapshot:
        return cls(
            session_id=data["session_id"],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            turn_count=data["turn_count"],
            messages=data["messages"],
            total_usage=TokenUsage(**data["total_usage"]),
        )


class PersistenceManager:
    def __init__(self) -> None:
        self.data_dir = get_data_dir()
        self.sessions_dir = self.data_dir / "sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        os.chmod(str(self.sessions_dir), 0o700)

    def save_session(self, snapshot: SessionSnapshot) -> None:
        file_path = self.sessions_dir / f"{snapshot.session_id}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(snapshot.to_dict(), f, indent=2)
        os.chmod(str(file_path), 0o600)

    def load_session(self, session_id: str) -> SessionSnapshot | None:
        file_path = self.sessions_dir / f"{session_id}.json"
        if not file_path.exists():
            return None
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return SessionSnapshot.from_dict(data)

    def list_sessions(self) -> list[str]:
        sessions = []
        for file_path in self.sessions_dir.glob("*.json"):
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            sessions.append(
                {
                    "session_id": data["session_id"],
                    "created_at": data["created_at"],
                    "updated_at": data["updated_at"],
                    "turn_count": data["turn_count"],
                    "total_usage": data["total_usage"],
                }
            )
        sessions.sort(key=lambda x: x["updated_at"], reverse=True)
        return sessions
