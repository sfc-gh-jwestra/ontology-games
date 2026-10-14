CREATE OR REPLACE TABLE ONTOLOGY_DEMO.GAME_CATALOG.MECHANICS (
	MECHANIC_ID NUMBER(38,0) NOT NULL AUTOINCREMENT START 1 INCREMENT 1 NOORDER,
	MECHANIC_NAME VARCHAR(16777216),
	PRIMARY KEY (MECHANIC_ID)
) COMMENT = 'The table contains records of mechanics, specifically those involved in gaming. Each record represents a single mechanic and includes details about the mechanic''s name.';
