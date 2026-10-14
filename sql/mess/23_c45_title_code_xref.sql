-- 23_c45_title_code_xref.sql
-- CHALLENGE 4/5: Identity via a code crosswalk (the store's own code list, like NDC <-> RxNorm).
--   TITLE_CODE_XREF : one row per title x PlayStation platform, store-style codes
--                     PS5 PPSA#####, PS4 CUSA#####, PS3 NPUA#####, Vita PCSA#####, PS2 SLUS#####
--                     CATALOG_GAME_ID is the only route back to the catalog for titles whose
--                     TITLES.CATALOG_GAME_ID is NULL. No rows for 631 / 639 (weak-key cases, see 22_c3).
--   DIGITAL_PRODUCTS.SKU_CODE : <title code>-<category><seq>, e.g. PPSA01234-C0901
-- Must run after 22_c3 (uses the new TITLE_ID and the CLEAN_BASELINE game id).
EXECUTE IMMEDIATE $$
BEGIN
    CREATE OR REPLACE TABLE ONTOLOGY_DEMO.GAME_SALES.TITLE_CODE_XREF (
        TITLE_CODE VARCHAR NOT NULL PRIMARY KEY COMMENT 'PlayStation Store title code',
        TITLE_ID NUMBER(38,0) NOT NULL,
        PLATFORM_CODE VARCHAR NOT NULL,
        CATALOG_GAME_ID NUMBER(38,0)
    ) COMMENT = 'PlayStation Store title code list';

    INSERT INTO ONTOLOGY_DEMO.GAME_SALES.TITLE_CODE_XREF
    SELECT pfx.PREFIX || LPAD(TO_VARCHAR(MOD(t.TITLE_ID * 37 + gp.PLATFORM_ID * 101, 100000)), 5, '0'),
           t.TITLE_ID,
           pfx.PLATFORM_CODE,
           g.GAME_ID
    FROM ONTOLOGY_DEMO.GAME_SALES.TITLES t
    JOIN ONTOLOGY_DEMO.GAME_SALES.GAME_PLATFORMS gp ON gp.TITLE_ID = t.TITLE_ID
    JOIN (SELECT column1 AS PLATFORM_ID, column2 AS PREFIX, column3 AS PLATFORM_CODE FROM VALUES
            (101, 'PPSA', 'PS5'), (8, 'CUSA', 'PS4'), (5, 'NPUA', 'PS3'),
            (202, 'PCSA', 'PSV'), (208, 'SLUS', 'PS2')) pfx ON pfx.PLATFORM_ID = gp.PLATFORM_ID
    -- recover the catalog id from the clean snapshot by original release order
    JOIN (SELECT GAME_ID, 5000 + ROW_NUMBER() OVER (ORDER BY RELEASE_DATE, GAME_ID) AS TITLE_ID
          FROM ONTOLOGY_DEMO.CLEAN_BASELINE.SAL_GAMES) g ON g.TITLE_ID = t.TITLE_ID
    WHERE g.GAME_ID NOT IN (631, 639);

    -- SKU code on each product: newest-generation title code + category + sequence
    ALTER TABLE ONTOLOGY_DEMO.GAME_SALES.DIGITAL_PRODUCTS ADD COLUMN SKU_CODE VARCHAR;
    UPDATE ONTOLOGY_DEMO.GAME_SALES.DIGITAL_PRODUCTS dp
    SET SKU_CODE = s.SKU_CODE
    FROM (
        SELECT dp2.DIGITAL_PRODUCT_ID,
               c.TITLE_CODE || '-C' || LPAD(TO_VARCHAR(dp2.CATEGORY_ID), 2, '0')
                 || LPAD(TO_VARCHAR(ROW_NUMBER() OVER (PARTITION BY dp2.TITLE_ID, dp2.CATEGORY_ID
                                                       ORDER BY dp2.DIGITAL_PRODUCT_ID)), 2, '0') AS SKU_CODE
        FROM ONTOLOGY_DEMO.GAME_SALES.DIGITAL_PRODUCTS dp2
        JOIN (SELECT TITLE_ID, TITLE_CODE FROM ONTOLOGY_DEMO.GAME_SALES.TITLE_CODE_XREF
              QUALIFY ROW_NUMBER() OVER (PARTITION BY TITLE_ID
                  ORDER BY DECODE(PLATFORM_CODE, 'PS5', 1, 'PS4', 2, 'PS3', 3, 'PSV', 4, 5)) = 1) c
          ON c.TITLE_ID = dp2.TITLE_ID
    ) s
    WHERE dp.DIGITAL_PRODUCT_ID = s.DIGITAL_PRODUCT_ID;

    RETURN 'C4/5 applied';
END;
$$;
