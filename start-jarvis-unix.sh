#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
command -v python3 >/dev/null || { echo 'Python 3.11+ is required.'; exit 1; }
command -v npm >/dev/null || { echo 'Node.js 22+ is required.'; exit 1; }
if [ ! -x backend/venv/bin/python ]; then
  python3 -m venv backend/venv
fi
backend/venv/bin/python -m pip install -r backend/requirements.txt
cd frontend
if [ ! -d node_modules ]; then npm ci; fi
echo 'Starting JARVIS. Ollama should be running separately.'
npm run electron:dev
