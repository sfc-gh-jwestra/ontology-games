create or replace TABLE ONTOLOGY_DEMO.GAME_SALES.GAMES (
	GAME_ID NUMBER(38,0) NOT NULL,
	GAME_NAME VARCHAR(16777216),
	RELEASE_DATE DATE,
	primary key (GAME_ID)
)COMMENT='Sales system copy of the games it sells: ID, official title and release date only. Game descriptive data (developer, POV, narrative, franchise) lives in GAME_CATALOG. Kept in sync by the add-game-data-ontology skill.'
;
