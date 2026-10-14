CREATE OR REPLACE TABLE ONTOLOGY_DEMO.GAME_CATALOG.GAMEPLAY_TYPES (
	GAMEPLAY_TYPE_ID NUMBER(38,0) NOT NULL AUTOINCREMENT START 1 INCREMENT 1 NOORDER,
	GAMEPLAY_TYPE_NAME VARCHAR(16777216),
	PRIMARY KEY (GAMEPLAY_TYPE_ID)
) COMMENT = 'The table contains records of gameplay types. Each record represents a specific type of gameplay and includes a unique identifier and a descriptive name.';
