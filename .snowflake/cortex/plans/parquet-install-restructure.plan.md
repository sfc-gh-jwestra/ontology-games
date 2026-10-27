# Plan: Parquet-based install, matching game_analytics_demo

## Context

**Sample: `~/Projects/cortex-sense/game_analytics_demo`**
- **`data/`**: `data/<SCHEMA>/<TABLE>_n_n_n.snappy.parquet`, 36 MB in total.
  - GAME_CATALOG: 31 files. GAME_SALES: 20 files; the large tables are split, e.g. HARDWARE_SALES_TRANSACTIONS has 4 parts.
  - Dynamic-table outputs are exported too (GAME_SIMILARITY_SCORES, GENRE_WHITESPACE_ANALYSIS, GAME_REVENUE, QUARTERLY_REVENUE). They are uploaded but not loaded, because the install recreates them as dynamic tables.
- **`sql/<SCHEMA>/<type>/<OBJECT>.sql`**: types are tables, views, functions, procedures and dynamic_tables. Uppercase schema folders; `BACKUP_*` tables are skipped.
- **`install.sh`**: numbered steps; flags `--from NN`, `--only NN`, `--list`; progress in `.install_state`; connection from `SNOWFLAKE_CONNECTION_NAME`; each step runs `snow sql -c "$CONN" --enable-templating NONE -f install/NN-*.sql`.
- **`scripts/generate_install_sql.py`** (step 00) regenerates the install SQL from the sources.
  - Step 02 does: PUT to `@PUBLIC.DATA_STAGE/<SCHEMA>/`; explicit table DDL, ordered by foreign keys; one `COPY INTO ... PATTERN '(.*/)?<T>_[0-9]+_[0-9]+_[0-9]+[.]snappy[.]parquet' MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE` per table; then functions, procedures, views and dynamic tables, ordered by dependency.
  - Step 03 runs `SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML`; step 09 runs `CREATE OR REPLACE AGENT ... FROM SPECIFICATION`.
- **README**: "Install, step by step", with a `connections.toml` example. There is no teardown.

**Fit with ontology-games**
- The sample's 31 Catalog and 16 Sales tables, in the messy shape (TITLES, TITLE_CODE_XREF, REVENUE_TYPES, GAMES with DEVELOPER_NAME/STATUS), match live `ONTOLOGY_DEMO` exactly.
- Its views (including `VW_GAME_GENRE_ROLLUP`) and dynamic tables match ours by name.
- This repo's `sql/` is **out of date**: it still has the clean shape from before the mess-up (DEVELOPERS, PUBLISHERS, FRANCHISES, GAME_SEQUELS, Sales GAMES, REVENUE_CATEGORIES). The sample's DDL becomes the table source, with `CORTEX_SENSE_DEMO` renamed to `ONTOLOGY_DEMO`.

**What to sunset**
- `sql/game_sales_gen/`: schema, 9 tables, 6 procedures (SP_GENERATE_SALES and the SP_GEN_* steps), UDF_U01, seeds.
- `sql/game_sales/retired/SP_GENERATE_MONTHLY_REVENUE.sql`.
- `sql/game_sales/tables/REVENUE_CATEGORIES.sql`, which inserts data.
- References to the generator in docs and comments.
- The live schema `ONTOLOGY_DEMO.GAME_SALES_GEN` (26 tables).
- `SP_CLASSIFY_GAMES` stays as an object. It derives classifications from rules rather than generating data, but the install no longer calls it, because classification rows come from Parquet.

**Decisions (from your answers)**
- Install into `ONTOLOGY_DEMO`.
- Steps: data, the semantic view and 2 agents, the Business Ontology, cross-domain, and the web app.
- Sunset generation in the repo and drop `GAME_SALES_GEN` in Snowflake. Document the generator logic first.
- Move every doc, including `resources/`, into `documentation/`.
- Leave `cross-domain/` alone. One unavoidable exception: `cross-domain/build_yamls.py` (and possibly `deploy.py`) reads `yamls/gaming_baseline_sv.yaml`. When that file moves, I'll change only that path string; nothing else in the folder.

## Target layout

