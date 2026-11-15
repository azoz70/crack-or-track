#!/usr/bin/env bash
# Record the demo as a cast file, then convert it to a GIF.
set -euo pipefail
cd "$(dirname "$0")"

if ! command -v asciinema >/dev/null 2>&1; then
  echo "Install asciinema first: brew install asciinema"
  exit 1
fi

echo "[*] Recording demo.cast ..."
asciinema rec demo.cast -c ./demo.sh --overwrite

if command -v agg >/dev/null 2>&1; then
  echo "[*] Converting to demo.gif ..."
  agg demo.cast demo.gif
  echo "[+] Wrote demo.gif — add it to README.md"
else
  echo "Install agg for GIF conversion: brew install agg"
fi
