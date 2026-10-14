create or replace TABLE ONTOLOGY_DEMO.GAME_CATALOG.GAMES (
	GAME_ID NUMBER(38,0) NOT NULL autoincrement start 1 increment 1 noorder,
	GAME_NAME VARCHAR(16777216),
	DEVELOPER_ID NUMBER(38,0),
	POV VARCHAR(16777216),
	RELEASE_DATE DATE,
	NARRATIVE_STRUCTURE_ID NUMBER(38,0),
	primary key (GAME_ID)
)COMMENT='The table contains records of video games, specifically games that have been developed and released. Each record represents a single game and includes details about the game''s narrative, gameplay perspective, and financial performance.'
;
