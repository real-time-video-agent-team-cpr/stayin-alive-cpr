#!/usr/bin/env bash
# One-command demo: venv, install, serve. Then open http://localhost:8000
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -d .venv ]; then
  echo "creating venv..."
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q -r requirements.txt

echo ""
echo "==================================================="
echo "  SHOREGUARD demo running at http://localhost:8000"
echo "  Mode: SIMULATED FEED (deterministic incident ~T+23s)"
echo "  Ctrl-C to stop"
echo "==================================================="
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
