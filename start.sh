#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
exec .venv/bin/python run.py "$@"
