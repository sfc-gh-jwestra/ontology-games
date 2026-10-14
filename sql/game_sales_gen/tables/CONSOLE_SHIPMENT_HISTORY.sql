create or replace TABLE ONTOLOGY_DEMO.GAME_SALES_GEN.CONSOLE_SHIPMENT_HISTORY (
	GENERATION VARCHAR(16777216) NOT NULL,
	PLATFORM_ID NUMBER(38,0) NOT NULL,
	SALES_YEAR NUMBER(4,0) NOT NULL,
	UNITS_ACTUAL NUMBER(38,0) NOT NULL,
	primary key (GENERATION, SALES_YEAR)
)COMMENT='Approximate actual (real-world) console sell-in per calendar year, split so each generation sums to Sony published lifetime totals: PS2 160M, PS3 87.4M, PS Vita 15.9M, PS4 117.2M, PS5 95.3M (through Sep 2026). Generator divides by REVENUE_SCALE_DIVISOR.'
;
