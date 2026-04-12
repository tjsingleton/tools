from kp.sources.voice_memo.discover import discover, sha256_file
from kp.sources.voice_memo.load import load
from kp.sources.voice_memo.normalize import normalize
from kp.pipeline.plugin import SourcePlugin  # re-export


class VoiceMemoPlugin:
    name = "voice_memo"

    def discover(self, path):
        return discover(path)

    def load(self, raw):
        return load(raw)

    def normalize(self, raw):
        return normalize(raw)


__all__ = ["VoiceMemoPlugin", "discover", "load", "normalize", "sha256_file", "SourcePlugin"]
