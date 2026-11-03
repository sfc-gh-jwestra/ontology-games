-- 01-setup-db
-- Written by hand. Database, schemas, stage and file format for the Parquet load.
-- Run from the repo root: snow sql -c <connection> --enable-templating NONE -f install/01-setup-db.sql
USE ROLE ACCOUNTADMIN;

CREATE DATABASE IF NOT EXISTS ONTOLOGY_DEMO;
CREATE SCHEMA IF NOT EXISTS ONTOLOGY_DEMO.GAME_CATALOG;
CREATE SCHEMA IF NOT EXISTS ONTOLOGY_DEMO.GAME_SALES;
CREATE SCHEMA IF NOT EXISTS ONTOLOGY_DEMO.AGENTS
  COMMENT = 'Cortex Agents for the ontology demo (semantic views live with their data)';

-- Data comes from data/*.parquet; nothing is generated.
-- The old synthetic-sales generator workspace is retired.
DROP SCHEMA IF EXISTS ONTOLOGY_DEMO.GAME_SALES_GEN;

CREATE STAGE IF NOT EXISTS ONTOLOGY_DEMO.PUBLIC.DATA_STAGE;
CREATE FILE FORMAT IF NOT EXISTS ONTOLOGY_DEMO.PUBLIC.PARQUET_FF
  TYPE = PARQUET
  USE_VECTORIZED_SCANNER = TRUE
  USE_LOGICAL_TYPE = TRUE;