```
ontology-games/
  README.md                      new: overview + "Install, step by step"
  install.sh                     new: runner modeled on the sample's
  install/                       generated NN-*.sql (plus 1 hand-written step)
  scripts/
    generate_install_sql.py      new: adapted from the sample's
    build_ontology.py            moved from ontology_setup/build/
  data/GAME_CATALOG/*.parquet    copied from the sample
  data/GAME_SALES/*.parquet
  sql/GAME_CATALOG/{tables,views,functions,procedures,dynamic_tables}/
  sql/GAME_SALES/{tables,views,dynamic_tables}/
  semantic_views/GAMING_BASELINE_SV.yaml
  agents/GAMING_BASELINE_AGENT.yaml, GAMING_BON_AGENT.yaml
  documentation/                 all ontology_setup/*.md, resources/*, data-generation.md (new)
  cross-domain/                  unchanged (except the one path string)
  app/                           unchanged
```

These are removed: `yamls/` (its YAMLs move, and `deploy_yamls.py` is replaced by the generator), `ontology_setup/`, `resources/`, the lowercase `sql/game_catalog/`, `sql/game_sales/` and `sql/game_sales_gen/`.

## Install steps

| Step | What it does | Source |
|---|---|---|
| 00 | `python3 scripts/generate_install_sql.py` | generator |
| 01 | Create `ONTOLOGY_DEMO`, the GAME_CATALOG, GAME_SALES and ONTOLOGY_AGENTS schemas, and `PUBLIC.DATA_STAGE` and `PUBLIC.PARQUET_FF` (the same file-format options as the sample). `DROP SCHEMA IF EXISTS ONTOLOGY_DEMO.GAME_SALES_GEN`. | hand-written |
| 02 | Load the data: PUT, then table DDL, then COPY INTO, then functions, procedures, views and dynamic tables | generated from `sql/` and `data/` |
| 03 | The semantic view in `ONTOLOGY_AGENTS`, then the two agents | generated from `semantic_views/` and `agents/` |
| 04 | Business Ontology: domains, terms, relationships and representations, from `build_ontology.py`. The domain creation calls aren't idempotent, so this step is **guarded**: if `SYSTEM$GET_GLOSSARY_SUMMARY()` already shows the 3 domains, it only applies the in-place description update (`SYSTEM$UPDATE_GLOSSARY_TERM`). | generated |
| 05 | Cross-domain: `python3 cross-domain/deploy.py` then `deploy_agents.py`, passing `--connection "$CONN"` | command |
| 06 | Web app OAuth: `app/sql/01_local_oauth.sql`. Prints a reminder to copy `app/backend/.env.example` to `.env`. | command |
| 07 | Start the web app with `bash app/dev.sh` (runs in the foreground; last step) | command |

## Implementation steps

1. **Snapshot before any change.**
   - Record the current row count of every `ONTOLOGY_DEMO` table, the eval reference answers (run the reference SQL from `ontology_eval_set.md`) and the glossary summary.
   - Keep the results in a file under `documentation/` so the post-install comparison has a baseline.
   - The Parquet export dates from 2026-10-22, from `CORTEX_SENSE_DEMO`, so values may differ from what is live.
2. **Document the generator** in `documentation/data-generation.md` before deleting it.
   - The pipeline order (SP_GEN_CATALOG, then CUSTOMERS_AND_HARDWARE, REVENUE_TARGETS, DIGITAL_SALES, SUBSCRIPTIONS), with each step's inputs, outputs, row-count logic and seeds.
   - The deterministic random function UDF_U01, the config tables and seed values, and the IS_ACTIVE 24-month rule.
   - How the messy shape (challenges C1 to C7) was applied, and the invariants a new generator must keep: TITLE_ID 5001-5090, every 10th transaction with NULL TITLE_ID, the SKU format, the region codes, and Y/N flags.
3. **Copy the data**: `cp -R ~/Projects/cortex-sense/game_analytics_demo/data ./data` (51 files).
4. **Rebuild `sql/`.**
   - Copy the sample's `sql/GAME_CATALOG` and `sql/GAME_SALES`, without `BACKUP_*`, renaming `CORTEX_SENSE_DEMO` to `ONTOLOGY_DEMO`.
   - Diff each view, dynamic table, procedure and function against this repo's version and against live `GET_DDL`. Where they differ, live `ONTOLOGY_DEMO` wins, and I'll report each difference.
   - Delete the old lowercase trees, including `game_sales_gen` and `retired/`.
