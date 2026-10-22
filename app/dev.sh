#!/usr/bin/env bash
# Local dev loop: FastAPI with auto-reload on :8080 + Vite with hot reload on :5173.
#   bash app/dev.sh          real agents; sign in with Snowflake OAuth (needs backend/.env)
#   bash app/dev.sh --mock   fake agents and sign-in, no Snowflake
# Open http://localhost:5173. Ctrl-C stops both.
set -euo pipefail
cd "$(dirname "$0")"

MOCK=0
[[ "${1:-}" == "--mock" ]] && MOCK=1

if [[ $MOCK == 0 && ! -f backend/.env ]]; then
  echo "backend/.env is missing. Copy backend/.env.example and fill in the OAuth client (see sql/01_local_oauth.sql)." >&2
  exit 1
fi
[[ -d frontend/node_modules ]] || (cd frontend && npm install --no-audit --no-fund)

pids=()
cleanup() { kill "${pids[@]}" 2>/dev/null || true; wait 2>/dev/null || true; }
trap cleanup EXIT INT TERM

if [[ $MOCK == 1 ]]; then
  (cd backend && python3 dev_mock.py) &
else
  # Reload on backend code and on eval-set edits (questions are parsed at startup).
  (cd backend && python3 -m uvicorn main:app --host 127.0.0.1 --port 8080 --timeout-keep-alive 120 \
    --reload --reload-dir . --reload-dir ../../ontology_setup --reload-include '*.md') &
fi
pids+=($!)

(cd frontend && npm run dev) &
pids+=($!)

echo "UI: http://localhost:5173"
wait
