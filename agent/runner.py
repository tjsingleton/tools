from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class AgentConfig:
    name: str | None
    model: str
    system: str | None


def parse_agent_yaml(text: str) -> dict[str, Any]:
    """
    Minimal YAML subset parser for agent.yaml.

    Supported:
    - top-level scalars: `key: value`
    - top-level lists:
        tools:
          - http
          - json
    - literal block scalars:
        system: |
          line 1
          line 2
    """
    lines = text.splitlines()
    i = 0
    out: dict[str, Any] = {}

    def peek() -> str | None:
        return lines[i] if i < len(lines) else None

    def consume() -> str:
        nonlocal i
        line = lines[i]
        i += 1
        return line

    while peek() is not None:
        raw = consume()
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if raw.startswith((" ", "\t")):
            raise ValueError("Unexpected indentation at top level")

        if ":" not in raw:
            raise ValueError(f"Invalid line (expected key: value): {raw!r}")
        key, rest = raw.split(":", 1)
        key = key.strip()
        rest = rest.lstrip()
        if not key:
            raise ValueError(f"Invalid key in line: {raw!r}")

        if rest == "|":
            block_lines: list[str] = []
            while peek() is not None:
                nxt = peek()
                if nxt is None:
                    break
                if not nxt.startswith((" ", "\t")):
                    break
                nxt_raw = consume()
                block_lines.append(nxt_raw[2:] if nxt_raw.startswith("  ") else nxt_raw.lstrip("\t"))
            out[key] = "\n".join(block_lines).rstrip("\n")
            continue

        if rest == "":
            # list form (only supports "- item" lines at 2-space indent)
            items: list[str] = []
            while peek() is not None:
                nxt = peek()
                if nxt is None:
                    break
                if not nxt.startswith("  - "):
                    break
                nxt_raw = consume()
                items.append(nxt_raw[4:].strip())
            out[key] = items
            continue

        # scalar
        if (rest.startswith('"') and rest.endswith('"')) or (rest.startswith("'") and rest.endswith("'")):
            rest = rest[1:-1]
        out[key] = rest

    return out


def load_agent_config(path: Path) -> AgentConfig:
    raw = path.read_text(encoding="utf-8")
    data = parse_agent_yaml(raw)

    model = str(data.get("model") or "").strip()
    if not model:
        raise ValueError("agent.yaml missing required field: model")

    name_val = data.get("name")
    name = str(name_val).strip() if isinstance(name_val, str) and name_val.strip() else None

    system_val = data.get("system")
    system = str(system_val).strip() if isinstance(system_val, str) and system_val.strip() else None

    return AgentConfig(name=name, model=model, system=system)

