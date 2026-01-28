from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = REPO_ROOT / "tools"


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

    try:
        import yaml  # type: ignore
    except Exception:
        print(
            "Agent mode requires PyYAML.\n"
            "Install: pip install -e '.[agent]'",
            file=sys.stderr,
        )
        return 2

    with agent_yaml.open("r", encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}

    print(
        "Agent mode scaffold only.\n"
        f"Loaded {agent_yaml.relative_to(REPO_ROOT)} with keys: {sorted(config.keys())}\n"
        "Next: implement agent runner in agent/ and wire it here.",
        file=sys.stderr,
    )
    return 2


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
    parser.add_argument(
        "args",
        nargs=argparse.REMAINDER,
        help="Args after -- are passed through to the tool",
    )

    ns = parser.parse_args(argv)

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

    passthrough = ns.args
    if passthrough[:1] == ["--"]:
        passthrough = passthrough[1:]

    if ns.agent:
        return _run_agent(tool_dir, passthrough)
    return _run_python_main(tool_dir, passthrough)


if __name__ == "__main__":
    raise SystemExit(main())

