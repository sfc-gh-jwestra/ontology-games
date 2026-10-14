create or replace TABLE ONTOLOGY_DEMO.GAME_CATALOG.MONETIZATION_TYPES (
	MONETIZATION_ID NUMBER(38,0) NOT NULL autoincrement start 1 increment 1 noorder,
	MONETIZATION_NAME VARCHAR(16777216) NOT NULL,
	DESCRIPTION VARCHAR(16777216),
	unique (MONETIZATION_NAME),
	primary key (MONETIZATION_ID)
)COMMENT='The table contains records of monetization types. Each record includes a unique identifier, a name, and a description of the type.'
;
