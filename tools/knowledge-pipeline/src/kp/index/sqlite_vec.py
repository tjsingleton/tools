from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


DEFAULT_INDEX_PATH = Path.home() / "Library" / "KnowledgePipeline" / "index.db"


class VectorIndex:
    """Local embeddings store.

    Uses sqlite-vec if available for cosine search; falls back to a plain
    SQLite table (embedding stored as JSON) when the extension can't load.

    Schema uses a composite primary key ``(content_hash, chunk_index)`` so
    long documents can be stored as multiple overlapping chunks.  Legacy
    single-PK databases (content_hash only) are migrated automatically on
    first open — existing rows survive at chunk_index=0.
    """

    def __init__(self, db_path: Path | str | None = None) -> None:
        self.db_path = Path(db_path) if db_path else DEFAULT_INDEX_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path))
        self._vec_enabled = self._try_load_vec()
        self._migrate_schema()
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

    def _migrate_schema(self) -> None:
        """Migrate legacy schema (content_hash PRIMARY KEY) to chunked schema.

        Idempotent — safe to call on a fresh or already-migrated DB.
        """
        cur = self._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='embeddings'"
        )
        if cur.fetchone() is None:
            # Table doesn't exist yet; _init_schema will create it fresh.
            return

        # Check whether chunk_index column already exists.
        col_info = self._conn.execute("PRAGMA table_info(embeddings)").fetchall()
        col_names = {row[1] for row in col_info}
        if "chunk_index" in col_names:
            # Already on new schema.
            return

        # Legacy schema detected: rename, recreate, and copy rows at chunk 0.
        self._conn.executescript(
            """
            BEGIN;
            ALTER TABLE embeddings RENAME TO embeddings_legacy;
            CREATE TABLE embeddings (
                content_hash TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,
                source TEXT NOT NULL,
                text TEXT NOT NULL,
                embedding_json TEXT NOT NULL,
                dim INTEGER NOT NULL,
                PRIMARY KEY (content_hash, chunk_index)
            );
            CREATE INDEX IF NOT EXISTS idx_embeddings_hash ON embeddings(content_hash);
            INSERT INTO embeddings (content_hash, chunk_index, source, text, embedding_json, dim)
                SELECT content_hash, 0, source, text, embedding_json, dim
                FROM embeddings_legacy;
            DROP TABLE embeddings_legacy;
            COMMIT;
            """
        )

    def _init_schema(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS embeddings (
                content_hash TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,
                source TEXT NOT NULL,
                text TEXT NOT NULL,
                embedding_json TEXT NOT NULL,
                dim INTEGER NOT NULL,
                PRIMARY KEY (content_hash, chunk_index)
            );
            CREATE INDEX IF NOT EXISTS idx_embeddings_hash ON embeddings(content_hash);
            """
        )
        self._conn.commit()

    # ------------------------------------------------------------------
    # Write helpers
    # ------------------------------------------------------------------

    def upsert_chunks(
        self,
        content_hash: str,
        source: str,
        chunks: list[dict[str, Any]],
    ) -> None:
        """Atomically replace all chunks for *content_hash*.

        Each entry in *chunks* must have keys ``index`` (int), ``text`` (str),
        and ``embedding`` (list[float]).
        """
        with self._conn:
            self._conn.execute(
                "DELETE FROM embeddings WHERE content_hash = ?", (content_hash,)
            )
            self._conn.executemany(
                """
                INSERT INTO embeddings
                    (content_hash, chunk_index, source, text, embedding_json, dim)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        content_hash,
                        chunk["index"],
                        source,
                        chunk["text"],
                        json.dumps(chunk["embedding"]),
                        len(chunk["embedding"]),
                    )
                    for chunk in chunks
                ],
            )

    def upsert(
        self,
        *,
        content_hash: str,
        source: str,
        text: str,
        embedding: list[float],
    ) -> None:
        """Single-chunk shim for back-compat.  Stores as chunk_index=0."""
        self.upsert_chunks(
            content_hash,
            source,
            [{"index": 0, "text": text, "embedding": embedding}],
        )

    # ------------------------------------------------------------------
    # Read helpers
    # ------------------------------------------------------------------

    def has(self, content_hash: str) -> bool:
        """Return True if ANY chunk exists for *content_hash*."""
        cur = self._conn.execute(
            "SELECT 1 FROM embeddings WHERE content_hash = ? LIMIT 1",
            (content_hash,),
        )
        return cur.fetchone() is not None

    def close(self) -> None:
        self._conn.close()
