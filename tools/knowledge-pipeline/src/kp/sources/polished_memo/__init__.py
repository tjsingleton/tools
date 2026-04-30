from __future__ import annotations

from kp.sources.polished_memo.discover import discover, sha256_content
from kp.sources.polished_memo.load import load
from kp.sources.polished_memo.normalize import normalize
from kp.pipeline.plugin import SourcePlugin  # re-export


class PolishedMemoPlugin:
    name = "polished_memo"

    def discover(self, path):
        return discover(path)

    def load(self, raw):
        return load(raw)

    def normalize(self, raw, **kwargs):
        return normalize(raw, **kwargs)


__all__ = ["PolishedMemoPlugin", "discover", "load", "normalize", "sha256_content", "SourcePlugin"]
