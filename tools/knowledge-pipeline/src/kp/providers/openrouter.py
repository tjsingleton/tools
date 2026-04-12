from __future__ import annotations

import os
from typing import Any

import httpx


DEFAULT_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "openai/gpt-4o-mini"


def get_api_key() -> str | None:
    try:
        import keyring  # type: ignore

        k = keyring.get_password("openrouter", "api_key")
        if k:
            return k
    except Exception:
        pass
    return os.environ.get("OPENROUTER_API_KEY")


class OpenRouterClient:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str = DEFAULT_URL,
        model: str = DEFAULT_MODEL,
    ) -> None:
        self.api_key = api_key or get_api_key()
        self.base_url = base_url.rstrip("/")
        self.model = model

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        response_format: dict | None = None,
        timeout: float = 120.0,
    ) -> dict[str, Any]:
        if not self.api_key:
            raise RuntimeError(
                "No OpenRouter API key; set OPENROUTER_API_KEY or keyring 'openrouter:api_key'"
            )
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {"model": self.model, "messages": messages}
        if response_format:
            payload["response_format"] = response_format
        with httpx.Client(timeout=timeout) as client:
            r = client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
            r.raise_for_status()
            return r.json()
