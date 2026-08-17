#!/usr/bin/env bash
# Uso: ./start.sh <TU_TOKEN>
set -e
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
  ./.venv/bin/pip install -q -r requirements.txt
fi
exec ./.venv/bin/python bot.py "$@"
