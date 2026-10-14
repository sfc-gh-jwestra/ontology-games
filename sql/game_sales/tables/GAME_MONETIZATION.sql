create or replace TABLE ONTOLOGY_DEMO.GAME_SALES.GAME_MONETIZATION (
	GAME_ID NUMBER(38,0) NOT NULL,
	MONETIZATION_ID NUMBER(38,0) NOT NULL,
	primary key (GAME_ID, MONETIZATION_ID),
	foreign key (GAME_ID) references ONTOLOGY_DEMO.GAME_SALES.GAMES(GAME_ID),
	foreign key (MONETIZATION_ID) references ONTOLOGY_DEMO.GAME_SALES.MONETIZATION_TYPES(MONETIZATION_ID)
)COMMENT='Sales system copy: monetization models each game uses. Drives the synthetic sales profile (SP_GEN_CATALOG). Kept in sync by the add-game-data-ontology skill.'
;
