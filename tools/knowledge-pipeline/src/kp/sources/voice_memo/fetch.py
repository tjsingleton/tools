from __future__ import annotations

import hashlib
import shutil
from pathlib import Path


def _sha256_file(path: Path, *, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def _build_dest_hash_index(dest: Path) -> set[str]:
    """Return set of SHA-256 hashes for all files already present under dest."""
    index: set[str] = set()
    if not dest.exists():
        return index
    for fp in dest.rglob("*"):
        if fp.is_file():
            try:
                index.add(_sha256_file(fp))
            except OSError:
                pass
    return index


def fetch_voice_memos(source_dir: Path, dest: Path) -> dict:
    """Copy new .m4a files from source_dir to dest, skipping duplicates by content hash.

    Returns {"copied": N, "skipped": M, "scanned": K}.
    """
    source_dir = Path(source_dir)
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)

    existing_hashes = _build_dest_hash_index(dest)

    audio_files = sorted(source_dir.rglob("*.m4a"))

    copied = 0
    skipped = 0

    for src in audio_files:
        if not src.is_file():
            continue
        try:
            h = _sha256_file(src)
        except OSError:
            skipped += 1
            continue

        if h in existing_hashes:
            skipped += 1
            continue

        # Determine destination path, handle name collisions with different content
        target = dest / src.name
        if target.exists():
            short_hash = h[:8]
            target = dest / f"{src.stem}-{short_hash}{src.suffix}"

        try:
            shutil.copy2(src, target)
        except OSError:
            skipped += 1
            continue

        existing_hashes.add(h)
        copied += 1

    return {"copied": copied, "skipped": skipped, "scanned": len(audio_files)}
