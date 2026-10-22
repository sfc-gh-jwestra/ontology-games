-- Cross-domain composable semantic views: checks.
-- Run after `python3 cross-domain/deploy.py`. Read-only. Each section returns one result set.
-- Currency is rounded to cents before comparing (FLOAT sums).

-- ============================================================================
-- 1. STRICT PARITY: SV_GAMING_CROSS_DOMAIN must return exactly what GAMING_BASELINE_SV returns.
--    Expect DIFF_ROWS = 0 for every check.
-- ============================================================================
WITH
b1 AS (SELECT ROUND(total_gross_revenue, 2) v FROM SEMANTIC_VIEW(ONTOLOGY_DEMO.ONTOLOGY_AGENTS.GAMING_BASELINE_SV METRICS digital_transactions.total_gross_revenue)),
c1 AS (SELECT ROUND(total_gross_revenue, 2) v FROM SEMANTIC_VIEW(ONTOLOGY_DEMO.CROSS_DOMAIN.SV_GAMING_CROSS_DOMAIN METRICS digital_transactions.total_gross_revenue)),
b2 AS (SELECT rollup_genre, rollup_game_count FROM SEMANTIC_VIEW(ONTOLOGY_DEMO.ONTOLOGY_AGENTS.GAMING_BASELINE_SV DIMENSIONS genre_rollup.rollup_genre METRICS genre_rollup.rollup_game_count)),
c2 AS (SELECT rollup_genre, rollup_game_count FROM SEMANTIC_VIEW(ONTOLOGY_DEMO.CROSS_DOMAIN.SV_GAMING_CROSS_DOMAIN DIMENSIONS genre_rollup.rollup_genre METRICS genre_rollup.rollup_game_count)),
b3 AS (SELECT developer_name, ROUND(total_gross_revenue, 2) v FROM SEMANTIC_VIEW(ONTOLOGY_DEMO.ONTOLOGY_AGENTS.GAMING_BASELINE_SV DIMENSIONS games.developer_name METRICS digital_transactions.total_gross_revenue)),
c3 AS (SELECT developer_name, ROUND(total_gross_revenue, 2) v FROM SEMANTIC_VIEW(ONTOLOGY_DEMO.CROSS_DOMAIN.SV_GAMING_CROSS_DOMAIN DIMENSIONS games.developer_name METRICS digital_transactions.total_gross_revenue)),
b4 AS (SELECT region, ROUND(hardware_gross_revenue, 2) v FROM SEMANTIC_VIEW(ONTOLOGY_DEMO.ONTOLOGY_AGENTS.GAMING_BASELINE_SV DIMENSIONS hardware_sales.region METRICS hardware_sales.hardware_gross_revenue)),
c4 AS (SELECT region, ROUND(hardware_gross_revenue, 2) v FROM SEMANTIC_VIEW(ONTOLOGY_DEMO.CROSS_DOMAIN.SV_GAMING_CROSS_DOMAIN DIMENSIONS hardware_sales.region METRICS hardware_sales.hardware_gross_revenue)),
b5 AS (SELECT region, status, customer_count FROM SEMANTIC_VIEW(ONTOLOGY_DEMO.ONTOLOGY_AGENTS.GAMING_BASELINE_SV DIMENSIONS customers.region, customers.status METRICS customers.customer_count)),
c5 AS (SELECT region, status, customer_count FROM SEMANTIC_VIEW(ONTOLOGY_DEMO.CROSS_DOMAIN.SV_GAMING_CROSS_DOMAIN DIMENSIONS customers.region, customers.status METRICS customers.customer_count))
SELECT 'digital gross revenue' AS check_name, (SELECT COUNT(*) FROM b1) baseline_rows, (SELECT COUNT(*) FROM c1) composed_rows,
       (SELECT COUNT(*) FROM (SELECT * FROM b1 EXCEPT SELECT * FROM c1)) + (SELECT COUNT(*) FROM (SELECT * FROM c1 EXCEPT SELECT * FROM b1)) diff_rows
UNION ALL SELECT 'game count by rollup genre (genre imports catalog)', (SELECT COUNT(*) FROM b2), (SELECT COUNT(*) FROM c2),
       (SELECT COUNT(*) FROM (SELECT * FROM b2 EXCEPT SELECT * FROM c2)) + (SELECT COUNT(*) FROM (SELECT * FROM c2 EXCEPT SELECT * FROM b2))
UNION ALL SELECT 'gross revenue by developer (cross-domain TITLE_GAME)', (SELECT COUNT(*) FROM b3), (SELECT COUNT(*) FROM c3),
       (SELECT COUNT(*) FROM (SELECT * FROM b3 EXCEPT SELECT * FROM c3)) + (SELECT COUNT(*) FROM (SELECT * FROM c3 EXCEPT SELECT * FROM b3))
