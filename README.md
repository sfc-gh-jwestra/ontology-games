# ontology-games

> **Disclaimer.** This demo uses game data publicly sourced from the web, so it may contain inaccuracies when compared with real data. All revenue and sales data is fictional and synthetically generated, based on how games have historically earned revenue. Sony was chosen because of the popularity of its platform. Microsoft (Xbox), Nintendo, or a completely fictional game and console provider would serve the demonstration equally well.

A Snowflake Business Ontology demo on two deliberately complex game-business systems, a game catalog and a sales system. It compares two Cortex Agents on the same 13 eval questions (11 that show the ontology's uplift, plus 2 controls): a baseline agent that only has a semantic view, and an agent that also searches Business Ontology. The ontology resolves the complexity: different names for the same thing, imperfect keys, a code crosswalk, divergent codes, overloaded columns and genre roll-ups.

> **Plan for Business Ontology indexing time.** After the install builds the ontology (step 04), Business Ontology search can take **several hours** to index the new terms. Until it finishes, the ontology agent can't find its definitions, so it answers like the baseline, and evals and Live comparisons understate the uplift. The rest of the install doesn't wait for it. If you install with CoCo, you can stop and later say "resume the ontology-games install" to pick up where it left off and re-check the index. See [Install, step by step](#install-step-by-step).

- **Data:** loaded from the Parquet files in `data/`. **Nothing is generated.** To change the data, see [documentation/data-generation.md](documentation/data-generation.md) (what a generator must produce for the current schemas, and how).
- **Database:** `ONTOLOGY_DEMO`. Data and semantic views live in `GAME_CATALOG` and `GAME_SALES`; the agents live in `AGENTS`.
- **Semantic views:** one per system, split by ontology domain, plus one composed view that both demo agents use:

  | Semantic view | Covers |
  |---|---|
  | `GAME_CATALOG.SV_GAME_CATALOG` | Game Catalog domain: 20 catalog tables and views |
  | `GAME_CATALOG.SV_GENRE_TAXONOMY` | Genre Taxonomy domain: 18 tables and views (imports `SV_GAME_CATALOG` for games) |
  | `GAME_SALES.SV_GAME_COMMERCE` | Game Commerce domain: 18 sales tables and views |
  | `GAME_CATALOG.SV_GAMING_CROSS_DOMAIN` | Imports the three above (all 56 tables and views) and adds the one strong-key join, `TITLES.CATALOG_GAME_ID` to `GAMES` |
- **Questions and expected answers:** [documentation/ontology_eval_set.md](documentation/ontology_eval_set.md).

## Prerequisites

- A Snowflake account with Business Ontology and Cortex Agents enabled, and the `ACCOUNTADMIN` role.
- [Snowflake CLI](https://docs.snowflake.com/en/developer-guide/snowflake-cli/index) (`snow`) with a connection in `~/.snowflake/connections.toml`:

  ```toml
  [ONTOLOGY_DEMO_CONN]
  account = "<orgname>-<accountname>"
  user = "<your_user>"
  authenticator = "externalbrowser"
  role = "ACCOUNTADMIN"
  warehouse = "COMPUTE_WH"
  database = "ONTOLOGY_DEMO"
  ```

  To use a connection with a different name, set `SNOWFLAKE_CONNECTION_NAME=<name>` before running the install. The web app's Live mode reads the same variable.
- A `COMPUTE_WH` warehouse. The dynamic tables, agents and semantic views use it.
- Python 3 with `pyyaml` (`pip install pyyaml`).
- For the web app only: Node.js. `app/dev.sh` installs the backend packages into `app/.venv`.

## Easy button: install with CoCo

Open this folder in [Cortex Code](https://docs.snowflake.com/en/user-guide/cortex-code/cortex-code) and paste:

```
Install the ontology-games demo in this repo into my Snowflake account, using the
connection ONTOLOGY_DEMO_CONN.

First, create a plan; don't run anything yet. Read README.md, install.sh and install/,
check that the connection works and uses a role that can do this install (ACCOUNTADMIN),
then plan each install step (00 to 06) with what it will create. Stop and let me review
the plan.

When I build the plan, run the install with install.sh one step at a time, and tell me
after each step what was created. Record progress in project memory. After step 04, check
whether Business Ontology search returns "Game Revenue"; if not, tell me it is still
indexing. Run step 06 in a background terminal and finish with the compare app open at
http://localhost:5173.
```

CoCo creates the plan first, so you can see every object it will create before anything runs. Clicking **Build** on the plan starts the install. Because CoCo records progress in its project memory, you can stop at any point and say "resume the ontology-games install" later.

Business Ontology indexing after step 04 can take **hours**. If CoCo reports that search doesn't return "Game Revenue" yet, let it finish the remaining steps, then come back later and ask CoCo to resume. It re-checks the index and tells you when the ontology agent is ready for evals and Live comparisons.

## Install, step by step

From the repo root:

```bash
bash install.sh            # all steps, in order
bash install.sh --list     # show steps and which have completed
bash install.sh --from 03  # resume at a step
bash install.sh --only 04  # run one step
```

| Step | What it does | File or command |
|---|---|---|
| 00 | Regenerates the install SQL from its sources | `python3 scripts/generate_install_sql.py` |
| 01 | Creates `ONTOLOGY_DEMO`, the `GAME_CATALOG`, `GAME_SALES` and `AGENTS` schemas, `PUBLIC.DATA_STAGE` and `PUBLIC.PARQUET_FF`. Drops the retired `GAME_SALES_GEN` schema. | `install/01-setup-db.sql` (hand-written) |
| 02 | **Loads the data:** PUTs `data/<SCHEMA>/*.parquet` to the stage, creates the 43 tables from `sql/<SCHEMA>/tables/`, runs one `COPY INTO ... MATCH_BY_COLUMN_NAME` per table, then creates the functions, procedures, views and dynamic tables in dependency order | `install/02-load-data.sql` |
| 03 | Creates the four semantic views above, then six agents in `AGENTS`: `GAMING_BASELINE_AGENT` and `GAMING_BON_AGENT` (both over `SV_GAMING_CROSS_DOMAIN`), and the optional router demo (`GAMING_ROUTER_AGENT` plus catalog, genre and sales agents; see [documentation/agent_router_demo.md](documentation/agent_router_demo.md)) | `install/03-deploy-sv-and-agents.sql` |
| 04 | Business Ontology: 3 domains, 72 terms, 98 relationships, 96 representations. Builds on a fresh account (`04a`). If the domains already exist, it rewrites descriptions and formulas in place instead (`04b`). | `install/04a-build-ontology.sql` or `04b-refresh-ontology.sql` |
| 05 | `ONTOLOGY_APP_ROLE` and its grants, the role the web app's Live mode and the batch eval run as | `app/sql/01_app_role.sql` |
| 06 | Starts the compare web app at http://localhost:5173 (Setup, Compare and Analysis tabs; no login, Recorded mode by default). It runs in the foreground; Ctrl-C stops it. See [app/README.md](app/README.md). | `bash app/dev.sh` |

**Notes**
- Progress is saved in `.install_state`; delete it to start over.
- Step 02 replaces every table with `CREATE OR REPLACE`, so re-running it resets the data to the Parquet snapshot.
- **Business Ontology indexing can take hours.** After step 04, search may return nothing for new terms for several hours. Steps 05 and 06 don't depend on it, so the install can finish, and Recorded mode works right away. Wait until `cortex search object "Game Revenue" --types=business-ontology` returns results before running the batch eval or comparing agents Live. If you're installing with CoCo, you can stop here and later ask it to "resume the ontology-games install" to re-check the index.
- To check an install against the last known state, compare row counts and answers with [documentation/install-baseline-snapshot.md](documentation/install-baseline-snapshot.md).
- To re-run the graded eval, see [Re-run the batch eval](#re-run-the-batch-eval) below.

## Re-run the batch eval

The install does **not** run the eval. The web app's Recorded mode and Analysis tab show the run committed in `evaluations/results/latest.json`. That run was recorded on another account, so re-run the eval to score the agents in yours.

**Before you run it:** finish the install, through step 05 at least. Also wait for Business Ontology search to index the new terms (see the notes above). Otherwise the ontology agent scores low because its ontology search returns nothing.

```bash
# From the repo root. Runs all 13 questions through both agents, then grades each pair.
SNOWFLAKE_CONNECTION_NAME=<connection> python3 scripts/batch_eval.py

# Options
python3 scripts/batch_eval.py --only 3,5,6          # a subset of question ids
python3 scripts/batch_eval.py --workers 2           # fewer parallel runs (default 4)
python3 scripts/batch_eval.py --role <role> --warehouse <wh>   # defaults: ONTOLOGY_APP_ROLE, COMPUTE_WH
python3 scripts/batch_eval.py --summarize evaluations/results/latest.json   # rebuild the .md only, no Snowflake
python3 scripts/batch_eval.py --rejudge evaluations/results/latest.json     # grade the recorded answers again (13 judge calls, no agent runs)
```

**What a run does:**
- Calls `SNOWFLAKE.CORTEX.DATA_AGENT_RUN` for `GAMING_BASELINE_AGENT` and `GAMING_BON_AGENT` on every question in [documentation/ontology_eval_set.md](documentation/ontology_eval_set.md), as `ONTOLOGY_APP_ROLE` with no secondary roles.
- Records each answer's text, every tool call in order, the SQL it ran, row counts, tokens and elapsed time.
- Grades both answers in one `AI_COMPLETE` call (claude-sonnet-4-5, temperature 0). It uses the same judge as the app's Live mode (`app/backend/judge.py`):

  | Score | Meaning |
  |---|---|
  | 1.0 | Amounts within 1% of expected, and counts and names exact |
  | 0.67 | Amounts within 3% of expected |
  | 0.33 | The right answer appears only as an alternative |
  | 0 | Anything else |

  A score of 0.67 or more counts as correct. The judge also names the ontology nodes the ontology agent applied and how; `app/backend/ontology_trace.py` adds expected-node coverage and the relationships between those nodes.
- Takes several minutes and uses credits: 26 agent runs plus 13 judge calls.

**What it updates** (all under `evaluations/results/`):

| File | Contents | In git? |
|---|---|---|
| `<run_id>.json` | The full run, with `run_id` = `YYYYMMDD_HHMM` | No (ignored) |
| `<run_id>.md` | A readable summary: scores by challenge C1-C7, then "Why answers failed" with the judge's reasons, then "How the ontology helped" (applied nodes, expected coverage, relationships) | No (ignored) |
| `latest.json` | A copy of the newest run's JSON | **Yes** |

`--only` runs also overwrite `latest.json`, so the app then shows only that subset.

**How it changes the UI:** the app backend reads `latest.json` on every request, so the new run appears when you reload the page. You don't need to restart the app.
- **Compare tab, Recorded mode:** each question shows the new answers, scores, judge reasons, tool calls and SQL. The scorecard by challenge and the batch run id under the picker both update.
- **Analysis tab:** the stat cards (including expected ontology nodes applied) and every question card (behaviour table with the ontology nodes applied, answers, reasons, and the "How the Business Ontology helped" box) show the new run.
- **Live mode** doesn't use `latest.json`. It runs the agents again and grades them with the same judge.

To keep a run as the demo's default, commit the new `latest.json`. To go back to the committed one, run `git checkout evaluations/results/latest.json`.

## Multi-agent router demo

An optional front-door agent, `GAMING_ROUTER_AGENT`, uses the preview `agent_router` tool to send each question to the domain agent that owns it. It isn't part of the with/without-ontology comparison, and none of these agents search the Business Ontology. Details: [documentation/agent_router_demo.md](documentation/agent_router_demo.md). Tool background: [documentation/agent_router.md](documentation/agent_router.md).

| Agent (`ONTOLOGY_DEMO.AGENTS`) | Semantic view | Answers |
|---|---|---|
| `GAMING_CATALOG_AGENT` | `GAME_CATALOG.SV_GAME_CATALOG` | games, developers, publishers, franchises, release dates, lifecycle status |
| `GAMING_GENRE_AGENT` | `GAME_CATALOG.SV_GENRE_TAXONOMY` | genre membership, counts by genre, parent genres and subgenres |
| `GAMING_SALES_AGENT` | `GAME_SALES.SV_GAME_COMMERCE` | digital, hardware and subscription revenue, customers, regions, products |
| `GAMING_BASELINE_AGENT` | `GAME_CATALOG.SV_GAMING_CROSS_DOMAIN` | cross-domain questions, such as revenue by developer or genre |
| `GAMING_ROUTER_AGENT` | none | routes to one specialist, or several in parallel, and combines the answers |

**Deploy.** Install step 03 creates all five agents from `agents/router/*.yaml` and `agents/GAMING_BASELINE_AGENT.yaml`, and step 05 grants `ONTOLOGY_APP_ROLE` the access the check runs with. Step 03 re-creates the agents, which drops their grants, so to redeploy only the agents and semantic views, run 05 again afterwards:

```bash
bash install.sh --only 00 && bash install.sh --only 03 && bash install.sh --only 05
```

**Test with CoCo.** Paste:

```
Run scripts/agent_routing_check.sql against my Snowflake account using the connection
ONTOLOGY_DEMO_CONN, one statement at a time. For each question, show me a table with
the expected specialist, the subagent the router actually called (subagent_name), and
the answer. Flag any question that went to the wrong agent, and confirm that the catalog
agent declined the sales question without running SQL.
```

Or run it yourself: `snow sql -c ONTOLOGY_DEMO_CONN -f scripts/agent_routing_check.sql`. Each statement takes 30-120 seconds.

| # | Question | Expected route |
|---|---|---|
| 1 | How many games has Santa Monica Studio developed? | Catalog agent |
| 2 | How many RPG games are there? | Genre agent |
| 3 | What was hardware revenue in North America? | Sales agent |
| 4 | Which developer earned the most revenue? | Baseline agent (cross-domain). This gives the strong-key answer, not the governed one. |
| 5 | How many Horror games are there, and what was total subscription revenue? | Genre and Sales agents in parallel (`direct_route: false`) |
| 6 | Catalog agent asked directly: What was hardware revenue in North America? | Declines, no tool call |

**Caveats.**
- **Preview tool.** `agent_router` is a preview, undocumented tool, and `CREATE AGENT` doesn't validate it. After a change, check the spec with `DESCRIBE AGENT ONTOLOGY_DEMO.AGENTS.GAMING_ROUTER_AGENT`.
- **Snowsight.** Snowsight doesn't show the router's subagents, and it can't open semantic views that use `IMPORTS`.

## Layout

```
install.sh                    install runner (steps 00-06)
install/                      generated NN-*.sql, plus 01-setup-db.sql (hand-written)
scripts/
  generate_install_sql.py     writes install/02, 03, 04a, 04b from the sources below
  build_ontology.py           Business Ontology content (domains, terms, relationships, representations)
  agent_routing_check.sql     routing check for the optional router demo
  batch_eval.py               graded eval of both agents over all questions (writes evaluations/results/)
evaluations/results/          batch eval runs (<run_id>.json/.md, latest.json for the app's Recorded mode)
data/<SCHEMA>/*.parquet       the data (GAME_CATALOG, GAME_SALES)
sql/<SCHEMA>/<type>/*.sql     object DDL: tables, views, functions, procedures, dynamic_tables
semantic_views/               SV_GAME_CATALOG, SV_GENRE_TAXONOMY, SV_GAME_COMMERCE, SV_GAMING_CROSS_DOMAIN (.yaml;
                              line 1 names the target schema)
agents/                       GAMING_BASELINE_AGENT.yaml, GAMING_BON_AGENT.yaml
agents/router/                optional router demo: GAMING_ROUTER_AGENT + catalog, genre and sales agents
app/                          local web app comparing the two agents (Recorded and Live, graded LLM judge)
documentation/                design docs, ontology phases, eval set, data generation
```

Edit the sources (`sql/`, `semantic_views/`, `agents/`, `scripts/build_ontology.py`), not the generated files under `install/`. Step 00 regenerates them.

## Documentation

- [ontology-overview.md](documentation/ontology-overview.md): the ontology analysis and diagrams
- [business_ontology_phases.md](documentation/business_ontology_phases.md): the phased build guide and decision log (D1-D17)
- [ontology_eval_set.md](documentation/ontology_eval_set.md): questions, expected answers and reference SQL
- [README_ontology_games_challenges.md](documentation/README_ontology_games_challenges.md): the 7 data challenges in GAME_CATALOG and GAME_SALES
- [data-generation.md](documentation/data-generation.md): how to generate new data for the current schemas
- [genre-hierarchy-design-issue.md](documentation/genre-hierarchy-design-issue.md): genre roll-up design notes
- [agent_router_demo.md](documentation/agent_router_demo.md): the optional router agent and its domain agents
- [agent_router.md](documentation/agent_router.md): what the preview `agent_router` tool is and how it compares with `agent_toolset`
- [database-design.md](documentation/database-design.md): the `ONTOLOGY_DEMO` schemas and the objects in each
- [install-baseline-snapshot.md](documentation/install-baseline-snapshot.md): row counts and answers from the last known-good install
- [app/README.md](app/README.md): the compare web app (Recorded and Live modes, graded judge)
- [limitedaccess-links.md](documentation/limitedaccess-links.md): private preview docs used here: [Business Ontology](https://docs.snowflake.com/en/LIMITEDACCESS/snowflake-horizon/business-ontology), [Composable semantic views](https://docs.snowflake.com/en/LIMITEDACCESS/composable-semantic-views), and the agent router references
