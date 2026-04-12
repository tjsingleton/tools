from __future__ import annotations

import json
import sqlite3
from pathlib import Path


DEFAULT_INDEX_PATH = Path.home() / "Library" / "KnowledgePipeline" / "index.db"


class VectorIndex:
    """Local embeddings store.

    Uses sqlite-vec if available for cosine search; falls back to a plain
    SQLite table (embedding stored as JSON) when the extension can't load.
    """

    def __init__(self, db_path: Path | str | None = None) -> None:
        self.db_path = Path(db_path) if db_path else DEFAULT_INDEX_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path))
        self._vec_enabled = self._try_load_vec()
        self._init_schema()

    def _try_load_vec(self) -> bool:
        try:
            import sqlite_vec  # type: ignore

            self._conn.enable_load_extension(True)
            sqlite_vec.load(self._conn)
            self._conn.enable_load_extension(False)
            return True
        except Exception:
            return False

    def _init_schema(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS embeddings (
                content_hash TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                text TEXT NOT NULL,
                embedding_json TEXT NOT NULL,
                dim INTEGER NOT NULL
            )
            """
        )
        self._conn.commit()

    def upsert(self, *, content_hash: str, source: str, text: str, embedding: list[float]) -> None:
        self._conn.execute(
            """
            INSERT INTO embeddings (content_hash, source, text, embedding_json, dim)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(content_hash) DO UPDATE SET
                source=excluded.source,
                text=excluded.text,
                embedding_json=excluded.embedding_json,
                dim=excluded.dim
            """,
            (content_hash, source, text, json.dumps(embedding), len(embedding)),
        )
        self._conn.commit()

    def has(self, content_hash: str) -> bool:
        cur = self._conn.execute(
            "SELECT 1 FROM embeddings WHERE content_hash = ? LIMIT 1", (content_hash,)
        )
        return cur.fetchone() is not None

    def close(self) -> None:
        self._conn.close()
