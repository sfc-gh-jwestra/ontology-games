-- Cross-domain identity map: one row per Sales title -> Catalog game.
-- Implements the Business Ontology "Game Identity Match Rule" as rows, because a semantic
-- view relationship can only equi-join columns and cannot express the three-route fallback.
-- Owned by the cross-domain layer: neither SV_GAME_COMMERCE nor SV_GAME_CATALOG knows about it.
-- Used only by SV_GAMING_CROSS_DOMAIN_RESOLVED.
CREATE OR REPLACE VIEW ONTOLOGY_DEMO.CROSS_DOMAIN.VW_TITLE_GAME_MAP
  COMMENT = 'Sales TITLE_ID -> Catalog GAME_ID via strong key, TITLE_CODE_XREF, then name (case/accent-insensitive) + release year'
AS
SELECT t.TITLE_ID,
       COALESCE(t.CATALOG_GAME_ID, x.CATALOG_GAME_ID, w.GAME_ID) AS GAME_ID,
       CASE WHEN t.CATALOG_GAME_ID IS NOT NULL THEN 'STRONG'
            WHEN x.CATALOG_GAME_ID IS NOT NULL THEN 'MEDIUM'
            WHEN w.GAME_ID IS NOT NULL THEN 'WEAK' END AS MATCH_ROUTE
FROM ONTOLOGY_DEMO.GAME_SALES.TITLES t
LEFT JOIN (SELECT TITLE_ID, MIN(CATALOG_GAME_ID) AS CATALOG_GAME_ID
           FROM ONTOLOGY_DEMO.GAME_SALES.TITLE_CODE_XREF GROUP BY TITLE_ID) x
  ON x.TITLE_ID = t.TITLE_ID
LEFT JOIN ONTOLOGY_DEMO.GAME_CATALOG.GAMES w
  ON COLLATE(w.GAME_NAME, 'en-ci-ai') = COLLATE(t.TITLE_NAME, 'en-ci-ai')
 AND YEAR(w.RELEASE_DATE) = YEAR(TO_DATE(t.RELEASE_DATE, 'YYYYMMDD'));
