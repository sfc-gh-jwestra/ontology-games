# Ontology vs Baseline compare app

A React + FastAPI app that runs on your machine. It sends the same question to
`GAMING_BASELINE_AGENT` (semantic view only) and `GAMING_BON_AGENT` (semantic view + Business
Ontology search) at the same time. Both answers stream side by side, and an AI_COMPLETE judge
grounded in `ontology_setup/ontology_eval_set.md` explains why the answers differ.

Nothing is deployed to Snowflake. UI edits hot-reload in the browser and backend edits restart
uvicorn automatically.

## How it works

- **Sign-in:** Snowflake OAuth (authorization code + PKCE) through the security integration
  `ONTOLOGY_COMPARE_LOCAL_OAUTH`. You pick a role from `APP_ROLES` in `backend/.env` (default
  `ONTOLOGY_APP_ROLE`), and the session uses only that role (`OAUTH_USE_SECONDARY_ROLES = NONE`).
  Tokens stay in backend memory behind an HttpOnly cookie and are refreshed before they expire.
  Restarting the backend signs you out.
- **Agent runs:** the backend runs both agents concurrently, as you, with
  `SNOWFLAKE.CORTEX.DATA_AGENT_RUN` over your OAuth SQL session. The REST `:run` endpoint rejected
  the app's OAuth token inside the BON agent's tool calls (`390303 Invalid OAuth access token`).
  SQL returns the whole answer at once, so each pane shows "running" and then the full answer
  with its steps. Stop cancels the query.
- **Verdict:** after both runs finish, one `AI_COMPLETE` call (claude-sonnet-4-5, JSON schema,
  temperature 0) runs as you and compares both answers with the eval key.
- **Questions:** parsed from `ontology_setup/ontology_eval_set.md` when the backend starts. Edits
  to that file trigger a reload.

## Layout

| Path | Purpose |
|---|---|
| `backend/main.py` | FastAPI routes: `/api/me`, `/api/questions`, `/api/compare` (SSE), cancel, SPA |
| `backend/oauth.py` | `/oauth/login`, `/oauth/callback`, `/oauth/logout`, `/api/roles`, token refresh |
| `backend/agents.py` | Agent runs via `DATA_AGENT_RUN` (async query, cancel), final-answer summarizer |
| `backend/judge.py` | AI_COMPLETE verdict |
| `backend/sf.py` | `.env` loading, REST headers, OAuth SQL connections |
| `backend/dev_mock.py` | Offline preview with fake agents and sign-in (no Snowflake) |
| `frontend/` | Vite + React UI; dev server proxies `/api` and `/oauth` to :8080 |
| `sql/01_local_oauth.sql` | OAuth integration and grants for `ONTOLOGY_APP_ROLE` |
| `dev.sh` | Starts uvicorn (:8080, reload) and Vite (:5173, HMR) |

## Setup (once)

1. Run `sql/01_local_oauth.sql` as ACCOUNTADMIN.
2. `cp backend/.env.example backend/.env`. You don't need to copy the client ID or secret. On the
   first sign-in the backend reads them from the integration through your `JWESTRA_AWS1` profile
   in `~/.snowflake/connections.toml` (`OAUTH_SECRETS_CONNECTION` / `OAUTH_SECRETS_ROLE`) and keeps
   them in memory only. If that profile signs in through the browser, expect one extra Snowflake
   login tab the first time. To skip the lookup, set `OAUTH_CLIENT_ID` and `OAUTH_CLIENT_SECRET`.
   To offer more roles, add them to `APP_ROLES` (comma-separated). Each one must be granted to
   you and have the same privileges as section 2 of the SQL file, including `READ ON ONTOLOGY
   DOMAIN` for each of the three domains. Without those, the BON agent's ontology search returns
   nothing, and the agent answers "no governed definition".
3. `pip install -r backend/requirements.txt`

## Run

```bash
bash app/dev.sh          # real agents; open http://localhost:5173 and sign in
bash app/dev.sh --mock   # fake agents, no Snowflake
```

ACCOUNTADMIN, ORGADMIN and SECURITYADMIN can't sign in through OAuth by default, so use a normal
role.

## Tests

```bash
cd app/backend
python3 test_compare.py && python3 -c "import test_questions as t; [getattr(t,n)() for n in dir(t) if n.startswith('test_')]"
```
