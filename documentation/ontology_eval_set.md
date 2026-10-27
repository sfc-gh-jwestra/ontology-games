# Evaluation set: with vs without Business Ontology

Thirteen questions for testing an agent on the complex `ONTOLOGY_DEMO` systems, **with** and **without** the Business Ontology defined in [business_ontology_phases.md](business_ontology_phases.md). Eleven questions show the ontology's uplift (the baseline gets them wrong). Two are controls that both agents should get right, to show the ontology doesn't break simple questions.

- **Vocabulary:** questions use **canonical business vocabulary only** (Game, Developer, Customer, North America...). They never use local names such as `TITLES`, `STUDIO`, `PLAYER_ID` or `SIEA`. Needing the local vocabulary is exactly what the ontology should remove (decision D1).
- **Answers:** every expected answer was computed against the current complex data using the reference SQL at the end (last verified 2026-10-26).
- **When answers change:** if the data changes, re-run the reference SQL and update this file.
- **Answers stay out of the ontology (D17):** this file is the only place expected values live. No ontology description may contain an expected answer, a trap value or an eval example. `scripts/build_ontology.py` holds these values in its `FORBIDDEN` list and fails the build on a leak, so update that list whenever answers here change. The list also keeps the values of retired questions; they're still trap or answer values.

## How to run

1. Build the ontology (Phases 1-7), then create the baseline semantic view and the two agents (Phase 8):
   - **Baseline agent:** semantic view only.
   - **BON agent:** semantic view + `snowscope_search` over `businessOntology`.
2. Ask each question **verbatim** to both agents, in a fresh thread per question. The local compare app (`bash app/dev.sh`) loads this file and runs both agents side by side.
3. Score each answer:
   - Counts: exact match.
   - Currency: within $0.01.
   - Lists: same members.
   - "Partial" is allowed for answers that are right but missing a required caveat.
4. Fill in the results template. The point of the demo is the difference between the two columns.

## Questions

