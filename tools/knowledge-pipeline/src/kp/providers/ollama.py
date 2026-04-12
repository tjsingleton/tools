from __future__ import annotations

from typing import Sequence

import httpx


DEFAULT_URL = "http://localhost:11434"
DEFAULT_MODEL = "nomic-embed-text"


class OllamaClient:
    def __init__(self, base_url: str = DEFAULT_URL, model: str = DEFAULT_MODEL) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model

    def embed(self, text: str, *, timeout: float = 60.0) -> list[float]:
        with httpx.Client(timeout=timeout) as client:
            r = client.post(
                f"{self.base_url}/api/embeddings",
                json={"model": self.model, "prompt": text},
            )
            r.raise_for_status()
            data = r.json()
            return list(data.get("embedding") or [])

    def embed_batch(self, texts: Sequence[str], *, timeout: float = 60.0) -> list[list[float]]:
        return [self.embed(t, timeout=timeout) for t in texts]
