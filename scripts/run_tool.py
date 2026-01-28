from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = REPO_ROOT / "tools"

# Ensure repo-root modules (e.g. agent/) are importable when running as a script.
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agent.openai_responses import (  # noqa: E402
    build_responses_payload,
    create_response,
    extract_output_text,
    get_openai_api_key,
)
from agent.runner import load_agent_config  # noqa: E402


def _list_tools() -> list[str]:
    if not TOOLS_DIR.exists():
        return []
    names: list[str] = []
    for entry in sorted(TOOLS_DIR.iterdir()):
        if not entry.is_dir():
            continue
        if entry.name.startswith("."):
            continue
        names.append(entry.name)
    return names


def _run_python_main(tool_dir: Path, args: list[str]) -> int:
    main_py = tool_dir / "main.py"
    if not main_py.exists():
        notes = tool_dir / "notes.md"
        msg = f"Nothing to run: {main_py} not found."
        if notes.exists():
            msg += f" See {notes.relative_to(REPO_ROOT)}."
        print(msg, file=sys.stderr)
        return 2

    env = os.environ.copy()
    env.setdefault("PYTHONUNBUFFERED", "1")
    proc = subprocess.run(
        [sys.executable, str(main_py), *args],
        cwd=str(tool_dir),
        env=env,
    )
    return proc.returncode


def _run_agent(tool_dir: Path, args: list[str]) -> int:
    agent_yaml = tool_dir / "agent.yaml"
    if not agent_yaml.exists():
        print(f"Agent mode requested, but {agent_yaml} not found.", file=sys.stderr)
        return 2

    p = argparse.ArgumentParser(
        prog=f"{Path(sys.argv[0]).name} {tool_dir.name} --agent --",
        description="Run tool in agent mode (OpenAI Responses API).",
    )
    p.add_argument(
        "--prompt",
        help="Single prompt to send to the agent (otherwise reads stdin until EOF)",
    )
    p.add_argument(
        "--timeout",
        type=float,
        default=60.0,
        help="HTTP timeout in seconds",
    )
    p.add_argument(
        "--print-payload",
        action="store_true",
        help="Print the JSON payload that would be sent (no network call).",
    )
    ns = p.parse_args(args)

    cfg = load_agent_config(agent_yaml)
    user_input = ns.prompt if ns.prompt is not None else sys.stdin.read()
    if not user_input.strip():
        print("No input provided. Use --prompt or pipe stdin.", file=sys.stderr)
        return 2

    payload = build_responses_payload(model=cfg.model, system=cfg.system, user_input=user_input)
    if ns.print_payload:
        import json

        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0

    try:
        api_key = get_openai_api_key()
        data = create_response(api_key=api_key, payload=payload, timeout_s=ns.timeout)
    except Exception as e:
        print(str(e), file=sys.stderr)
        return 1

    text = extract_output_text(data)
    if text:
        sys.stdout.write(text)
        sys.stdout.write("\n")
        return 0

    import json

    sys.stdout.write(json.dumps(data, indent=2, sort_keys=True))
    sys.stdout.write("\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run a tool from tools/<name>/",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("tool", nargs="?", help="Tool folder name under tools/")
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available tools",
    )
    parser.add_argument(
        "--agent",
        action="store_true",
        help="Run in agent mode (requires tools/<name>/agent.yaml)",
    )

    ns, remainder = parser.parse_known_args(argv)

    if ns.list:
        for name in _list_tools():
            print(name)
        return 0

    if not ns.tool:
        parser.print_help()
        print("\nAvailable tools:", file=sys.stderr)
        for name in _list_tools():
            print(f"  - {name}", file=sys.stderr)
        return 2

    tool_dir = TOOLS_DIR / ns.tool
    if not tool_dir.exists() or not tool_dir.is_dir():
        print(f"Tool not found: {tool_dir.relative_to(REPO_ROOT)}", file=sys.stderr)
        print("Use --list to see available tools.", file=sys.stderr)
        return 2

    passthrough = remainder
    if passthrough[:1] == ["--"]:
        passthrough = passthrough[1:]

    if ns.agent:
        return _run_agent(tool_dir, passthrough)
    return _run_python_main(tool_dir, passthrough)


if __name__ == "__main__":
    raise SystemExit(main())
