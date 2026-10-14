CREATE OR REPLACE TABLE ONTOLOGY_DEMO.GAME_CATALOG.GAME_CONTEXTS (
	GAME_CONTEXT_ID NUMBER(38,0) NOT NULL AUTOINCREMENT START 1 INCREMENT 1 NOORDER,
	GAME_ID NUMBER(38,0),
	CONTEXT_ID NUMBER(38,0),
	PRIMARY KEY (GAME_CONTEXT_ID)
) COMMENT = 'The table contains records of game contexts, specifically settings or scenarios within games. Each record represents a unique context and includes details about the associated game.';
