create or replace TABLE ONTOLOGY_DEMO.GAME_SALES.MONETIZATION_TYPES (
	MONETIZATION_ID NUMBER(38,0) NOT NULL,
	MONETIZATION_NAME VARCHAR(16777216) NOT NULL,
	unique (MONETIZATION_NAME),
	primary key (MONETIZATION_ID)
)COMMENT='Sales system copy of monetization model names (premium, dlc, microtransactions, ...) used to pick each game''s synthetic sales profile. Loaded from data/GAME_SALES (no sync process).'
;
