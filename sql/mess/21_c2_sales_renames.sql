-- 21_c2_sales_renames.sql
-- CHALLENGE 2: Same entity, different names across systems. GAME_SALES only; GAME_CATALOG keeps its names.
--   Game      : Catalog GAMES.GAME_NAME            vs Sales TITLES.TITLE_NAME (8 titles spelled differently)
--   Developer : Catalog GAMES.DEVELOPER_NAME       vs Sales TITLES.STUDIO ('Santa_Monica_Studio' vs 'Santa Monica Studio')
--   Publisher : Catalog GAMES.PUBLISHER_NAME       vs Sales TITLES.PUBLISHER_LABEL ('SIE')
--   Customer  : CUSTOMER_ACCOUNTS.CUSTOMER_ID, called PLAYER_ID / SUBSCRIBER_ID / BUYER_ID in the fact tables
--   Platform  : Catalog 'PS5', 'Pc_gaming'         vs Sales 'PlayStation 5', 'PC (Steam)'
-- Reads CLEAN_BASELINE.CAT_* (one-time copy of studio names); no Sales object reads GAME_CATALOG at runtime.
EXECUTE IMMEDIATE $$
BEGIN
    -- Game -> Title
    ALTER TABLE ONTOLOGY_DEMO.GAME_SALES.GAMES RENAME TO ONTOLOGY_DEMO.GAME_SALES.TITLES;
    ALTER TABLE ONTOLOGY_DEMO.GAME_SALES.TITLES RENAME COLUMN GAME_ID TO TITLE_ID;
    ALTER TABLE ONTOLOGY_DEMO.GAME_SALES.TITLES RENAME COLUMN GAME_NAME TO TITLE_NAME;
    ALTER TABLE ONTOLOGY_DEMO.GAME_SALES.TITLES ADD COLUMN
        STUDIO VARCHAR COMMENT 'Development studio',
        PUBLISHER_LABEL VARCHAR COMMENT 'Publishing label';

    UPDATE ONTOLOGY_DEMO.GAME_SALES.TITLES t
    SET STUDIO = REPLACE(d.DEVELOPER_NAME, '_', ' '),
        PUBLISHER_LABEL = 'SIE'
    FROM ONTOLOGY_DEMO.CLEAN_BASELINE.CAT_GAMES g
    JOIN ONTOLOGY_DEMO.CLEAN_BASELINE.CAT_DEVELOPERS d ON d.DEVELOPER_ID = g.DEVELOPER_ID
    WHERE t.TITLE_ID = g.GAME_ID;

    -- Store-facing title names that differ from the catalog
    UPDATE ONTOLOGY_DEMO.GAME_SALES.TITLES t
    SET TITLE_NAME = v.NEW_NAME
    FROM (SELECT column1 AS GAME_ID, column2 AS NEW_NAME FROM VALUES
            (315, 'God of War Ragnarok'),
            (631, 'Ghost of Yotei'),
            (627, 'DEATH STRANDING 2'),
            (403, 'GT7'),
            (406, 'Spider-Man 2'),
            (640, 'Ratchet and Clank Rift Apart'),
            (636, 'The Last of Us Part 1'),
            (655, 'Demons Souls')) v
    WHERE t.TITLE_ID = v.GAME_ID;

    -- Same customer, four names
    ALTER TABLE ONTOLOGY_DEMO.GAME_SALES.CUSTOMER_ACCOUNTS RENAME COLUMN ACCOUNT_ID TO CUSTOMER_ID;
    ALTER TABLE ONTOLOGY_DEMO.GAME_SALES.DIGITAL_PRODUCT_TRANSACTIONS RENAME COLUMN ACCOUNT_ID TO PLAYER_ID;
    ALTER TABLE ONTOLOGY_DEMO.GAME_SALES.SUBSCRIPTION_CHARGES RENAME COLUMN ACCOUNT_ID TO SUBSCRIBER_ID;
    ALTER TABLE ONTOLOGY_DEMO.GAME_SALES.HARDWARE_SALES_TRANSACTIONS RENAME COLUMN ACCOUNT_ID TO BUYER_ID;

    -- Store-style platform names
    UPDATE ONTOLOGY_DEMO.GAME_SALES.PLATFORMS p
    SET PLATFORM_NAME = v.NEW_NAME
    FROM (SELECT column1 AS PLATFORM_ID, column2 AS NEW_NAME FROM VALUES
            (1, 'Android'), (2, 'Nintendo DS'), (3, 'Xbox One'), (4, 'Apple iOS'),
            (5, 'PlayStation 3'), (6, 'PC (Steam)'), (7, 'Xbox 360'), (8, 'PlayStation 4'),
            (101, 'PlayStation 5'), (102, 'Xbox Series X|S'), (103, 'Nintendo Switch'), (104, 'Google Stadia'),
            (201, 'Nintendo 3DS'), (202, 'PlayStation Vita'), (203, 'NES'), (204, 'Super NES'),
            (205, 'Nintendo 64'), (206, 'GameCube'), (207, 'Wii'), (208, 'PlayStation 2')) v
    WHERE p.PLATFORM_ID = v.PLATFORM_ID;

    RETURN 'C2 applied';
END;
$$;
