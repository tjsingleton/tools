# Bootstrap

One-time setup for the knowledge pipeline on macOS.

## 1. System deps
```bash
brew install ffmpeg ollama
ollama serve &        # background
ollama pull nomic-embed-text
```

## 2. Python env
```bash
cd tools/knowledge-pipeline
uv sync                # installs deps from pyproject.toml
```

## 3. Secrets
```bash
# macOS keyring (preferred):
python -c "import keyring; keyring.set_password('openrouter','api_key','<KEY>')"
# or env:
export OPENROUTER_API_KEY=<KEY>
```

## 4. Verify
```bash
uv run pytest -q
uv run python main.py budget status
uv run python main.py events tail --limit 1
```

If `pytest` is green and `budget status` prints, you are ready.
