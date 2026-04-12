from __future__ import annotations

from typing import Any


class OB1Client:
    """Thin wrapper around OB1 MCP tools. Disabled in dry-run mode."""

    def __init__(self, *, dry_run: bool = True) -> None:
        self.dry_run = dry_run

    def search_thoughts(self, query: str, *, limit: int = 10) -> list[dict[str, Any]]:
        if self.dry_run:
            return []
        raise NotImplementedError("OB1 MCP integration not wired in MVP-Vertical")

    def capture_thought(self, content: str, *, metadata: dict | None = None) -> dict[str, Any]:
        if self.dry_run:
            raise RuntimeError("capture_thought disabled in dry-run mode")
        raise NotImplementedError("OB1 MCP integration not wired in MVP-Vertical")
