create or replace TABLE ONTOLOGY_DEMO.GAME_SALES.CUSTOMER_ACCOUNTS (
	ACCOUNT_ID NUMBER(38,0) NOT NULL autoincrement start 1 increment 1 noorder,
	PLATFORM_ID NUMBER(38,0),
	REGION VARCHAR(16777216),
	ACCOUNT_CREATED_DATE DATE,
	IS_ACTIVE BOOLEAN DEFAULT TRUE,
	primary key (ACCOUNT_ID),
	foreign key (PLATFORM_ID) references ONTOLOGY_DEMO.GAME_SALES.PLATFORMS(PLATFORM_ID)
)COMMENT='Platform network accounts (PSN-style) that buy hardware, buy digital products, and hold subscriptions. PLATFORM_ID is the account home network.'
;
