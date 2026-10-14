CREATE OR REPLACE TABLE ONTOLOGY_DEMO.GAME_CATALOG.GAME_GAMEPLAY (
	GAME_GAMEPLAY_ID NUMBER(38,0) NOT NULL AUTOINCREMENT START 1 INCREMENT 1 NOORDER,
	GAME_ID NUMBER(38,0),
	GAMEPLAY_TYPE_ID NUMBER(38,0),
	PRIMARY KEY (GAME_GAMEPLAY_ID)
) COMMENT = 'The table contains records of gameplay types for games. Each record represents a single gameplay type and includes details about the game it belongs to.';
