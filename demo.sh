#!/usr/bin/env bash
# Scripted playthrough for recordings and screenshots.
# Drives the menu: CRACK -> mission 1 -> win -> exit.
set -euo pipefail
cd "$(dirname "$0")"

commands=(
  "1"                 # CRACK — mission list
  "1"                 # Mission 1
  "scan"
  "connect 10.10.10.10"
  "cat index.html"
  "login 10.10.10.20 admin Sunshine2024"
  "cat flag.txt"
  "flag"
  "5"                 # exit
)

for c in "${commands[@]}"; do
  sleep 0.7
  printf '%s\n' "$c"
done | env -u NO_COLOR python3 cli.py
