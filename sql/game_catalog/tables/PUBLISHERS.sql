create or replace TABLE ONTOLOGY_DEMO.GAME_CATALOG.PUBLISHERS (
	PUBLISHER_ID NUMBER(38,0),
	PUBLISHER_NAME VARCHAR(16777216),
	HEADQUARTERS VARCHAR(16777216),
	FOUNDED_YEAR NUMBER(38,0)
)COMMENT='The table contains records of game publishers. Each record represents a single publisher and includes details about their headquarters and founding year.'
;
