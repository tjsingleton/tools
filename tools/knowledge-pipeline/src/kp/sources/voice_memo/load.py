from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from kp.pipeline.plugin import RawDocument


FFMPEG = shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"
CACHE_DIR = Path.home() / "Library" / "KnowledgePipeline" / "cache" / "audio"


def _convert_qta_to_m4a(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    cmd = [FFMPEG, "-y", "-i", str(src), "-c:a", "aac", "-b:a", "128k", str(dst)]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {proc.stderr[:500]}")


def load(raw: RawDocument) -> RawDocument:
    """Convert .qta -> .m4a; otherwise pass through. Returns updated RawDocument."""
    src = Path(raw.path)
    ext = src.suffix.lower()
    if ext == ".m4a":
        return raw
    if ext == ".qta":
        dst = CACHE_DIR / f"{raw.content_hash}.m4a"
        if not dst.exists():
            _convert_qta_to_m4a(src, dst)
        metadata = dict(raw.metadata)
        metadata["original_path"] = str(src)
        metadata["converted"] = True
        return RawDocument(
            content_hash=raw.content_hash,
            source=raw.source,
            path=dst,
            metadata=metadata,
        )
    return raw