| # | Question (ask verbatim) | Challenge | Expected answer | Naive trap → likely wrong answer | Ontology nodes that fix it |
|---|---|---|---|---|---|
| 1 | What is total revenue across all catalog games? | C3 + C4 crosswalk | **$19,231,852.01** | Joins on `CATALOG_GAME_ID` only → $15,861,443.42 | Game Revenue (route split); Title Code; Game Identity Match Rule |
| 2 | Which developer earned the most revenue, and how much? | C1 overloaded + C2 | **Santa_Monica_Studio, $3,419,553.73** | Developer has no table; Sales calls it Studio; strong key only → $2,919,819.89 | Developer (synonym Studio); Developer Revenue |
| 3 | What is our total developer revenue? | C6 misnamed column + C3 | **$19,231,852.01** (gross, all 41 studios) | Sums `NET_DEVELOPER_REVENUE`, which is the publisher's share after the store cut → $19,119,344.99 | Developer Revenue (Studio Revenue); Net Publisher Revenue (column is misnamed); Game Identity Match Rule |
| 4 | How much revenue did first-person shooters make? | C7 genre synonym + C3 identity | **$203,000.00** | "first-person shooter" is not a genre value; may sum all shooters or 0, plus the identity traps | FPS (synonym first-person shooter); Game Revenue |
| 5 | Which catalog games have no digital sales? | C3 imperfect keys + grain (D11) | **3 games: Astro's Playroom, Concord, My First Gran Turismo** | Follows only `TITLES.CATALOG_GAME_ID` → 18 games, including well-known sellers such as The Last of Us Part II and Ghost of Yōtei | Game Identity Match Rule; Title Code; Digital Sales (keep rows with no TITLE_ID) |
| 6 | How much revenue have games built on the Naughty Dog engine made? | C4 crosswalk + C3 | **$1,444,560.00** (5 games: The Last of Us Part II $600,000; The Last of Us Part I $378,000; Uncharted: The Lost Legacy $314,760; The Last of Us Part II Remastered $120,000; Uncharted: Legacy of Thieves Collection $31,800) | Engine exists only in the catalog; the two Part II titles reach the catalog only through `TITLE_CODE_XREF`, so joining on `TITLES.CATALOG_GAME_ID` alone → $624,348 (or $692,760 with untagged transactions) | Game Identity Match Rule (crosswalk route); Title Code; Engine; Game Revenue |
| 7 | Which genre has the most revenue? | C7 genre roll-up + C3 identity | **Action, $14,642,492.04** (66 games). Ranking: Action $14,642,492.04; RPG $13,436,693.28; Horror $6,080,639.52; MultiplayerAvailable $3,938,359.98; Adventure $3,892,173.76; Strategic $2,008,400.00; Simulator $49,000.00; Other $30,500.00 | (a) Groups by the classified genre only, so parents never appear → ActionRPG $13,436,693.28 (or $12,278,693.28 with the strong key only). (b) Uses the roll-up but only the strong title key → Action $13,217,013.28, and RPG missing | Genre Roll-up Rule; Genre Revenue; Game Identity Match Rule |
| 8 | How much revenue did RPG games make? | C7 genre roll-up (D9) + C3 identity | **$13,436,693.28** (43 games) | Strict tree: `ROLLUP_GENRE = 'RPG'` has no games → $0. Strong title key only → $12,278,693.28 | RPG term; Genre Roll-up Rule; Game Identity Match Rule |
| 9 | What is revenue for each Action subgenre? | C7 genre hierarchy | **ActionRPG $13,436,693.28; DynamicAdventure $12,662,253.28; Shooter $7,836,560.00; Stealth $5,271,160.00; Platformer $990,310.00; Survival $184,988.76; Fighting $65,000.00** (direct children of Action, each including its own subgenres) | Lists only directly classified rows, so Shooter excludes FPS/TPS-only games, or sums the subgenres and presents the overlap ($30.6M+) as Action's total | Genre Roll-up Rule; Genre Revenue (not additive) |
| 10 | What was console revenue in North America? | C5 codes + synonym | **$70,243,201.72** | "Console" is not a column or table name; uses the customer code `SIEA` on hardware sales (which use NA) → $0 | Hardware Revenue (synonym Console Revenue); Sales Region Code; SIE Region Code equivalent to Sales Region Code |
| 11 | How much revenue did the Ghost of Tsushima franchise make? | C2 + C3 weak key | **$978,000.00** (Ghost of Tsushima $780,000.00 + Ghost of Yōtei $198,000.00) | Franchise exists only in the catalog, and Ghost of Yōtei has no catalog ID, no store code and an accent-free Sales name ("Ghost of Yotei"), so the catalog-ID join drops it → $780,000.00 (or ~$700,775 if untagged transactions are also dropped) | Franchise Revenue; Game Identity Match Rule (weak route: name + year, accent-insensitive) |
| 12 | What is our total digital game revenue? | control (C3 imperfect keys) | **$19,231,852.01** | Drops transactions whose game key is missing → $17,312,180.80 | Digital Gross Revenue (do not filter `TITLE_ID`); Digital Transaction |
| 13 | How many active customers do we have? | control (C6 overloaded names) | **96,773** | Counts all accounts → 289,225 | Account Status; Active Customer Count |

**Expected behaviour without the ontology:** questions 1-11 should fail or return a plausible but wrong number. Question 6 cannot be answered at all. With the GENRE_ROLLUP table in the semantic view, the baseline agent can show parent genres for 7 and 9 but should still undercount revenue (strong key only) and get 0 for RPG (8). Questions 12 and 13 are controls: in React UI runs the baseline also got them right, so a correct baseline answer there is expected.

**Genre totals are not additive:** the eight top-level totals in Q7 add up to $30,641,565.30 (more than the $19,231,852.01 total) because each game counts in every genre it belongs to. `MultiplayerAvailable` and `Other` are top-level rows in `GENRE_RULES`, so they appear in the ranking.

**Q11 depends on the ontology search index:** the BON agent only passes once search returns the Game Identity Match Rule text that requires `COLLATE(..., 'en-ci-ai')`. With older text it writes `LOWER()` name matches and misses the accented name. Q11 asks about the franchise rather than the game itself: asked directly about Ghost of Yōtei, the baseline just filters Sales titles by name and passes. Franchise is a catalog-only attribute, so the catalog-to-Sales join can't be skipped. In 2026-10-27 runs the baseline missed it 8/8 ($780,000 ×4, ~$700,775 ×3, ~$878,987 ×1) and BON returned $978,000 in every run that printed a figure (6 of 8).

## Results template

| # | Baseline agent answer | Correct? | BON agent answer | Correct? | Notes (which node was used) |
|---|---|---|---|---|---|
| 1 | | | | | |
| 2 | | | | | |
| 3 | | | | | |
| 4 | | | | | |
| 5 | | | | | |
| 6 | | | | | |
| 7 | | | | | |
| 8 | | | | | |
| 9 | | | | | |
| 10 | | | | | |
| 11 | | | | | |
| 12 | | | | | |
| 13 | | | | | |
| **Total** | | **/13** | | **/13** | |

