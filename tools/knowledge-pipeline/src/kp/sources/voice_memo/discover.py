from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Iterable, Iterator

from kp.pipeline.plugin import RawDocument


AUDIO_EXTS = {".m4a", ".qta"}


def sha256_file(path: Path, *, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def discover(path: Path) -> Iterator[RawDocument]:
    """Glob audio files; emit RawDocument per unique content_hash."""
    root = Path(path)
    seen: set[str] = set()
    files: Iterable[Path]
    if root.is_file():
        files = [root]
    else:
        files = sorted(p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in AUDIO_EXTS)
    for fp in files:
        try:
            h = sha256_file(fp)
        except OSError:
            continue
        if h in seen:
            continue
        seen.add(h)
        yield RawDocument(
            content_hash=h,
            source="voice_memo",
            path=fp,
            metadata={
                "filename": fp.name,
                "ext": fp.suffix.lower(),
                "size_bytes": fp.stat().st_size,
            },
        )
