create or replace TABLE ONTOLOGY_DEMO.GAME_SALES.GAME_MONETIZATION (
	TITLE_ID NUMBER(38,0) NOT NULL,
	MONETIZATION_ID NUMBER(38,0) NOT NULL,
	primary key (TITLE_ID, MONETIZATION_ID),
	foreign key (MONETIZATION_ID) references ONTOLOGY_DEMO.GAME_SALES.MONETIZATION_TYPES(MONETIZATION_ID)
)COMMENT='Sales system copy: monetization models each game uses. Loaded from data/GAME_SALES (no sync process).'
;
