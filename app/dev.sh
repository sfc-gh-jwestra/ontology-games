#!/usr/bin/env bash
# Local dev loop: FastAPI with auto-reload on :8080 + Vite with hot reload on :5173. No app login.
#   bash app/dev.sh          Recorded mode works offline; Live mode opens SNOWFLAKE_CONNECTION_NAME on first use
#   bash app/dev.sh --mock   fake Live agents and judge, no Snowflake at all
# Open http://localhost:5173. Ctrl-C stops both.
set -euo pipefail
cd "$(dirname "$0")"

MOCK=0
[[ "${1:-}" == "--mock" ]] && MOCK=1

# Optional overrides (SNOWFLAKE_CONNECTION_NAME, APP_ROLE, APP_WAREHOUSE).
if [[ -f backend/.env ]]; then set -a; source backend/.env; set +a; fi

# Backend virtual env: the browser-based connections.toml authenticators need connector 3.15+.
if [[ ! -x .venv/bin/python ]]; then
  python3 -m venv .venv
fi
.venv/bin/python -m pip install -q --disable-pip-version-check -r backend/requirements.txt
[[ -d frontend/node_modules ]] || (cd frontend && npm install --no-audit --no-fund)

pids=()
cleanup() { kill "${pids[@]}" 2>/dev/null || true; wait 2>/dev/null || true; }
trap cleanup EXIT INT TERM

if [[ $MOCK == 1 ]]; then
  (cd backend && ../.venv/bin/python dev_mock.py) &
else
  # Reload on backend code and on eval-set edits (questions are parsed at startup).
  (cd backend && ../.venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port 8080 --timeout-keep-alive 120 \
    --reload --reload-dir . --reload-dir ../../documentation --reload-include '*.md') &
fi
pids+=($!)

(cd frontend && npm run dev) &
pids+=($!)

echo "UI: http://localhost:5173  (Live connection: ${SNOWFLAKE_CONNECTION_NAME:-ONTOLOGY_DEMO_CONN})"
wait
