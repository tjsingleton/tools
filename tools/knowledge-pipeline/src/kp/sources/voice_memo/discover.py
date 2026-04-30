from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator

import structlog

from kp.pipeline.plugin import RawDocument
from kp.sources.voice_memo.fingerprint import FingerprintFailed, fingerprint_file
from kp.sources.voice_memo.load import CACHE_DIR, _convert_qta_to_m4a

log = structlog.get_logger()


AUDIO_EXTS = {".m4a", ".qta"}
TRANSCRIPT_EXTS = {".vtt", ".srt"}
_CANONICAL_JSON = "voice_memo_transcript_pairs_canonical.json"

# Match the polished_memo filename pattern to extract source_title
_POLISHED_STEM_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}\s+-\s+\d+\s+-\s+(?P<source_title>.+?)\s+-\s+.+$"
)

_VOICE_MEMOS_RE = re.compile(r"^(\d{8})\s+(\d{6})")  # 20260214 143432
_ISO_DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")     # 2025-10-26


def _recorded_at_from_filename(name: str) -> str | None:
    """Return an ISO 8601 string if filename encodes a date, else None."""
    m = _VOICE_MEMOS_RE.match(name)
    if m:
        try:
            dt = datetime.strptime(m.group(1) + m.group(2), "%Y%m%d%H%M%S")
            return dt.replace(tzinfo=timezone.utc).isoformat()
        except ValueError:
            pass
    m = _ISO_DATE_RE.search(name)
    if m:
        try:
            dt = datetime.strptime(m.group(1), "%Y-%m-%d")
            return dt.replace(tzinfo=timezone.utc).isoformat()
        except ValueError:
            pass
    return None


def _recorded_at_from_mtime(path: Path) -> str | None:
    try:
        ts = os.stat(path).st_mtime
        return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
    except OSError:
        return None


def sha256_file(path: Path, *, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def _load_canonical_json(root: Path) -> dict[str, Any]:
    """Search up to 2 parent levels for the canonical pairs JSON."""
    for candidate in [root, root.parent, root.parent.parent]:
        p = candidate / _CANONICAL_JSON
        if p.is_file():
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                pass
    return {}


def _build_canonical_audio_index(canonical_data: dict) -> dict[str, dict]:
    """Map audio filename -> entry from the canonical JSON."""
    index: dict[str, dict] = {}
    entries = canonical_data if isinstance(canonical_data, list) else canonical_data.get("entries", [])
    for entry in entries:
        for audio_name in entry.get("audio_files", []):
            index[audio_name] = entry
    return index


def _find_polished_md(polished_dir: Path, audio_stem: str) -> Path | None:
    """Look in polished_dir for an .md whose source_title portion matches audio_stem."""
    if not polished_dir.is_dir():
        return None
    for md in polished_dir.glob("*.md"):
        m = _POLISHED_STEM_RE.match(md.stem)
        if m and m.group("source_title") == audio_stem:
            return md
    return None


def discover(path: Path) -> Iterator[RawDocument]:
    """Glob audio files; emit RawDocument per unique content_hash and fingerprint.

    Deduplicates by both sha256 (exact byte identity) and chromaprint fingerprint
    (acoustic identity). For .qta sources the cache .m4a is fingerprinted so the
    fingerprint matches the .m4a of the same recording.

    If FingerprintFailed is raised for a file it is logged as a warning and skipped
    entirely — no RawDocument is emitted. FingerprintUnavailable (fpcalc missing)
    propagates as a fatal config error.
    """
    root = Path(path)
    seen: set[str] = set()
    seen_fp: dict[str, Path] = {}  # fp_string -> kept file path
    files: Iterable[Path]
    if root.is_file():
        files = [root]
        search_root = root.parent
    else:
        # sorted() ensures .m4a sorts before .qta (m < q) within the same directory,
        # which implements the tie-break: first .m4a seen wins.
        files = sorted(p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in AUDIO_EXTS)
        search_root = root

    # Load canonical JSON once
    canonical_data = _load_canonical_json(search_root)
    canonical_index = _build_canonical_audio_index(canonical_data)

    # Locate polished_transcripts sibling dir
    polished_dir = search_root / "polished_transcripts"

    for fp in files:
        try:
            h = sha256_file(fp)
        except OSError:
            continue
        if h in seen:
            continue

        # Resolve the audio path for fingerprinting.
        # .qta files must be fingerprinted via their cache .m4a so the fingerprint
        # is consistent with the re-encoded audio Whisper transcribes.
        ext = fp.suffix.lower()
        if ext == ".qta":
            cache_m4a = CACHE_DIR / f"{h}.m4a"
            if not cache_m4a.exists():
                try:
                    _convert_qta_to_m4a(fp, cache_m4a)
                except Exception as exc:
                    log.warning("discover.fingerprint_failed", path=str(fp), error=str(exc))
                    continue
            audio_for_fp = cache_m4a
        else:
            audio_for_fp = fp

        try:
            duration, fp_str = fingerprint_file(audio_for_fp)
        except FingerprintFailed as exc:
            log.warning("discover.fingerprint_failed", path=str(fp), error=str(exc))
            continue
        # FingerprintUnavailable propagates — it is a fatal config error.

        if fp_str in seen_fp:
            kept_path = seen_fp[fp_str]
            log.info(
                "discover.fingerprint_collapse",
                kept_path=str(kept_path),
                collapsed_path=str(fp),
                fingerprint_prefix=fp_str[:16],
            )
            continue

        seen_fp[fp_str] = fp
        seen.add(h)

        metadata: dict[str, Any] = {
            "filename": fp.name,
            "ext": ext,
            "size_bytes": fp.stat().st_size,
        }

        # Look for sibling transcript file (.vtt / .srt, case-insensitive)
        for sibling in fp.parent.iterdir():
            if sibling.stem == fp.stem and sibling.suffix.lower() in TRANSCRIPT_EXTS:
                metadata["macwhisper_vtt_path"] = str(sibling)
                break

        # Look up in canonical JSON
        canonical_entry = canonical_index.get(fp.name)
        if canonical_entry:
            metadata["canonical_stem"] = canonical_entry.get("canonical_stem", "")

        # Look for paired polished .md
        polished_md = _find_polished_md(polished_dir, fp.stem)
        if polished_md:
            metadata["polished_md_path"] = str(polished_md)

        # Determine recorded_at from best available signal
        recorded_at = _recorded_at_from_filename(fp.name)
        if recorded_at is None and canonical_entry:
            modified_range = canonical_entry.get("modified_range")
            if modified_range and len(modified_range) > 0:
                try:
                    dt = datetime.strptime(modified_range[0], "%b %d, %Y %H:%M")
                    recorded_at = dt.replace(tzinfo=timezone.utc).isoformat()
                except (ValueError, TypeError):
                    pass
        if recorded_at is None:
            recorded_at = _recorded_at_from_mtime(fp)
        metadata["recorded_at"] = recorded_at

        yield RawDocument(
            content_hash=h,
            source="voice_memo",
            path=fp,
            metadata=metadata,
            audio_fingerprint=(duration, fp_str),
        )
