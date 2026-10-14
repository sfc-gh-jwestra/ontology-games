create or replace TABLE ONTOLOGY_DEMO.GAME_SALES_GEN.SALES_GEN_CONFIG (
	CONFIG_KEY VARCHAR(16777216) NOT NULL,
	CONFIG_VALUE VARCHAR(16777216) NOT NULL,
	DESCRIPTION VARCHAR(16777216),
	primary key (CONFIG_KEY)
)COMMENT='Parameters for the synthetic sales generator. Source tables hold actual real-world figures; the generator divides by REVENUE_SCALE_DIVISOR.'
;
