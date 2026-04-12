from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Ensure src/ importable without install.
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@pytest.fixture
def tmp_event_store(tmp_path):
    from kp.events import EventStore

    s = EventStore(db_path=tmp_path / "events.db")
    yield s
    s.close()


@pytest.fixture
def tmp_review_dir(tmp_path):
    d = tmp_path / "review"
    d.mkdir()
    return d
