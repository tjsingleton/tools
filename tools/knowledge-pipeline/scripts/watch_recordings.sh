#!/usr/bin/env bash
set -euo pipefail

DUMP_DIR="/Volumes/DataDock/Users/tjsingleton/Archives/Misc/VOICE MEMO DUMP"
PIPELINE_DIR="/Volumes/DataDock/Users/tjsingleton/src/github.com/tjsingleton/tools/tools/knowledge-pipeline"

if [ ! -d "$DUMP_DIR" ]; then
  echo "$(date '+%Y-%m-%dT%H:%M:%S') kp-watcher: DataDock not mounted, skipping"
  exit 0
fi

cd "$PIPELINE_DIR"

exec uv run python main.py run \
  --source voice_memo \
  --path "$DUMP_DIR" \
  --stages ingest,normalize,diarize,analyze,embed \
  --whisper-model base \
  --no-dry-run
