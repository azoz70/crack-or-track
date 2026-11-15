#!/usr/bin/env bash
# Scripted playthrough for recordings and screenshots.
# Usage: ./demo.sh
set -euo pipefail
cd "$(dirname "$0")"

commands=(
  "scan"
  "connect 10.10.10.10"
  "cat index.html"
  "login 10.10.10.20 admin Sunshine2024"
  "ls"
  "cat flag.txt"
  "flag"
)

for c in "${commands[@]}"; do
  sleep 0.8
  printf '%s\n' "$c"
done | python3 breach.py
