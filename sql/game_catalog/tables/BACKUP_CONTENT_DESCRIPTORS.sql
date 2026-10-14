-- Backup of the dropped CONTENT_DESCRIPTORS lookup (15 rows), cloned 2026-10-09 before content descriptors
-- were removed from the data model. Age ratings now come only from GAME_RATINGS / AGE_RATINGS.
create or replace TABLE ONTOLOGY_DEMO.GAME_CATALOG.BACKUP_CONTENT_DESCRIPTORS (
	DESCRIPTOR_ID NUMBER(38,0),
	DESCRIPTOR_NAME VARCHAR(16777216),
	DESCRIPTOR_CATEGORY VARCHAR(16777216)
)COMMENT='The table contains categorizations of game content. Each record represents a specific descriptor and includes details about its category.'
;
