# Messy source systems: GAME_CATALOG and GAME_SALES

This explains how `ONTOLOGY_DEMO.GAME_CATALOG` and `ONTOLOGY_DEMO.GAME_SALES` were deliberately made messy. The goal is to show how a Business Ontology gets correct answers where a naive "table = class" approach fails.

The patterns follow [README_ontology_challenges.md](README_ontology_challenges.md), applied to gaming. Challenges 1-7 are covered (C4 and C5 are combined). Challenge 8 (wide vs long grain) is not covered.

**Design rules**
- **No two systems get the same kind of mess.** GAME_CATALOG gets *overloaded tables*. GAME_SALES gets *renamed entities, its own keys and its own codes*.
- **The mess isn't hidden.** No views, UDFs or procedures smooth it over. The only new object is `TITLE_CODE_XREF`, a store code list that real systems really have.
- **Existing analytic objects are only repointed.** Columns and tables are renamed; nothing is cleaned up.
- **Every row is still recoverable.** Every number and name in the clean data can still be reached (see Verification).

Applied 2026-10-13 with `sql/mess/RUN_ALL.sql`.

---

## Challenge 1: Overloaded tables (GAME_CATALOG)

| Table | Classes crammed into one row | Columns added |
|---|---|---|
| `GAMES` | **Game** + **Developer** + **Publisher** + **Franchise** | `DEVELOPER_NAME`, `DEVELOPER_IS_INDIE`, `PUBLISHER_ID`, `PUBLISHER_NAME`, `PUBLISHER_HQ`, `FRANCHISE_NAME` |
| `GAME_FRANCHISES` | **Franchise membership** + **Franchise** + **Sequel graph** | `FRANCHISE_NAME`, `FIRST_RELEASE_YEAR`, `PUBLISHER_ID`, `RELATED_GAME_ID`, `RELATIONSHIP_TYPE` |
| `STUDIO_ACQUISITIONS` | **Acquisition** + **Studio** | `STUDIO_NAME` |

`DEVELOPERS`, `PUBLISHERS`, `FRANCHISES` and `GAME_SEQUELS` were **dropped**.
- Developer, Publisher and Franchise now exist only as columns inside other rows.
- Franchise name is stored twice (in GAMES and in GAME_FRANCHISES).
- The 39 sequel links now live in `GAME_FRANCHISES.RELATED_GAME_ID` and `RELATIONSHIP_TYPE` (`original`, `sequel`, `prequel`, `spinoff`, `remake`, `spiritual_successor`). Two of them cross franchises: Saros → Returnal and The Inpatient → Until Dawn.

**Ontology resolution**
- Separate nodes for Game, Developer, Publisher and Franchise.
- Each class gets column-level representations on `GAMES` and `GAME_FRANCHISES`.
- Relationships: `DEVELOPED_BY`, `PUBLISHED_BY`, `PART_OF`, and a self-relationship on Game for `SEQUEL_OF` / `PREQUEL_OF` / `REMAKE_OF` / `SPINOFF_OF` / `SPIRITUAL_SUCCESSOR_OF`.

## Challenge 2: Same entity, different names (GAME_SALES renames; Catalog keeps its names)

| Ontology class | GAME_CATALOG | GAME_SALES |
|---|---|---|
| **Game** | `GAMES` / `GAME_NAME` | `TITLES` / `TITLE_NAME` |
| **Developer** | `GAMES.DEVELOPER_NAME` = `Santa_Monica_Studio` | `TITLES.STUDIO` = `Santa Monica Studio` |
| **Publisher** | `GAMES.PUBLISHER_NAME` = `Sony Interactive Entertainment` | `TITLES.PUBLISHER_LABEL` = `SIE`; `HARDWARE_PRODUCTS.MANUFACTURER` = full name |
| **Customer / Player** | `GAME_MODES.MIN_PLAYERS/MAX_PLAYERS` ("player" is a headcount) | `CUSTOMER_ACCOUNTS.CUSTOMER_ID`, called `PLAYER_ID` in `DIGITAL_PRODUCT_TRANSACTIONS`, `SUBSCRIBER_ID` in `SUBSCRIPTION_CHARGES`, `BUYER_ID` in `HARDWARE_SALES_TRANSACTIONS` |
| **Platform** | `PLATFORMS.PLATFORM_NAME` = `PS5`, `Pc_gaming`, `XBOX_ONE` | `PLATFORMS.PLATFORM_NAME` = `PlayStation 5`, `PC (Steam)`, `Xbox One` |

Store-facing title names that differ from the catalog (8):

| Catalog GAME_NAME | Sales TITLE_NAME |
|---|---|
| God of War Ragnarök | God of War Ragnarok |
| Ghost of Yōtei | Ghost of Yotei |
| Death Stranding 2: On the Beach | DEATH STRANDING 2 |
| Gran Turismo 7 | GT7 |
| Marvel's Spider-Man 2 | Spider-Man 2 |
| Ratchet & Clank: Rift Apart | Ratchet and Clank Rift Apart |
| The Last of Us Part I | The Last of Us Part 1 |
| Demon's Souls | Demons Souls |

