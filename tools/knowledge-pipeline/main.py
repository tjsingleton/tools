from __future__ import annotations

import sys
from pathlib import Path

# Allow `python main.py ...` without install.
sys.path.insert(0, str(Path(__file__).parent / "src"))

from kp.cli import cli  # noqa: E402


if __name__ == "__main__":
    cli()
