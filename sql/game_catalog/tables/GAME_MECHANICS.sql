CREATE OR REPLACE TABLE ONTOLOGY_DEMO.GAME_CATALOG.GAME_MECHANICS (
	GAME_MECHANIC_ID NUMBER(38,0) NOT NULL AUTOINCREMENT START 1 INCREMENT 1 NOORDER,
	GAME_ID NUMBER(38,0),
	MECHANIC_ID NUMBER(38,0),
	PRIMARY KEY (GAME_MECHANIC_ID)
) COMMENT = 'The table contains records of game mechanics. Each record represents a single game mechanic and includes details about the game and the mechanic itself.';
