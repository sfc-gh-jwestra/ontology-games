# ontology-games

A Snowflake Business Ontology demo on two deliberately complex game-business systems, a game catalog and a sales system. It compares two Cortex Agents on the same 13 eval questions (11 that show the ontology's uplift, plus 2 controls): a baseline agent that only has a semantic view, and an agent that also searches Business Ontology. The ontology resolves the complexity: different names for the same thing, imperfect keys, a code crosswalk, divergent codes, overloaded columns and genre roll-ups.

- **Data:** loaded from the Parquet files in `data/`. **Nothing is generated.** To change the data, see [documentation/data-generation.md](documentation/data-generation.md) (what a generator must produce for the current schemas, and how).
- **Database:** `ONTOLOGY_DEMO`. Data and semantic views live in `GAME_CATALOG` and `GAME_SALES`; the agents live in `AGENTS`.
- **Semantic views:** one per system, split by ontology domain, plus one composed view that both demo agents use:

  | Semantic view | Covers |
  |---|---|
  | `GAME_CATALOG.SV_GAME_CATALOG` | Game Catalog domain: 20 catalog tables and views |
  | `GAME_CATALOG.SV_GENRE_TAXONOMY` | Genre Taxonomy domain: 18 tables and views (imports `SV_GAME_CATALOG` for games) |
  | `GAME_SALES.SV_GAME_COMMERCE` | Game Commerce domain: all 19 sales tables and views |
  | `GAME_CATALOG.SV_GAMING_CROSS_DOMAIN` | Imports the three above (all 57 tables and views) and adds the one strong-key join, `TITLES.CATALOG_GAME_ID` to `GAMES` |
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
- Business Ontology search can take a while to index new terms. Wait until `cortex search object "Game Revenue" --types=business-ontology` returns results before running the evaluation.
- To check an install against the last known state, compare row counts and answers with [documentation/install-baseline-snapshot.md](documentation/install-baseline-snapshot.md).

## Layout

```
install.sh                    install runner (steps 00-06)
install/                      generated NN-*.sql, plus 01-setup-db.sql (hand-written)
scripts/
  generate_install_sql.py     writes install/02, 03, 04a, 04b from the sources below
  build_ontology.py           Business Ontology content (domains, terms, relationships, representations)
  agent_routing_check.sql     routing check for the optional router demo
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
