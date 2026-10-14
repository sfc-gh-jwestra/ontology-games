create or replace TABLE ONTOLOGY_DEMO.GAME_CATALOG.DEVELOPERS (
	DEVELOPER_ID NUMBER(38,0) NOT NULL autoincrement start 1 increment 1 noorder,
	DEVELOPER_NAME VARCHAR(16777216),
	IS_INDIE BOOLEAN,
	primary key (DEVELOPER_ID)
)COMMENT='The table contains records of game developers. Each record represents a single developer and includes details about their status as an independent developer.'
;
