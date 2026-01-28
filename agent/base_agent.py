from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AgentConfig:
    name: str | None = None
    model: str | None = None
    system: str | None = None
    tools: list[str] | None = None
    memory: dict[str, Any] | None = None


class ToolAgent:
    def __init__(self, config: AgentConfig, context: dict[str, Any]) -> None:
        self.config = config
        self.context = context

    def run(self, user_input: str) -> str:
        raise NotImplementedError("Agent runner not implemented yet.")

