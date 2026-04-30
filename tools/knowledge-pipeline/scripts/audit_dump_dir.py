#!/usr/bin/env python3
"""Audit VOICE MEMO DUMP dir for files not yet in events.db.

Usage: uv run python scripts/audit_dump_dir.py
Output: .omc/spikes/dump-dir-gap-2026-04-30.json
"""
import hashlib
import json
import sqlite3
from pathlib import Path

DUMP_DIR = Path("/Volumes/DataDock/Users/tjsingleton/Archives/Misc/VOICE MEMO DUMP")
DB_PATH = Path.home() / "Library/KnowledgePipeline/events.db"
OUTPUT = Path(".omc/spikes/dump-dir-gap-2026-04-30.json")

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

def main():
    # Load existing content_hashes from events.db
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT content_hash FROM events WHERE event_type='ItemIngested' AND source='voice_memo'"
    ).fetchall()
    conn.close()
    existing = {r[0] for r in rows}
    print(f"Existing ItemIngested hashes: {len(existing)}")

    audio_extensions = {".m4a", ".qta", ".mp3", ".wav", ".aac"}
    all_files = [
        p for p in DUMP_DIR.iterdir()
        if p.suffix.lower() in audio_extensions and p.is_file()
    ]
    print(f"Audio files in dump dir: {len(all_files)}")

    gap = []
    in_db = []
    for p in sorted(all_files):
        h = sha256_file(p)
        if h in existing:
            in_db.append({"file": str(p), "sha256": h})
        else:
            gap.append({"file": str(p), "sha256": h, "stem": p.stem, "suffix": p.suffix})

    result = {
        "date": "2026-04-30",
        "dump_dir": str(DUMP_DIR),
        "total_files": len(all_files),
        "already_ingested": len(in_db),
        "gap_count": len(gap),
        "gap": gap,
    }
    OUTPUT.write_text(json.dumps(result, indent=2))
    print(f"Gap: {len(gap)} files not in events.db")
    print(f"Written to {OUTPUT}")

if __name__ == "__main__":
    main()