5. **Move the YAML.**
   - `yamls/gaming_baseline_sv.yaml` goes to `semantic_views/GAMING_BASELINE_SV.yaml`; the agent YAMLs go to `agents/`.
   - Delete `yamls/deploy_yamls.py`.
   - Update the one path string in `cross-domain/build_yamls.py` (and in `deploy.py`, if it references the file).
6. **Write `scripts/generate_install_sql.py`**, adapted from the sample.
   - `DB = "ONTOLOGY_DEMO"`, `SCHEMAS = ["GAME_CATALOG", "GAME_SALES"]`.
   - `gen_02`: the sample's logic, unchanged.
   - `gen_03`: semantic view into `ONTOLOGY_AGENTS`, then the agents. Keep the drop-before-create from `deploy_yamls.py` and the `$$` guard.
   - `gen_04`: import `scripts/build_ontology.py`, emit the guarded ontology step (a Snowflake Scripting block that checks the domain count).
   - Move `build_ontology.py` to `scripts/`; it writes nothing on its own now.
7. **Write `install.sh` and `install/01-setup-db.sql`.**
   - Copy the sample's runner structure: steps, titles, `--from`, `--only`, `--list` and `.install_state`.
   - Default connection `JWESTRA_AWS1`, overridable with `SNOWFLAKE_CONNECTION_NAME`.
   - Add `.install_state` to `.gitignore`.
8. **Move the docs.**
   - `ontology_setup/*.md` and `resources/*` move to `documentation/`. Update the relative links and every path that changed (`yamls/`, `ontology_setup/build/`, `sql/game_catalog/...`) in the docs and in `app/`.
   - Mark `mess-up-database.md` and `messy_data_design.md` as historical: the messy state now ships in the Parquet files.
   - Replace the "re-run SP_GENERATE_SALES / RUN_ALL" guidance in the eval set with "re-install from `data/`".
9. **Write `README.md`**:
   - prerequisites (snow CLI, the connection, ACCOUNTADMIN, Python 3, Node for the app)
   - install step by step, and what each step creates
   - re-running and resuming
   - the layout
   - "no data generation; see `documentation/data-generation.md`"
10. **Run the install** with `./install.sh`: steps 00 to 06, with 07 started by hand. Then verify.

## Verification

- `./install.sh --list` shows every step; step 00 runs cleanly.
- **Data:** every table has the same row count as the Parquet files. The 4 dynamic tables refresh and their counts match the pre-install snapshot. Each `COPY INTO` reports 0 errors.
- **Objects:** the semantic view, both agents and the 5 cross-domain agents exist. `cross-domain/parity_check.sql` and `agent_routing_check.sql` pass.
- **Ontology:** the guarded step is a no-op apart from the description refresh. The glossary still has 70+ ACTIVE terms and the same relationship and representation counts.
- **Eval answers:** re-run the reference SQL. If any value differs from the snapshot because the Parquet data differs, update `ontology_eval_set.md` and the `FORBIDDEN` list in `build_ontology.py`, and report the differences.
- **Sunset:** `SHOW SCHEMAS LIKE 'GAME_SALES_GEN' IN DATABASE ONTOLOGY_DEMO` returns nothing, and a grep for `SP_GENERATE|GAME_SALES_GEN|SP_GEN_` finds hits only in `documentation/data-generation.md`.
- **Web app:** `bash app/dev.sh` starts and one comparison question gets an answer.

## Risks

- **Step 02 replaces the live tables.** The Parquet copy is the source from now on. The snapshot in step 1 is what lets you tell whether anything changed.
- **The views read the VIDEOWL schema?** It isn't in `data/`. If any object depends on it, the dependency will show during the diff in step 4; in that case VIDEOWL is left in place, not reinstalled.
- **`dev.sh` blocks.** As in the sample, step 07 is the last step and runs in the foreground.

## Critical Files

- `~/Projects/cortex-sense/game_analytics_demo/scripts/generate_install_sql.py`: the generator to adapt.
- `~/Projects/cortex-sense/game_analytics_demo/install.sh`: the runner pattern.
- [scripts/build_ontology.py](ontology_setup/build/build_ontology.py): becomes the source for install step 04.
- [cross-domain/build_yamls.py](cross-domain/build_yamls.py): the one path string to update.
- [sql/game_sales_gen/stored_procedures/SP_GENERATE_SALES.sql](sql/game_sales_gen/stored_procedures/SP_GENERATE_SALES.sql): the source for `data-generation.md` before deletion.
