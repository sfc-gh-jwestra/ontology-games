-- RUN_ALL.sql
-- Applies the full mess from the clean baseline. Re-runnable (starts with a restore).
-- Run from the repo root:  snow sql -c <connection> -f sql/mess/RUN_ALL.sql
-- Prerequisite: 00_snapshot_clean_baseline.sql has been run on clean data.
!source sql/mess/10_restore_from_baseline.sql
!source sql/mess/20_c1_overloaded_catalog.sql
!source sql/mess/21_c2_sales_renames.sql
!source sql/mess/22_c3_sales_keys.sql
!source sql/mess/23_c45_title_code_xref.sql
!source sql/mess/24_c6_codes.sql
!source sql/mess/25_c7_overloaded_names.sql
!source sql/mess/30_repoint_dependents.sql
