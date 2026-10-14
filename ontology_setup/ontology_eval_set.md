# Evaluation set: with vs without Business Ontology

Twenty questions for testing an agent on the messy `ONTOLOGY_DEMO` systems, **with** and **without** the Business Ontology defined in [business_ontology_phases.md](business_ontology_phases.md).

- **Vocabulary:** questions use **canonical business vocabulary only** (Game, Developer, Customer, North America...). They never use local names such as `TITLES`, `STUDIO`, `PLAYER_ID` or `SIEA`. Needing the local vocabulary is exactly what the ontology should remove (decision D1).
- **Answers:** every expected answer was computed on 2026-10-13 against the current messy data, using the reference SQL at the end.
- **When answers change:** if the data is regenerated (`sql/mess/RUN_ALL.sql` after `SP_GENERATE_SALES`), re-run the reference SQL and update this file.
- **Answers stay out of the ontology (D17):** this file is the only place expected values live. No ontology description may contain an expected answer, a trap value or an eval example. `build/build_ontology.py` holds these values in its `FORBIDDEN` list and fails the build on a leak, so update that list whenever answers here change.

## How to run

1. Build the ontology (Phases 1-7), then create the baseline semantic view and the two agents (Phase 8):
   - **Baseline agent:** semantic view only.
   - **BON agent:** semantic view + `snowscope_search` over `businessOntology`.
2. Ask each question **verbatim** to both agents, in a fresh thread per question.
3. Score each answer:
   - Counts: exact match.
   - Currency: within $0.01.
   - Lists: same members.
   - "Partial" is allowed for answers that are right but missing a required caveat.
4. Fill in the results template. The point of the demo is the difference between the two columns.

## Questions

| # | Question (ask verbatim) | Challenge | Expected answer | Naive trap → likely wrong answer | Ontology nodes that fix it |
|---|---|---|---|---|---|
| 1 | What is our total digital game revenue? | C3 imperfect keys | **$19,231,852.01** | Drops transactions whose game key is missing → $17,312,180.80 | Digital Gross Revenue (do not filter `TITLE_ID`); Digital Transaction |
| 2 | How much revenue did Gran Turismo 7 make? | C2 names | **$899,999.98** | Sales calls it "GT7" → not found / $0 | Game (synonym Title); Game Identity Match Rule |
| 3 | How much revenue did Ghost of Yōtei make? | C2 + C3 weak key | **$198,000.00** | No catalog ID, no store code, accent dropped in Sales ("Ghost of Yotei") → not found / $0 | Game Identity Match Rule (weak route: name + year) |
| 4 | What is total revenue across all catalog games? | C3 + C4/5 crosswalk | **$19,231,852.01** | Joins on `CATALOG_GAME_ID` only → $15,861,443.42 | Game Revenue (route split); Title Code; Game Identity Match Rule |
| 5 | Which developer earned the most revenue, and how much? | C1 overloaded + C2 | **Santa_Monica_Studio, $3,419,553.73** | Developer has no table; Sales calls it Studio; strong key only → $2,919,819.89 | Developer (synonym Studio); Developer Revenue |
| 6 | How much revenue did the God of War franchise make? | C1 overloaded | **$3,428,553.73** | Franchise has no table, its name lives inside game rows; strong key only undercounts | Franchise; Franchise Revenue |
| 7 | How many active customers do we have? | C7 overloaded names | **96,773** | Counts all accounts → 289,225 | Account Status; Active Customer Count |
| 8 | How many active customers are in North America? | C6 codes | **38,699** | Filters `REGION = 'NA'` (customers use SIEA) → 0 | SIE Region Code; Account Status |
| 9 | What was hardware revenue in North America? | C6 codes | **$70,243,201.72** | Uses the customer code `SIEA` on hardware sales (which use NA) → $0 | Sales Region Code; SIE Region Code equivalent to Sales Region Code |
| 10 | How much revenue came from battle passes? | C7 homonym | **$150,389.48** | Answers from the business-model tag ("2 games have a battle pass") | Revenue Type Code vs Monetization Model; Battle Pass Sales Revenue |
| 11 | How much digital revenue does the publisher keep after store commission? | C7 misnamed column | **$19,119,344.99** | Treats `NET_DEVELOPER_REVENUE` as the developer's share, or reports gross | Net Publisher Revenue |
| 12 | How much total revenue does the platform keep across hardware, digital and subscriptions? | metric definition | **$211,407,934.18** | Sums all gross → $230,527,279.17 | Total Platform Revenue; Platform Commission Revenue |
| 13 | How many RPG games are there? | genre roll-up (D8/D9) | **43** | The strict `GENRE_RULES` tree puts ActionRPG under Action → 0 | RPG term (ActionRPG and Soulslike also RPG); Genre Match Status |
| 14 | How many first-person shooters are there? | genre synonym | **10** | "first-person shooter" is not a genre value; may count all shooters (30) or 0 | FPS (synonym first-person shooter); Shooter has variant FPS |
| 15 | How much revenue did first-person shooters make? | genre + identity | **$203,000.00** | Same synonym miss, plus the identity traps | FPS; Game Revenue |
| 16 | How many game-platform pairs are currently exclusive? | C6 value conventions | **53** | `IS_EXCLUSIVE = TRUE` fails on 'Y'/'N' text → error or 0 | Exclusivity Flag; Currently Exclusive Game Count |
| 17 | How many active (not delisted) games are in the catalog? | C7 overloaded names | **89** | Ignores lifecycle status → 90, or uses the wrong STATUS column | Game Lifecycle Status; Active Catalog Game Count |
| 18 | How many games have digital sales? | grain (D11) | **87** games | Counts products/SKUs → 351 | Game grain warning; Digital Product |
| 19 | What game and product type is SKU CUSA86252-C1101? | C4/5 crosswalk (D11) | **MLB The Show 17, LOOT_BOX** (a PS4 store code; the game has no `CATALOG_GAME_ID` in Sales) | Cannot read the SKU format; strong key returns no game | SKU Code; Title Code; Game Identity Match Rule |
| 20 | Which business concepts break if the store title-code crosswalk is removed? | governance (D15) | **Game, Title Code, SKU Code, Game Revenue** | Cannot answer without representations | Phase 7 representations on `TITLE_CODE_XREF` |

