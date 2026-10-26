#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
if command -v uv >/dev/null 2>&1; then
  uv venv .venv --python 3.12
  uv pip install --python .venv/bin/python -r requirements.txt
else
  python3 -m venv .venv
  .venv/bin/python -m pip install -r requirements.txt
fi
printf '\nReady. Start ComfyUI, then run: sh start.sh\n'
