-- Workspace for the synthetic sales generator. Nothing in GAME_SALES references this schema;
-- the generator (CALL ONTOLOGY_DEMO.GAME_SALES_GEN.SP_GENERATE_SALES()) reads its inputs here and writes
-- the business tables in GAME_SALES.
--   Code:        SP_GENERATE_SALES, SP_GEN_CATALOG, SP_GEN_CUSTOMERS_AND_HARDWARE, SP_GEN_REVENUE_TARGETS,
--                SP_GEN_DIGITAL_SALES, SP_GEN_SUBSCRIPTIONS, UDF_U01 (stored_procedures/, functions/)
--   Seeds:       SALES_GEN_CONFIG, CONSOLE_SHIPMENT_HISTORY, PS_PLUS_SUBSCRIBER_HISTORY, GEN_CATEGORY_WEIGHTS,
--                GEN_PRICE_OVERRIDES, GEN_PLATFORM_DATE_OVERRIDES (tables/, seeds/GENERATOR_SEED_DATA.sql)
--   Inputs:      BACKUP_GAME_MNTHLY_REVENUE (protected source revenue), ADD_GAME_TMP (add-game skill staging)
--   Outputs:     GAME_REVENUE_TARGETS
--   Scratch:     transient GEN_* tables rebuilt on every run
CREATE SCHEMA IF NOT EXISTS ONTOLOGY_DEMO.GAME_SALES_GEN;
ALTER SCHEMA ONTOLOGY_DEMO.GAME_SALES_GEN SET COMMENT = 'Synthetic sales generator workspace (not business data). Code: SP_GENERATE_SALES + SP_GEN_* steps, UDF_U01. Seeds/config: SALES_GEN_CONFIG, CONSOLE_SHIPMENT_HISTORY, PS_PLUS_SUBSCRIBER_HISTORY, GEN_CATEGORY_WEIGHTS, GEN_PRICE_OVERRIDES, GEN_PLATFORM_DATE_OVERRIDES (actual real-world figures). Inputs: BACKUP_GAME_MNTHLY_REVENUE (protected), ADD_GAME_TMP (add-game skill staging). Output: GAME_REVENUE_TARGETS. All other tables are transient scratch rebuilt on every run. Writes GAME_SALES; GAME_SALES never references this schema.';