UNION ALL SELECT 'hardware revenue by region', (SELECT COUNT(*) FROM b4), (SELECT COUNT(*) FROM c4),
       (SELECT COUNT(*) FROM (SELECT * FROM b4 EXCEPT SELECT * FROM c4)) + (SELECT COUNT(*) FROM (SELECT * FROM c4 EXCEPT SELECT * FROM b4))
UNION ALL SELECT 'customers by region and status', (SELECT COUNT(*) FROM b5), (SELECT COUNT(*) FROM c5),
       (SELECT COUNT(*) FROM (SELECT * FROM b5 EXCEPT SELECT * FROM c5)) + (SELECT COUNT(*) FROM (SELECT * FROM c5 EXCEPT SELECT * FROM b5));

-- ============================================================================
-- 2. RESOLVED vs EXPECTED: SV_GAMING_CROSS_DOMAIN_RESOLVED should hit the governed answers in
--    ontology_setup/ontology_eval_set.md. STRICT_VALUE shows what the strong-key join returns.
-- ============================================================================
WITH
r_game AS (SELECT game_id, game_name, developer_name, total_gross_revenue v FROM SEMANTIC_VIEW(ONTOLOGY_DEMO.CROSS_DOMAIN.SV_GAMING_CROSS_DOMAIN_RESOLVED
           DIMENSIONS games.game_id, games.game_name, games.developer_name METRICS digital_transactions.total_gross_revenue) WHERE game_id IS NOT NULL),
s_game AS (SELECT game_id, game_name, developer_name, total_gross_revenue v FROM SEMANTIC_VIEW(ONTOLOGY_DEMO.CROSS_DOMAIN.SV_GAMING_CROSS_DOMAIN
           DIMENSIONS games.game_id, games.game_name, games.developer_name METRICS digital_transactions.total_gross_revenue) WHERE game_id IS NOT NULL),
r_route AS (SELECT match_route, mapped_title_count FROM SEMANTIC_VIEW(ONTOLOGY_DEMO.CROSS_DOMAIN.SV_GAMING_CROSS_DOMAIN_RESOLVED
           DIMENSIONS title_game_map.match_route METRICS title_game_map.mapped_title_count)),
rpg AS (SELECT DISTINCT game_id FROM SEMANTIC_VIEW(ONTOLOGY_DEMO.CROSS_DOMAIN.SV_GAMING_CROSS_DOMAIN_RESOLVED
           DIMENSIONS games.game_id, genre_rollup.rollup_genre) WHERE rollup_genre IN ('RPG', 'Roguelike', 'ActionRPG', 'Soulslike')),
top_r AS (SELECT developer_name, SUM(v) v FROM r_game GROUP BY 1 ORDER BY v DESC LIMIT 1),
top_s AS (SELECT developer_name, SUM(v) v FROM s_game GROUP BY 1 ORDER BY v DESC LIMIT 1)
SELECT 'titles mapped (strong/medium/weak)' AS check_name, '90 (75/13/2)' AS expected,
       (SELECT SUM(mapped_title_count) || ' (' || LISTAGG(mapped_title_count, '/') WITHIN GROUP (ORDER BY DECODE(match_route, 'STRONG', 1, 'MEDIUM', 2, 3)) || ')' FROM r_route) AS resolved_value,
       '75 (strong only)' AS strict_value
UNION ALL SELECT 'revenue across catalog games (Q4)', '19231852.01',
       TO_VARCHAR(ROUND((SELECT SUM(v) FROM r_game), 2)), TO_VARCHAR(ROUND((SELECT SUM(v) FROM s_game), 2))
UNION ALL SELECT 'top developer revenue (Q5)', 'Santa_Monica_Studio 3419553.73',
       (SELECT developer_name || ' ' || ROUND(v, 2) FROM top_r), (SELECT developer_name || ' ' || ROUND(v, 2) FROM top_s)
UNION ALL SELECT 'games with digital sales (Q18)', '87',
       TO_VARCHAR((SELECT COUNT(DISTINCT game_id) FROM r_game WHERE v > 0)), TO_VARCHAR((SELECT COUNT(DISTINCT game_id) FROM s_game WHERE v > 0))
UNION ALL SELECT 'Ghost of Yotei revenue (Q3)', '198000.00',
       TO_VARCHAR((SELECT ROUND(SUM(v), 2) FROM r_game WHERE COLLATE(game_name, 'en-ci-ai') = 'ghost of yotei')),
       COALESCE(TO_VARCHAR((SELECT ROUND(SUM(v), 2) FROM s_game WHERE COLLATE(game_name, 'en-ci-ai') = 'ghost of yotei')), 'not found')
UNION ALL SELECT 'RPG revenue, roll-up incl. ActionRPG/Soulslike (Q22)', '13436693.28',
       TO_VARCHAR((SELECT ROUND(SUM(v), 2) FROM r_game WHERE game_id IN (SELECT game_id FROM rpg))),
       TO_VARCHAR((SELECT ROUND(SUM(v), 2) FROM s_game WHERE game_id IN (SELECT game_id FROM rpg)));
