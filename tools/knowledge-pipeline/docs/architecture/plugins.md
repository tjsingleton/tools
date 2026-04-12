# Plugins

A source plugin implements the `SourcePlugin` Protocol (`kp.pipeline.plugin`):

```python
class SourcePlugin(Protocol):
    name: str
    def discover(self, path: Path) -> Iterable[RawDocument]: ...
    def load(self, raw: RawDocument) -> RawDocument: ...
    def normalize(self, raw: RawDocument) -> Document: ...
```

## voice_memo
- `discover`: globs `.m4a` + `.qta`, SHA-256 hashes for dedupe.
- `load`: converts `.qta` -> `.m4a` via `ffmpeg` into `~/Library/KnowledgePipeline/cache/audio/`.
- `normalize`: produces canonical `Document` with transcribed text + metadata.
- Transcription is a pluggable backend: `faster_whisper` (default) or `pywhispercpp` (stub).

## Future plugins
- `chatgpt_export` — ingest conversations JSON export.
- `notes_md` — ingest Obsidian/plain markdown notes.

New plugins go in `src/kp/sources/<name>/` and register in `kp.cli._get_plugin`.