## Reference SQL (expected answers)

All queries are read-only. Most game-level answers use this resolution CTE, which implements the Game Identity Match Rule:

```sql
-- RESOLVED: Sales title -> catalog game (strong -> medium -> weak)
WITH xref AS (
    SELECT TITLE_ID, MIN(CATALOG_GAME_ID) AS CATALOG_GAME_ID
    FROM ONTOLOGY_DEMO.GAME_SALES.TITLE_CODE_XREF GROUP BY TITLE_ID
), title_to_game AS (
    SELECT t.TITLE_ID,
           COALESCE(t.CATALOG_GAME_ID, x.CATALOG_GAME_ID, w.GAME_ID) AS GAME_ID
    FROM ONTOLOGY_DEMO.GAME_SALES.TITLES t
    LEFT JOIN xref x ON x.TITLE_ID = t.TITLE_ID
    LEFT JOIN ONTOLOGY_DEMO.GAME_CATALOG.GAMES w
      ON COLLATE(w.GAME_NAME, 'en-ci-ai') = COLLATE(t.TITLE_NAME, 'en-ci-ai')
     AND YEAR(w.RELEASE_DATE) = YEAR(TO_DATE(t.RELEASE_DATE, 'YYYYMMDD'))
), game_revenue AS (
    SELECT tg.GAME_ID, SUM(d.GROSS_REVENUE) AS INCOME
    FROM ONTOLOGY_DEMO.GAME_SALES.DIGITAL_PRODUCT_TRANSACTIONS d
    JOIN ONTOLOGY_DEMO.GAME_SALES.DIGITAL_PRODUCTS p ON p.DIGITAL_PRODUCT_ID = d.DIGITAL_PRODUCT_ID
    JOIN title_to_game tg ON tg.TITLE_ID = COALESCE(d.TITLE_ID, p.TITLE_ID)
    GROUP BY tg.GAME_ID
)
SELECT ... ;
```

| # | Final SELECT (append to the CTE where it is used) |
|---|---|
| 1 | `SELECT SUM(INCOME) FROM game_revenue;` (naive: join `d.TITLE_ID = t.TITLE_ID` with `t.CATALOG_GAME_ID IS NOT NULL` → $15,861,443.42) |
| 2 | `SELECT g.DEVELOPER_NAME, SUM(r.INCOME) v FROM game_revenue r JOIN ONTOLOGY_DEMO.GAME_CATALOG.GAMES g USING (GAME_ID) GROUP BY 1 ORDER BY v DESC LIMIT 1;` |
| 3 | `SELECT SUM(r.INCOME) FROM game_revenue r JOIN ONTOLOGY_DEMO.GAME_CATALOG.GAMES g USING (GAME_ID);` (naive: `SUM(NET_DEVELOPER_REVENUE)` → $19,119,344.99) |
| 4 | `SELECT SUM(r.INCOME) FROM game_revenue r JOIN ONTOLOGY_DEMO.GAME_CATALOG.GAME_GENRE_CLASSIFICATION c ON c.GAME_ID = r.GAME_ID AND c.GENRE = 'FPS' AND c.MATCH_STATUS = 'FULL';` |
| 5 | `SELECT GAME_ID, GAME_NAME FROM ONTOLOGY_DEMO.GAME_CATALOG.GAMES WHERE GAME_ID NOT IN (SELECT GAME_ID FROM game_revenue);` (naive: keep only `TITLES.CATALOG_GAME_ID` matches → 18 games) |
| 6 | `SELECT SUM(r.INCOME) FROM game_revenue r JOIN ONTOLOGY_DEMO.GAME_CATALOG.GAME_ENGINES ge USING (GAME_ID) JOIN ONTOLOGY_DEMO.GAME_CATALOG.ENGINES e USING (ENGINE_ID) WHERE e.ENGINE_NAME = 'Naughty_Dog_Engine';` |
| 7 | `SELECT g.G, COUNT(DISTINCT g.GAME_ID), SUM(r.INCOME) v FROM (SELECT GAME_ID, ROLLUP_GENRE G FROM ONTOLOGY_DEMO.GAME_CATALOG.VW_GAME_GENRE_ROLLUP WHERE ROLLUP_DEPTH = 1 AND ROLLUP_GENRE <> 'RPG' UNION SELECT GAME_ID, 'RPG' FROM ONTOLOGY_DEMO.GAME_CATALOG.VW_GAME_GENRE_ROLLUP WHERE ROLLUP_GENRE IN ('RPG','Roguelike','ActionRPG','Soulslike')) g JOIN game_revenue r ON r.GAME_ID = g.GAME_ID GROUP BY 1 ORDER BY v DESC;` |
| 8 | `SELECT SUM(INCOME) FROM game_revenue WHERE GAME_ID IN (SELECT GAME_ID FROM ONTOLOGY_DEMO.GAME_CATALOG.VW_GAME_GENRE_ROLLUP WHERE ROLLUP_GENRE IN ('RPG','Roguelike','ActionRPG','Soulslike'));` |
| 9 | `SELECT u.ROLLUP_GENRE, SUM(r.INCOME) v FROM ONTOLOGY_DEMO.GAME_CATALOG.VW_GAME_GENRE_ROLLUP u JOIN ONTOLOGY_DEMO.GAME_CATALOG.VW_GENRE_HIERARCHY h ON h.GENRE = u.ROLLUP_GENRE JOIN game_revenue r ON r.GAME_ID = u.GAME_ID WHERE h.PARENT_GENRE = 'Action' GROUP BY 1 ORDER BY v DESC;` |
| 10 | `SELECT SUM(GROSS_REVENUE) FROM ONTOLOGY_DEMO.GAME_SALES.HARDWARE_SALES_TRANSACTIONS WHERE REGION = 'NA';` |
| 11 | `SELECT g.GAME_NAME, r.INCOME FROM game_revenue r JOIN ONTOLOGY_DEMO.GAME_CATALOG.GAMES g USING (GAME_ID) WHERE g.FRANCHISE_NAME = 'Ghost of Tsushima';` (sum the rows; naive: strong key only drops Ghost of Yōtei → $780,000.00) |
| 12 | `SELECT SUM(GROSS_REVENUE) FROM ONTOLOGY_DEMO.GAME_SALES.DIGITAL_PRODUCT_TRANSACTIONS;` |
| 13 | `SELECT COUNT(*) FROM ONTOLOGY_DEMO.GAME_SALES.CUSTOMER_ACCOUNTS WHERE STATUS = 'A';` |