**Expected behaviour without the ontology:** questions 2, 3, 5, 8, 9, 10, 13, 14, 15, 16 and 19 usually fail outright. Questions 1, 4, 6, 7, 11, 12, 17 and 18 usually return a plausible but wrong number. Question 20 cannot be answered.

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
| 14 | | | | | |
| 15 | | | | | |
| 16 | | | | | |
| 17 | | | | | |
| 18 | | | | | |
| 19 | | | | | |
| 20 | | | | | |
| **Total** | | **/20** | | **/20** | |

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
      ON LOWER(TRANSLATE(w.GAME_NAME, 'ōöéü', 'ooeu')) = LOWER(t.TITLE_NAME)
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
| 1 | `SELECT SUM(GROSS_REVENUE) FROM ONTOLOGY_DEMO.GAME_SALES.DIGITAL_PRODUCT_TRANSACTIONS;` |
| 2, 3 | `SELECT g.GAME_NAME, r.INCOME FROM game_revenue r JOIN ONTOLOGY_DEMO.GAME_CATALOG.GAMES g USING (GAME_ID) WHERE g.GAME_ID IN (403, 631);` |
| 4 | `SELECT SUM(INCOME) FROM game_revenue;` (naive: join `d.TITLE_ID = t.TITLE_ID` with `t.CATALOG_GAME_ID IS NOT NULL` → $15,861,443.42) |
| 5 | `SELECT g.DEVELOPER_NAME, SUM(r.INCOME) v FROM game_revenue r JOIN ONTOLOGY_DEMO.GAME_CATALOG.GAMES g USING (GAME_ID) GROUP BY 1 ORDER BY v DESC LIMIT 1;` |
| 6 | `SELECT SUM(r.INCOME) FROM game_revenue r JOIN ONTOLOGY_DEMO.GAME_CATALOG.GAMES g USING (GAME_ID) WHERE g.FRANCHISE_NAME = 'God of War';` |
| 7 | `SELECT COUNT(*) FROM ONTOLOGY_DEMO.GAME_SALES.CUSTOMER_ACCOUNTS WHERE STATUS = 'A';` |
| 8 | `SELECT COUNT(*) FROM ONTOLOGY_DEMO.GAME_SALES.CUSTOMER_ACCOUNTS WHERE STATUS = 'A' AND REGION = 'SIEA';` |
| 9 | `SELECT SUM(GROSS_REVENUE) FROM ONTOLOGY_DEMO.GAME_SALES.HARDWARE_SALES_TRANSACTIONS WHERE REGION = 'NA';` |
| 10 | `SELECT SUM(d.GROSS_REVENUE) FROM ONTOLOGY_DEMO.GAME_SALES.DIGITAL_PRODUCT_TRANSACTIONS d JOIN ONTOLOGY_DEMO.GAME_SALES.DIGITAL_PRODUCTS p USING (DIGITAL_PRODUCT_ID) JOIN ONTOLOGY_DEMO.GAME_SALES.REVENUE_TYPES r ON r.CATEGORY_ID = p.CATEGORY_ID WHERE r.MONETIZATION_TYPE = 'BATTLE_PASS';` |
| 11 | `SELECT SUM(NET_DEVELOPER_REVENUE) FROM ONTOLOGY_DEMO.GAME_SALES.DIGITAL_PRODUCT_TRANSACTIONS;` |
| 12 | `SELECT (SELECT SUM(GROSS_REVENUE) FROM ONTOLOGY_DEMO.GAME_SALES.HARDWARE_SALES_TRANSACTIONS) + (SELECT SUM(GROSS_REVENUE - NET_DEVELOPER_REVENUE) FROM ONTOLOGY_DEMO.GAME_SALES.DIGITAL_PRODUCT_TRANSACTIONS) + (SELECT SUM(GROSS_REVENUE) FROM ONTOLOGY_DEMO.GAME_SALES.SUBSCRIPTION_CHARGES);` |
| 13 | `SELECT COUNT(DISTINCT GAME_ID) FROM ONTOLOGY_DEMO.GAME_CATALOG.GAME_GENRE_CLASSIFICATION WHERE MATCH_STATUS = 'FULL' AND GENRE IN ('RPG','Roguelike','ActionRPG','Soulslike');` (naive strict tree: FULL members of RPG's descendants in `VW_GENRE_HIERARCHY` → 0) |
| 14 | `SELECT COUNT(DISTINCT GAME_ID) FROM ONTOLOGY_DEMO.GAME_CATALOG.GAME_GENRE_CLASSIFICATION WHERE MATCH_STATUS = 'FULL' AND GENRE = 'FPS';` |
| 15 | `SELECT SUM(r.INCOME) FROM game_revenue r JOIN ONTOLOGY_DEMO.GAME_CATALOG.GAME_GENRE_CLASSIFICATION c ON c.GAME_ID = r.GAME_ID AND c.GENRE = 'FPS' AND c.MATCH_STATUS = 'FULL';` |
| 16 | `SELECT COUNT(*) FROM ONTOLOGY_DEMO.GAME_SALES.GAME_PLATFORMS WHERE IS_EXCLUSIVE = 'Y' AND (EXCLUSIVITY_TYPE = 'PERMANENT' OR (EXCLUSIVITY_TYPE = 'TIMED' AND EXCLUSIVE_END >= CURRENT_DATE()));` |
| 17 | `SELECT COUNT(*) FROM ONTOLOGY_DEMO.GAME_CATALOG.GAMES WHERE STATUS <> 'DELISTED';` |
| 18 | `SELECT COUNT(DISTINCT GAME_ID) FROM game_revenue;` (naive: `SELECT COUNT(DISTINCT DIGITAL_PRODUCT_ID) FROM ONTOLOGY_DEMO.GAME_SALES.DIGITAL_PRODUCT_TRANSACTIONS` → 351) |
| 19 | `SELECT g.GAME_NAME, r.MONETIZATION_TYPE FROM ONTOLOGY_DEMO.GAME_SALES.DIGITAL_PRODUCTS p JOIN ONTOLOGY_DEMO.GAME_SALES.TITLE_CODE_XREF x ON p.SKU_CODE LIKE x.TITLE_CODE || '-%' JOIN ONTOLOGY_DEMO.GAME_CATALOG.GAMES g ON g.GAME_ID = x.CATALOG_GAME_ID JOIN ONTOLOGY_DEMO.GAME_SALES.REVENUE_TYPES r ON r.CATEGORY_ID = p.CATEGORY_ID WHERE p.SKU_CODE = 'CUSA86252-C1101';` |
| 20 | No SQL. Answered from the ontology's representations (`SYSTEM$GET_GLOSSARY_GRAPH()` or catalog lineage) |
