CREATE OR REPLACE TABLE ONTOLOGY_DEMO.GAME_CATALOG.CONTEXTS (
	CONTEXT_ID NUMBER(38,0) NOT NULL AUTOINCREMENT START 1 INCREMENT 1 NOORDER,
	CONTEXT_NAME VARCHAR(16777216),
	PRIMARY KEY (CONTEXT_ID)
) COMMENT = 'The table contains records of gaming contexts. Each record represents a single context and includes details about its name.';
