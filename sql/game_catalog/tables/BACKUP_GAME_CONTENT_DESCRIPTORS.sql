-- Backup of the dropped GAME_CONTENT_DESCRIPTORS bridge (199 rows, 78 games), cloned 2026-10-09 before content
-- descriptors were removed from the data model. Age ratings now come only from GAME_RATINGS / AGE_RATINGS.
create or replace TABLE ONTOLOGY_DEMO.GAME_CATALOG.BACKUP_GAME_CONTENT_DESCRIPTORS (
	GAME_ID NUMBER(38,0),
	DESCRIPTOR_ID NUMBER(38,0)
)COMMENT='The table contains metadata about game content descriptors. Each record represents a single descriptor and includes details about the game and its associated attributes.'
;
