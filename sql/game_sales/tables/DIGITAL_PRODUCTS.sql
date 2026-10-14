create or replace TABLE ONTOLOGY_DEMO.GAME_SALES.DIGITAL_PRODUCTS (
	DIGITAL_PRODUCT_ID NUMBER(38,0) NOT NULL autoincrement start 1 increment 1 noorder,
	GAME_ID NUMBER(38,0),
	CATEGORY_ID NUMBER(38,0) NOT NULL,
	PRODUCT_NAME VARCHAR(16777216) NOT NULL,
	LIST_PRICE FLOAT,
	CURRENCY_CODE VARCHAR(3) DEFAULT 'USD',
	IS_CONSUMABLE BOOLEAN DEFAULT FALSE,
	RELEASE_DATE DATE,
	primary key (DIGITAL_PRODUCT_ID),
	foreign key (CATEGORY_ID) references ONTOLOGY_DEMO.GAME_SALES.REVENUE_CATEGORIES(CATEGORY_ID),
	foreign key (GAME_ID) references ONTOLOGY_DEMO.GAME_SALES.GAMES(GAME_ID)
)COMMENT='Unified SKU catalog for every digital good: base games, DLC, expansions, season and battle passes, cosmetics, consumables, loot boxes, and virtual currency bundles. GAME_ID is null for platform-wide items.'
;
