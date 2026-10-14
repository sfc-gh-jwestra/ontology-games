create or replace TABLE ONTOLOGY_DEMO.GAME_SALES_GEN.GEN_PRICE_OVERRIDES (
	GAME_ID NUMBER(38,0) NOT NULL,
	LAUNCH_PRICE NUMBER(10,2) NOT NULL,
	primary key (GAME_ID)
)COMMENT='Approximate US launch MSRP for games that differ from the era default ($49.99 pre-PS3, $59.99 until PS5 launch, $69.99 after).'
;
