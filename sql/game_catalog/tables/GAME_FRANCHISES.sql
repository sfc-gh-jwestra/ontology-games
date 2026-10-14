create or replace TABLE ONTOLOGY_DEMO.GAME_CATALOG.GAME_FRANCHISES (
	GAME_ID NUMBER(38,0),
	FRANCHISE_ID NUMBER(38,0),
	SEQUENCE_ORDER NUMBER(38,0)
)COMMENT='The table contains records of game franchises. Each record represents a single franchise and includes details about its sequence order and relationship to a specific game.'
;
