---
name: "remove-all-backups"
created: "2026-10-26T22:00:23.581Z"
status: pending
---

# Plan: Remove all backups

## Context

Inventory (read-only, ONTOLOGY\_DEMO only; DEMO not touched):

- Schema `BACKUP_GAMES_CORE` (14 tables, pre-split clone of GAMES\_CORE). Nothing reads it.
- Schema `CLEAN_BASELINE` (18 tables, pre-mess snapshot). Read by `sql/mess/` 00, 10, 21, 23, 24, 90, 99 and RUN\_ALL. User: drop it.
- `GAME_CATALOG.BACKUP_GENRE_RULES_20261009`, `BACKUP_GENRE_RULES_SINGLE_PARENT_20261009`, `BACKUP_GAME_GENRE_CLASSIFICATION_20261009`. Nothing reads them.
- `GAME_SALES_GEN.BACKUP_GAME_MNTHLY_REVENUE` (587 rows). Real generator input read by SP\_GEN\_CATALOG, SP\_GEN\_REVENUE\_TARGETS, SP\_GENERATE\_SALES. User: it belongs in GAME\_SALES\_GEN. It is already there.
- BACKUP\_CONTENT\_DESCRIPTORS / BACKUP\_GAME\_CONTENT\_DESCRIPTORS no longer exist in Snowflake; only their DDL files remain.

**Assumption:** "no backup anything" includes the name. So the revenue table stays in GAME\_SALES\_GEN, keeps its data, and is renamed to `SOURCE_GAME_MONTHLY_REVENUE`. Its readers get updated.

**Consequence:** dropping CLEAN\_BASELINE means the mess can no longer be restored or re-run. The current messy data stays as is. So the mess scripts that depend on the snapshot get deleted, not edited.

## Implementation steps

1. **Drop the Snowflake backups** (SQL tool, one statement each):

   - `DROP SCHEMA ONTOLOGY_DEMO.BACKUP_GAMES_CORE`
   - `DROP SCHEMA ONTOLOGY_DEMO.CLEAN_BASELINE`
   - `DROP TABLE` for the 3 GAME\_CATALOG backup tables

2. **Rename the revenue source** to `ALTER TABLE GAME_SALES_GEN.BACKUP_GAME_MNTHLY_REVENUE RENAME TO SOURCE_GAME_MONTHLY_REVENUE`. Then:

   - Recreate SP\_GEN\_CATALOG, SP\_GEN\_REVENUE\_TARGETS and SP\_GENERATE\_SALES from the edited files. Change the table name, and change the comment/label `'BACKUP'` to `'SOURCE'` in TARGET\_SOURCE and TARGET values.
   - Update the comments on GAME\_REVENUE\_TARGETS and on the GAME\_SALES\_GEN schema.
   - Do NOT run SP\_GENERATE\_SALES. It would wipe the messy data.

3. **Delete files:**

   - `sql/game_catalog/tables/BACKUP_CONTENT_DESCRIPTORS.sql`
   - `sql/game_catalog/tables/BACKUP_GAME_CONTENT_DESCRIPTORS.sql`
   - `sql/mess/00_snapshot_clean_baseline.sql`, `10_restore_from_baseline.sql`, `99_restore_clean.sql`, `RUN_ALL.sql`
   - `sql/mess/20-30` apply scripts and `90_verify_mess.sql`. These read CLEAN\_BASELINE or start with a restore, so they can't run anymore.

4. **Rename the file** `sql/game_sales_gen/tables/BACKUP_GAME_MNTHLY_REVENUE.sql` to `SOURCE_GAME_MONTHLY_REVENUE.sql` and update its DDL. Edit the other `sql/game_sales_gen` files (SCHEMA.sql, GAME\_REVENUE\_TARGETS.sql, the 3 procs) to match.

5. **Scrub the docs:**

   - `ontology_setup/ontology-overview.md`: lines 19, 180, 379.
   - `ontology_setup/messy_data_design.md`: the restore/snapshot section around lines 125-140. Replace it with a note that the mess is one-way and the scripts were removed.
   - In `.snowflake/cortex/plans/*.plan.md` (6 plans), delete the backup lines and sections; plans are historical.

6. **Skill** `~/.snowflake/cortex/skills/add-game-data-ontology/SKILL.md`: rename the table and delete any backup or restore steps (for example "run 99 first").

7. **Memory:**

   - In the project MEMORY.md, delete the BACKUP\_\* / CLEAN\_BASELINE / 99\_restore lines and the "backup CLONE" lesson.
   - In `ontology-demo-reproduction.md`, delete the backup notes and rename the revenue table there.
   - Add one line: "no backups kept; mess is one-way".

## Verification

- Query `INFORMATION_SCHEMA.TABLES` / `SCHEMATA` for `%BACKUP%` and `CLEAN_BASELINE`. Expect 0 rows, apart from the built-in INFORMATION\_SCHEMA views.
- Run `SELECT COUNT(*) FROM GAME_SALES_GEN.SOURCE_GAME_MONTHLY_REVENUE`. Expect 587.
- Run `SHOW PROCEDURES IN GAME_SALES_GEN`, then `GET_DDL` on the 3 procs. Neither should mention BACKUP.
- Grep the repo, skill and memory for `backup|CLEAN_BASELINE|restore_clean`. Expect no hits.

## Critical Files

- `sql/game_sales_gen/stored_procedures/SP_GEN_REVENUE_TARGETS.sql` - reads the revenue table
- `sql/game_sales_gen/stored_procedures/SP_GEN_CATALOG.sql` - reads the revenue table and sets the 'BACKUP' label
- `sql/mess/` - scripts to delete
- `ontology_setup/messy_data_design.md` - restore documentation
- `/memories/projects/.../MEMORY.md` - backup notes to remove
