#!/usr/bin/env bash
# Local OCR — Gradio UI 실행 (http://127.0.0.1:7860)
set -e
cd "$(dirname "$0")"

if command -v python3 >/dev/null 2>&1; then
  PY=python3
else
  PY=python
fi

echo "Starting Gradio at http://127.0.0.1:7860  (Ctrl+C to stop)"
exec $PY app.py