Strong-key-only naive figures (Q7b, Q8) join `DIGITAL_PRODUCTS.TITLE_ID` to `TITLES` and keep only `TITLES.CATALOG_GAME_ID`, which is the only title-to-game join in `SV_GAMING_CROSS_DOMAIN`.

## Why these questions

The set was cut from 23 to 13 on 2026-10-26, based on React UI runs judged by an LLM against this answer key.

- **Kept for uplift (ontology right, baseline wrong):** catalog revenue, top developer, publisher net revenue, FPS revenue, games with digital sales, crosswalk lineage, and the three genre roll-up questions.
- **Merged:** catalog revenue, top developer and God of War franchise revenue all fail for the same reason (strong title key only). Catalog revenue and top developer stay; franchise revenue was dropped.
- **Reworded:** "hardware revenue in North America" became "console revenue". The baseline got the hardware wording right, but fails when it has to map console to hardware, which the ontology handles with the Console Revenue synonym.
- **Reworded to trap the baseline:** Ghost of Yōtei revenue became Ghost of Tsushima franchise revenue (2026-10-27). It still tests the hardest identity route (accented name + year only), but the baseline can no longer pass by filtering Sales titles by name.
- **Controls:** total digital revenue and active customers. Both agents got them right.
- **Dropped (both agents right, or duplicates):** Gran Turismo 7 revenue, God of War franchise revenue, active customers in North America, battle pass revenue, total platform revenue, RPG game count, FPS game count, exclusive game-platform pairs, active catalog games, and the SKU lookup.

| New # | Old # |
|---|---|
| 1 | 4 |
| 2 | 5 |
| 3 | 11 (replaced: was "publisher keeps after store commission", which the baseline passed) |
| 4 | 15 |
| 5 | 18 (replaced: was "How many games have digital sales?", which the baseline passed by counting titles) |
| 6 | 20 (replaced: was "Which business concepts break if the store title-code crosswalk is removed?", not a realistic business question) |
| 7 | 21 |
| 8 | 22 |
| 9 | 23 |
| 10 | 9 (reworded) |
| 11 | 3 |
| 12 | 1 |
| 13 | 7 |