**Ontology resolution**
- One node per class, with synonyms: Title = Game; Studio = Developer; Label = Publisher; Player / Subscriber / Buyer = Customer.
- Representations of each node in both domains.

## Challenge 3: Identity resolution with imperfect keys (Sales to Catalog)

Sales now has its **own key**, `TITLES.TITLE_ID` = 5001-5090, assigned in release order. It no longer equals the catalog `GAME_ID`.

| Link strength | Key | Degradation | Titles resolved |
|---|---|---|---|
| Strong | `TITLES.CATALOG_GAME_ID` | NULL for every 7th TITLE_ID, plus 631 and 639 (15 NULL) | 75 |
| Medium | `TITLE_CODE_XREF.CATALOG_GAME_ID` (Challenge 4/5) | no xref rows for 631 / 639 | 13 |
| Weak | Normalized title name + release year | Ghost of Yotei needs accent folding. Uncharted: Legacy of Thieves needs its text JP date parsed | 2 |

- `DIGITAL_PRODUCT_TRANSACTIONS.TITLE_ID` is **NULL for every 10th transaction** (53,444 rows). The title can be recovered only via `DIGITAL_PRODUCT_ID` → `DIGITAL_PRODUCTS.TITLE_ID`.
- `DIGITAL_PRODUCTS`, `GAME_PLATFORMS` and `GAME_MONETIZATION` all use the Sales `TITLE_ID`.

**Ontology resolution**
- An identifier hierarchy on Game: catalog GAME_ID, Sales TITLE_ID, store title code.
- A `SAME_AS` link between Sales Title and Catalog Game.
- A documented match rule that falls back to name + year.

## Challenge 4/5: Code crosswalk (Sales)

`GAME_SALES.TITLE_CODE_XREF` (`TITLE_CODE`, `TITLE_ID`, `PLATFORM_CODE`, `CATALOG_GAME_ID`) is the PlayStation Store code list, comparable to the NDC ↔ RxNorm crosswalk in the healthcare example.
- 100 rows, one per title per PlayStation platform: `PPSA#####` for PS5, `CUSA#####` for PS4, `NPUA#####` for PS3, `PCSA#####` for Vita, `SLUS#####` for PS2.
- PC, Switch and other non-PlayStation releases have **no code**.
- `DIGITAL_PRODUCTS.SKU_CODE` = `<newest-gen title code>-C<category><seq>`, for example `PPSA01234-C0901`. 4 products have no SKU because their title has no PlayStation code.
- For 13 titles, `TITLE_CODE_XREF.CATALOG_GAME_ID` is the only route back to the catalog.

**Ontology resolution**
- Title Code is an identifier node, linked to Game and Platform.
- The SKU code is a typed property of the Product node.

## Challenge 6: Divergent code and value conventions

| Concept | GAME_CATALOG | GAME_SALES |
|---|---|---|
| Region | — | `CUSTOMER_ACCOUNTS.REGION` uses SIE codes `SIEA`, `SIEE`, `SIEJ`, `SIEAP`, `SIELA`. `HARDWARE_SALES_TRANSACTIONS.REGION` keeps `NA`, `EU`, `JP`, `ASIA`, `LATAM`, so there are **two conventions inside Sales** |
| Platform | `PLATFORM_NAME` = `PS5` | `PLATFORM_NAME` = `PlayStation 5`, plus a new `PLATFORM_CODE` = `PS5`, `PS4`, `PSV`, `PC`, `NSW`, ... |
| Exclusive flag | `GAME_PLATFORMS.IS_EXCLUSIVE` BOOLEAN | `GAME_PLATFORMS.IS_EXCLUSIVE` VARCHAR `'Y'` / `'N'` |
| Release date | `GAMES.RELEASE_DATE` DATE (worldwide) | `TITLES.RELEASE_DATE` VARCHAR `'YYYYMMDD'`. For 3 titles it is the **JP date**, one day earlier: Miles Morales, Uncharted: Legacy of Thieves, Returnal |
| Monetization vocabulary | `MONETIZATION_TYPES.MONETIZATION_NAME` lowercase (`battle_pass`) | `REVENUE_TYPES.MONETIZATION_TYPE` uppercase (`BATTLE_PASS`) |

**Ontology resolution**
- Region and Platform become code-list nodes, with the values from both systems mapped to one canonical value.
- Typed attributes for flags and dates.
- A property note that the Sales release date is regional.

## Challenge 7: Overloaded column names

