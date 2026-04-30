from __future__ import annotations

from pathlib import Path
from typing import Iterable


class FingerprintError(Exception):
    """Base class for fingerprint errors."""


class FingerprintUnavailable(FingerprintError):
    """fpcalc binary missing or pyacoustid not importable."""


class FingerprintFailed(FingerprintError):
    """fpcalc failed on this specific file (corrupt/unreadable)."""


def fingerprint_file(path: Path) -> tuple[float, str]:
    """Return (duration_seconds, fingerprint_string) for an audio file.

    Raises FingerprintUnavailable if fpcalc/acoustid is unavailable.
    Raises FingerprintFailed for unreadable or corrupt input.
    Never returns None or empty string silently.
    """
    try:
        import acoustid
    except ImportError as exc:
        raise FingerprintUnavailable("pyacoustid is not installed") from exc

    try:
        duration, fp_bytes = acoustid.fingerprint_file(str(path))
    except acoustid.NoBackendError as exc:
        raise FingerprintUnavailable("fpcalc binary not found") from exc
    except acoustid.FingerprintGenerationError as exc:
        raise FingerprintFailed(f"Failed to fingerprint {path}: {exc}") from exc

    if not fp_bytes:
        raise FingerprintFailed(f"Empty fingerprint returned for {path}")

    fp_string = fp_bytes.decode("ascii") if isinstance(fp_bytes, bytes) else fp_bytes
    return float(duration), fp_string


def cluster_by_fingerprint(
    items: Iterable[tuple[str, str]],
) -> dict[str, list[str]]:
    """Group (content_hash, fp_string) pairs by fp_string using exact equality.

    Returns a dict mapping fp_string -> list of content_hashes.
    All groups are returned (size 1 and above); callers filter as needed.
    """
    clusters: dict[str, list[str]] = {}
    for content_hash, fp_string in items:
        clusters.setdefault(fp_string, []).append(content_hash)
    return clusters
