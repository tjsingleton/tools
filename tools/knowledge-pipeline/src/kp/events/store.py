from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Iterable, Iterator

from kp.events.events import Event


DEFAULT_DB_PATH = Path.home() / "Library" / "KnowledgePipeline" / "events.db"


class EventStore:
    """Append-only SQLite event log."""

    def __init__(self, db_path: Path | str | None = None) -> None:
        self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                event_type TEXT NOT NULL,
                source TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                data_json TEXT NOT NULL
            )
            """
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_events_content_hash ON events(content_hash)"
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type)"
        )
        self._conn.commit()

    def append(self, event: Event) -> int:
        cur = self._conn.execute(
            "INSERT INTO events (timestamp, event_type, source, content_hash, data_json) VALUES (?, ?, ?, ?, ?)",
            (
                event.timestamp,
                event.event_type,
                event.source,
                event.content_hash,
                json.dumps(event.data, default=str),
            ),
        )
        self._conn.commit()
        return int(cur.lastrowid)

    def has_event(self, *, content_hash: str, event_type: str) -> bool:
        cur = self._conn.execute(
            "SELECT 1 FROM events WHERE content_hash = ? AND event_type = ? LIMIT 1",
            (content_hash, event_type),
        )
        return cur.fetchone() is not None

    def tail(self, *, source: str | None = None, limit: int = 50) -> Iterable[dict]:
        if source:
            cur = self._conn.execute(
                "SELECT * FROM events WHERE source = ? ORDER BY id DESC LIMIT ?",
                (source, limit),
            )
        else:
            cur = self._conn.execute(
                "SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,)
            )
        for row in cur.fetchall():
            yield dict(row)

    def all(self) -> Iterator[dict]:
        cur = self._conn.execute("SELECT * FROM events ORDER BY id ASC")
        for row in cur.fetchall():
            yield dict(row)

    def query(self, *, event_type: str | None = None, source: str | None = None) -> list[dict]:
        """Return events matching optional filters, ordered by id ASC."""
        conditions = []
        params: list = []
        if event_type is not None:
            conditions.append("event_type = ?")
            params.append(event_type)
        if source is not None:
            conditions.append("source = ?")
            params.append(source)
        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        cur = self._conn.execute(
            f"SELECT * FROM events {where} ORDER BY id ASC",
            params,
        )
        rows = [dict(r) for r in cur.fetchall()]
        for row in rows:
            if "data_json" in row:
                row["data"] = json.loads(row.pop("data_json"))
        return rows

    def by_hash(self, content_hash: str) -> list[dict]:
        cur = self._conn.execute(
            "SELECT * FROM events WHERE content_hash = ? ORDER BY id ASC",
            (content_hash,),
        )
        return [dict(r) for r in cur.fetchall()]

    def delete_by_hash(self, content_hash: str) -> int:
        cur = self._conn.execute(
            "DELETE FROM events WHERE content_hash = ?", (content_hash,)
        )
        self._conn.commit()
        return cur.rowcount

    def close(self) -> None:
        self._conn.close()
