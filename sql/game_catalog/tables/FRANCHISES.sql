create or replace TABLE ONTOLOGY_DEMO.GAME_CATALOG.FRANCHISES (
	FRANCHISE_ID NUMBER(38,0),
	FRANCHISE_NAME VARCHAR(16777216),
	PUBLISHER_ID NUMBER(38,0),
	FIRST_RELEASE_YEAR NUMBER(38,0)
)COMMENT='The table contains records of video game franchises. Each record represents a single franchise and includes details about the franchise''s name, publisher, and release year.'
;
