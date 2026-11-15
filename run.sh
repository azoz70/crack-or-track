#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
exec ./.venv/bin/uvicorn app:app --host 127.0.0.1 --port 8800
