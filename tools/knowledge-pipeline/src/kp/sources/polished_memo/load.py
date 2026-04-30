from __future__ import annotations

from kp.pipeline.plugin import RawDocument


def load(raw: RawDocument) -> RawDocument:
    """Pass-through; markdown files need no conversion."""
    return raw
