CREATE OR REPLACE TABLE ONTOLOGY_DEMO.GAME_SALES.REVENUE_CATEGORIES (
	CATEGORY_ID NUMBER(38,0) NOT NULL AUTOINCREMENT START 1 INCREMENT 1 NOORDER,
	CATEGORY_NAME VARCHAR(16777216) NOT NULL,
	CATEGORY_GROUP VARCHAR(16777216) NOT NULL,
	DESCRIPTION VARCHAR(16777216),
	UNIQUE (CATEGORY_NAME),
	PRIMARY KEY (CATEGORY_ID)
) COMMENT = 'Commerce taxonomy for every way the platform earns revenue. CATEGORY_GROUP rolls categories up to HARDWARE, DIGITAL, or SUBSCRIPTION.';

INSERT INTO ONTOLOGY_DEMO.GAME_SALES.REVENUE_CATEGORIES (CATEGORY_NAME, CATEGORY_GROUP, DESCRIPTION) VALUES
	('HARDWARE_CONSOLE', 'HARDWARE', 'Console unit sales'),
	('HARDWARE_PERIPHERAL', 'HARDWARE', 'Controllers, VR headsets, and other accessories'),
	('BASE_GAME_DIGITAL', 'DIGITAL', 'Full game purchased as a digital download'),
	('BASE_GAME_PHYSICAL', 'DIGITAL', 'Full game purchased on physical media'),
	('DLC', 'DIGITAL', 'Downloadable content adding maps, characters, or story'),
	('EXPANSION', 'DIGITAL', 'Large paid content expansion to a base game'),
	('SEASON_PASS', 'DIGITAL', 'Bundle of future DLC sold up front at a discount'),
	('BATTLE_PASS', 'DIGITAL', 'Seasonal paid pass with tiered, progression-unlocked rewards'),
	('COSMETIC_MICROTRANSACTION', 'DIGITAL', 'Skins, emotes, outfits, and other non-gameplay items'),
	('CONSUMABLE_MICROTRANSACTION', 'DIGITAL', 'Boosts, potions, extra lives, and other used-up items'),
	('LOOT_BOX', 'DIGITAL', 'Randomized paid item containers (gacha)'),
	('VIRTUAL_CURRENCY', 'DIGITAL', 'Premium in-game currency bundles purchased with real money'),
	('SUBSCRIPTION', 'SUBSCRIPTION', 'Recurring paid access, platform-wide or game-specific');
