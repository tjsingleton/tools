from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any


OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"


def get_openai_api_key() -> str:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise ValueError("Missing OPENAI_API_KEY")
    return api_key


def build_responses_payload(*, model: str, system: str | None, user_input: str) -> dict[str, Any]:
    payload: dict[str, Any] = {"model": model, "input": user_input}
    if system:
        payload["instructions"] = system
    return payload


def extract_output_text(data: dict[str, Any]) -> str:
    output = data.get("output") or []
    parts: list[str] = []

    if isinstance(output, list):
        for item in output:
            if not isinstance(item, dict):
                continue
            if item.get("type") != "message":
                continue
            if item.get("role") != "assistant":
                continue
            content = item.get("content") or []
            if not isinstance(content, list):
                continue
            for c in content:
                if not isinstance(c, dict):
                    continue
                if c.get("type") in ("output_text", "text") and isinstance(c.get("text"), str):
                    parts.append(c["text"])

    return "".join(parts).strip()


def create_response(
    *,
    api_key: str,
    payload: dict[str, Any],
    timeout_s: float = 60.0,
) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        OPENAI_RESPONSES_URL,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
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
        raise RuntimeError(f"OpenAI HTTPError {e.code}: {raw}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"OpenAI URLError: {e.reason}") from e

