from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Iterator

from kp.pipeline.plugin import RawDocument


# Pattern: {YYYY-MM-DD} - {sort_order} - {source_title} - {generated_title}.md
_FILENAME_RE = re.compile(
    r"^(?P<date>\d{4}-\d{2}-\d{2})"
    r"\s+-\s+(?P<sort_order>\d+)"
    r"\s+-\s+(?P<source_title>.+?)"
    r"\s+-\s+(?P<generated_title>.+)$"
)


def sha256_content(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def discover(path: Path) -> Iterator[RawDocument]:
    """Glob *.md files; emit RawDocument per unique content_hash."""
    root = Path(path)
    seen: set[str] = set()
    files: list[Path]
    if root.is_file():
        files = [root]
    else:
        files = sorted(p for p in root.rglob("*.md") if p.is_file())

    for fp in files:
        try:
            h = sha256_content(fp)
        except OSError:
            continue
        if h in seen:
            continue
        seen.add(h)

        metadata: dict = {
            "filename": fp.name,
            "ext": ".md",
            "size_bytes": fp.stat().st_size,
        }

        stem = fp.stem
        m = _FILENAME_RE.match(stem)
        if m:
            metadata["date"] = m.group("date")
            metadata["sort_order"] = int(m.group("sort_order"))
            metadata["source_title"] = m.group("source_title")
            metadata["generated_title"] = m.group("generated_title")
        else:
            metadata["stem"] = stem

        yield RawDocument(
            content_hash=h,
            source="polished_memo",
            path=fp,
            metadata=metadata,
        )
