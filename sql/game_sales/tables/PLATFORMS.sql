create or replace TABLE ONTOLOGY_DEMO.GAME_SALES.PLATFORMS (
	PLATFORM_ID NUMBER(38,0) NOT NULL,
	PLATFORM_NAME VARCHAR(16777216),
	PLATFORM_CODE VARCHAR(16777216),
	primary key (PLATFORM_ID)
)COMMENT='Sales system copy of platforms (consoles, PC, mobile) that hardware and digital sales are recorded against. Loaded from data/GAME_SALES (no sync process).'
;
