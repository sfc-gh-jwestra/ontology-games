create or replace TABLE ONTOLOGY_DEMO.GAME_SALES_GEN.PS_PLUS_SUBSCRIBER_HISTORY (
	SUB_YEAR NUMBER(4,0) NOT NULL,
	SUBSCRIBERS_ACTUAL NUMBER(38,0) NOT NULL,
	primary key (SUB_YEAR)
)COMMENT='Approximate actual (real-world) PS Plus paying subscribers per year (launched June 2010; ~47M in 2021-2026). With annual billing, one charge per subscriber per year. Generator divides by REVENUE_SCALE_DIVISOR.'
;
