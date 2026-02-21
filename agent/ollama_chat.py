from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any


DEFAULT_OLLAMA_HOST = "http://localhost:11434"


def get_ollama_host() -> str:
    host = os.environ.get("OLLAMA_HOST", "").strip() or DEFAULT_OLLAMA_HOST
    return host.rstrip("/")


def build_ollama_chat_payload(*, model: str, system: str | None, user_input: str) -> dict[str, Any]:
    messages: list[dict[str, str]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": user_input})
    return {"model": model, "stream": False, "messages": messages}


def extract_ollama_content(data: dict[str, Any]) -> str:
    msg = data.get("message")
    if isinstance(msg, dict):
        content = msg.get("content")
        if isinstance(content, str):
            return content.strip()
    return ""


def create_chat(
    *,
    host: str,
    payload: dict[str, Any],
    timeout_s: float = 60.0,
) -> dict[str, Any]:
    url = f"{host.rstrip('/')}/api/chat"
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return json.loads(raw)
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Ollama HTTPError {e.code}: {raw}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Ollama URLError: {e.reason}") from e