| Name | Meaning in place A | Meaning in place B | Meaning in place C |
|---|---|---|---|
| `STATUS` | Catalog `GAMES.STATUS`: game lifecycle (`RELEASED` 79, `REMASTERED` 10, `DELISTED` 1 = Concord) | Sales `CUSTOMER_ACCOUNTS.STATUS`: account `A` / `S` / `C` (replaces `IS_ACTIVE`) | Sales `DIGITAL_PRODUCTS.STATUS`: store listing `LIVE` / `DELISTED` |
| `MONETIZATION_TYPE` | `MONETIZATION_TYPES` (both systems): the **business model** tagged on a game, with nothing priced | Sales `REVENUE_TYPES.MONETIZATION_TYPE` (was `REVENUE_CATEGORIES.CATEGORY_NAME`): **what was actually sold**, attached to priced products and transactions | — |
| `CATEGORY` | Catalog `GENRE_CATEGORY_MAP.CATEGORY_NAME`: a genre feature group | Catalog `ACCESSIBILITY_FEATURES.FEATURE_CATEGORY` | Sales `REVENUE_TYPES.CATEGORY_GROUP`: DIGITAL / HARDWARE / SUBSCRIPTION |
| `*DEVELOPER*` | Catalog `GAMES.DEVELOPER_NAME`: the studio | Sales `DIGITAL_PRODUCT_TRANSACTIONS.NET_DEVELOPER_REVENUE`: really the **publisher's** share after the store cut | Catalog `ENGINES.DEVELOPER_COMPANY`: the engine vendor |

**Ontology resolution**
- Each column is represented on a typed property of the correct class: Game Lifecycle Status, Account Status, Listing Status.
- Monetization Model and Revenue Type become separate nodes, linked by `REALIZED_AS`.
- Net Publisher Revenue is a metric defined as gross minus platform commission.

---

## Scripts (`sql/mess/`)

| Script | Purpose |
|---|---|
| `00_snapshot_clean_baseline.sql` | Zero-copy clones the 18 clean tables, plus a revenue answer key, into schema `CLEAN_BASELINE`. Refuses to run if the live data is already messy |
| `10_restore_from_baseline.sql` | Restores the 17 affected tables and drops `TITLES`, `TITLE_CODE_XREF` and `REVENUE_TYPES` |
| `20_c1_overloaded_catalog.sql` … `25_c7_overloaded_names.sql` | One script per challenge. Deterministic (MOD / rank, no RANDOM) |
| `30_repoint_dependents.sql` | Messy versions of `VW_CANNIBALIZATION_CANDIDATES`, `SP_FIND_CANNIBALIZATION`, `MONTHLY_REVENUE`, `GAME_REVENUE`, `QUARTERLY_REVENUE` and `VW_PLATFORM_EXCLUSIVITY`. The revenue objects are now keyed by Sales `TITLE_ID` |
| `RUN_ALL.sql` | Runs 10 → 20-25 → 30. Re-runnable: re-running gives identical hashes |
| `90_verify_mess.sql` | Read-only checks (below) |
| `99_restore_clean.sql` | Runs 10, then redeploys the clean dependents from `sql/game_*` |

Run them from the repo root: `snow sql -c JWESTRA_AWS1 -f sql/mess/RUN_ALL.sql`.

**Regenerating sales data.** `GAME_SALES_GEN.SP_GENERATE_SALES` only understands the clean shape. To regenerate:
1. `99_restore_clean.sql`
2. `CALL ONTOLOGY_DEMO.GAME_SALES_GEN.SP_GENERATE_SALES()`
3. `00_snapshot_clean_baseline.sql`
4. `RUN_ALL.sql`

The clean DDL files under `sql/game_catalog` and `sql/game_sales` describe the **clean** shape. The live messy shape is the clean shape plus `sql/mess/20-30`.

## Verification (2026-10-13)

- **Mess present:**
  - The 4 catalog tables are dropped.
  - 8 title names differ from the catalog.
  - 15 titles have no catalog ID.
  - 53,444 transactions have no title.
  - 100 crosswalk rows.
  - 5 SIE region codes.
- **Nothing lost:**
  - Digital, hardware and subscription totals match the baseline. The digital total is $19,231,852.01.
  - Every developer, publisher and franchise name is still present.
  - All 39 sequel links are present.
- **Still answerable:** revenue per catalog game, resolved through the strong → medium → weak keys (75 / 13 / 2 titles), matches the clean answer for every game.
- **Dependents run:**
  - The 6 repointed objects return the same row counts as the clean versions.
  - `SP_FIND_CANNIBALIZATION(0.3)` returns 1,166 rows.
  - `SP_CLASSIFY_GAMES` gives 3,420 rows / 258 FULL.
- **Round trip:** 99 → RUN_ALL gives identical messy hashes, and 99 alone gives hashes identical to the clean baseline.

## TODO

- **Update the `add-game-data-ontology` skill to write the messy shape.** It currently inserts into the dropped `DEVELOPERS` / `PUBLISHERS` / `FRANCHISES` / `GAME_SEQUELS`, and into Sales `GAMES` keyed by the catalog `GAME_ID`. Until it is updated, run `99_restore_clean.sql` before adding games, then re-snapshot and run `RUN_ALL.sql`.
- Challenge 8 (wide vs long grain) is not implemented. A candidate is a wide per-title KPI table in Sales.
