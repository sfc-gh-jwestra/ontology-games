create or replace TABLE ONTOLOGY_DEMO.GAME_CATALOG.GAME_SEQUELS (
	GAME_ID NUMBER(38,0),
	SEQUEL_OF_GAME_ID NUMBER(38,0),
	RELATIONSHIP_TYPE VARCHAR(16777216)
)COMMENT='The table contains relationships between games, specifically sequels. Each record represents a connection between a game and its sequel, including the type of relationship.'
;
