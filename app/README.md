# Ontology vs Baseline compare app

A React + FastAPI app that runs on your machine. It compares `GAMING_BASELINE_AGENT` (semantic view
only) with `GAMING_BON_AGENT` (the same semantic view plus Business Ontology search) on the questions in
`documentation/ontology_eval_set.md`. There is no app login. The layout follows the
`game_analytics_demo` app, with three tabs:

- **Setup:** how the comparison works, the four semantic views, the three ontology domains, the seven
  data challenges with their questions, and the deployed agent YAML. Read from repo files.
- **Compare:** pick a question. The mode defaults to **Recorded**, which shows the answers, tool calls,
  SQL, tokens, score and judge reason from the latest batch run straight away, with no Snowflake
  connection. **Live** runs both agents now and judges them. A custom question always runs Live.
  A scorecard by challenge sits below.
- **Analysis:** the whole recorded run, grouped by challenge C1-C7. Each question shows a behaviour
  table (score, tool calls, tools used, tables touched, tokens, time), both answers, and the judge's
  reasons.

Nothing is deployed to Snowflake. UI edits hot-reload in the browser and backend edits restart
uvicorn automatically.

## How it works

- **Recorded mode** reads `evaluations/results/latest.json`, which `scripts/batch_eval.py` writes.
  Rerun that script to refresh it; the app picks up the new file on the next request.
- **Live mode** opens one named connection from `~/.snowflake/connections.toml` on the first Live run
  (`SNOWFLAKE_CONNECTION_NAME`, default `ONTOLOGY_DEMO_CONN`). If the profile signs in through the
  browser (`externalbrowser` or `OAUTH_AUTHORIZATION_CODE`), that is the only login, and the backend
  reuses the session until it restarts. The session switches to `APP_ROLE` (default
  `ONTOLOGY_APP_ROLE`) with no secondary roles, the same role the batch eval uses.
- **Agent runs:** both agents run at the same time with `SNOWFLAKE.CORTEX.DATA_AGENT_RUN` (async query
  plus polling). SQL returns the whole answer at once, so each pane shows "running" and then the full
  answer with its steps. Stop cancels the query.
- **Judge:** `backend/judge.py` is shared with the batch eval, so Live and Recorded scores mean the same
  thing. One AI_COMPLETE call (claude-sonnet-4-5, temperature 0) scores each answer: 1.0 when amounts are
  within 1% of expected, 0.67 within 3%, 0.33 when the right answer is only an alternative, and 0
  otherwise. Correct means 0.67 or higher.
- **Questions:** parsed from `documentation/ontology_eval_set.md` when the backend starts. Edits to that
  file trigger a reload.

## Layout

| Path | Purpose |
|---|---|
| `backend/main.py` | FastAPI routes: `/api/questions`, `/api/recorded`, `/api/setup`, `/api/live-status`, `/api/compare` (SSE), cancel, SPA |
| `backend/agents.py` | Agent runs via `DATA_AGENT_RUN` (async query, cancel); `parse_response`, shared with the batch eval |
| `backend/judge.py` | Graded AI_COMPLETE judge, shared with the batch eval |
| `backend/sf.py` | The lazy, shared Live connection |
| `backend/setup_info.py` | Setup tab content from `semantic_views/`, `agents/`, `scripts/build_ontology.py` and the challenges README |
| `backend/dev_mock.py` | Offline preview with fake Live agents and judge (no Snowflake) |
| `frontend/` | Vite + React UI (`App.tsx` tabs; `components/SetupView`, `CompareView`, `AnalysisView`, `common`) |
| `sql/01_app_role.sql` | `ONTOLOGY_APP_ROLE` and its grants (install step 05) |
| `dev.sh` | Creates `.venv`, starts uvicorn (:8080, reload) and Vite (:5173, HMR) |

## Setup (once)

1. Run `sql/01_app_role.sql` as ACCOUNTADMIN (install step 05 does this). The role needs
   `READ ON ONTOLOGY DOMAIN` for each of the three domains. Without it, the BON agent's ontology search
   returns nothing.
2. Optional: `cp backend/.env.example backend/.env` to change the connection, role or warehouse.

`dev.sh` creates `app/.venv` and installs `backend/requirements.txt` into it. The connector must be
version 3.15 or later to support the browser-based `OAUTH_AUTHORIZATION_CODE` authenticator.

## Run

```bash
bash app/dev.sh          # open http://localhost:5173; Live mode logs in on first use
bash app/dev.sh --mock   # fake Live agents, no Snowflake
```

## Tests

```bash
cd app/backend
python3 test_compare.py && python3 test_questions.py
```
