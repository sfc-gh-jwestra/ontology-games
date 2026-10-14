-- 99_restore_clean.sql
-- Returns GAME_CATALOG and GAME_SALES to the clean shape (tables + clean dependents).
-- Use before CALL GAME_SALES_GEN.SP_GENERATE_SALES(), which only understands the clean shape.
-- Run from the repo root:  snow sql -c <connection> -f sql/mess/99_restore_clean.sql
-- After regenerating: run 00_snapshot_clean_baseline.sql, then RUN_ALL.sql.
!source sql/mess/10_restore_from_baseline.sql
!source sql/game_catalog/views/VW_CANNIBALIZATION_CANDIDATES.sql
!source sql/game_catalog/stored_procedures/SP_FIND_CANNIBALIZATION.sql
!source sql/game_sales/views/MONTHLY_REVENUE.sql
!source sql/game_sales/dynamic_tables/GAME_REVENUE.sql
!source sql/game_sales/dynamic_tables/QUARTERLY_REVENUE.sql
!source sql/game_sales/views/VW_PLATFORM_EXCLUSIVITY.sql
