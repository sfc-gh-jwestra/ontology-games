# Generating data

The project doesn't generate data. `bash install.sh` loads `ONTOLOGY_DEMO.GAME_CATALOG` and `ONTOLOGY_DEMO.GAME_SALES` from the Parquet files in `data/`. Read this page only if the data has to change: new games, a later as-of date, more volume. It describes what a generator must produce for the **current schemas** and how to produce it.

The two schemas are deliberately two inconsistent systems: a game catalog and a sales system. The inconsistencies are the point of the demo; the ontology resolves them. A generator must produce them as-is, not a clean version.

## Workflow

1. Write the generator as SQL scripts or stored procedures that write the tables below directly. Make it deterministic (see [Randomness](#randomness)).
2. Run it into `ONTOLOGY_DEMO`, then refresh the dynamic tables: `GAME_SIMILARITY_SCORES`, `GENRE_WHITESPACE_ANALYSIS`, `GAME_REVENUE` and `QUARTERLY_REVENUE`.
3. Re-derive genre membership with `CALL ONTOLOGY_DEMO.GAME_CATALOG.SP_CLASSIFY_GAMES()`. It rebuilds `GAME_GENRE_CLASSIFICATION` from `GENRE_RULES` and the game features.
4. Check every invariant at the end of this page.
5. Export each base table to Parquet, one folder per schema, and replace `data/`:
   ```sql
   COPY INTO @ONTOLOGY_DEMO.PUBLIC.DATA_STAGE/export/GAME_SALES/TITLES_
     FROM ONTOLOGY_DEMO.GAME_SALES.TITLES
     FILE_FORMAT = (TYPE = PARQUET) HEADER = TRUE;
   -- then: GET @ONTOLOGY_DEMO.PUBLIC.DATA_STAGE/export/ file://data/ (and move files into data/<SCHEMA>/)
   ```
   The install matches files by the name pattern `<TABLE>_<n>_<n>_<n>.snappy.parquet`. If you change a table's columns, update `sql/<SCHEMA>/tables/<TABLE>.sql` too.
6. Re-run the reference SQL in [ontology_eval_set.md](ontology_eval_set.md), update the expected answers, and update the `FORBIDDEN` list in `scripts/build_ontology.py`.

## GAME_CATALOG (master game data)

Catalog data is researched per game (title, studio, release date, features), not simulated.

| Table | Grain and key columns | Notes |
|---|---|---|
| GAMES | one row per game: GAME_ID, GAME_NAME, RELEASE_DATE (DATE), POV ('1P'/'3P'), NARRATIVE_STRUCTURE_ID, DEVELOPER_ID, DEVELOPER_NAME, DEVELOPER_IS_INDIE, PUBLISHER_ID, PUBLISHER_NAME, PUBLISHER_HQ, FRANCHISE_NAME, STATUS | **Overloaded:** developer, publisher and franchise have no tables of their own; they live as columns here. DEVELOPER_NAME uses underscores (`Santa_Monica_Studio`). STATUS is RELEASED / REMASTERED / DELISTED. |
| GAME_FRANCHISES | one row per game in a franchise: GAME_ID, FRANCHISE_ID, FRANCHISE_NAME, SEQUENCE_ORDER, FIRST_RELEASE_YEAR, PUBLISHER_ID, RELATED_GAME_ID, RELATIONSHIP_TYPE | Sequel links are RELATED_GAME_ID plus RELATIONSHIP_TYPE (original, sequel, prequel, spinoff, remake, spiritual_successor) and may cross franchises. |
| PLATFORMS, GAME_PLATFORMS | GAME_PLATFORMS: GAME_PLATFORM_ID, GAME_ID, PLATFORM_ID, IS_EXCLUSIVE (**BOOLEAN**), EXCLUSIVITY_TYPE (PERMANENT / TIMED / TIMED_EXPIRED), EXCLUSIVE_START, EXCLUSIVE_END | Catalog PLATFORM_NAME style: PS5, PS4, Pc_gaming, XBOX_ONE. |
| Feature tables | GAMEPLAY_TYPES / GAME_GAMEPLAY, MECHANICS / GAME_MECHANICS, CONTEXTS / GAME_CONTEXTS, NARRATIVE_STRUCTURES, GAME_MODES, ENGINES / GAME_ENGINES, AGE_RATINGS / GAME_RATINGS, INPUT_DEVICES / GAME_INPUT_DEVICES, ACCESSIBILITY_FEATURES / GAME_ACCESSIBILITY, AWARDS / GAME_AWARDS, MONETIZATION_TYPES / GAME_MONETIZATION, STUDIO_ACQUISITIONS | These drive genre classification and similarity. Value names follow VideOWL (e.g. `free_shooting`, `mithical`). |
| GENRE_RULES, GENRE_CATEGORY_MAP, SIMILARITY_WEIGHTS | reference data | GENRE_RULES is single-parent (PARENT_GENRE). Keep it as is (decision D9: ActionRPG and Soulslike stay under Action). |
| GAME_GENRE_CLASSIFICATION | one row per game and rule | Derived by SP_CLASSIFY_GAMES. Never write it directly. |

## GAME_SALES (the store's own system)

### Reference tables

| Table | Columns | Rules |
|---|---|---|
| TITLES | TITLE_ID, TITLE_NAME, STUDIO, PUBLISHER_LABEL, CATALOG_GAME_ID, RELEASE_DATE (**TEXT YYYYMMDD**) | One row per game, **Sales' own key** 5001-5090 (≠ GAME_ID). TITLE_NAME uses the store's spelling: 8 differ from the catalog (GT7, Ghost of Yotei without the macron, Spider-Man 2, God of War Ragnarok, Demons Souls...). STUDIO uses spaces (`Santa Monica Studio`). PUBLISHER_LABEL = 'SIE'. CATALOG_GAME_ID is NULL for some titles. RELEASE_DATE may be the Japanese date. |
| TITLE_CODE_XREF | TITLE_CODE, TITLE_ID, PLATFORM_CODE, CATALOG_GAME_ID | The PlayStation Store crosswalk: one code per game per PlayStation platform. Prefixes: PPSA = PS5, CUSA = PS4, NPUA = PS3, PCSA = Vita, SLUS = PS2. PC and Switch releases have none. For some titles, CATALOG_GAME_ID here is the **only** link to the catalog. |
| PLATFORMS | PLATFORM_ID, PLATFORM_NAME, PLATFORM_CODE | Same PLATFORM_ID values as the catalog, but store names (PlayStation 5, PC (Steam)) and codes (PS5, PSV, PC, NSW). |
| GAME_PLATFORMS | GAME_PLATFORM_ID, TITLE_ID, PLATFORM_ID, EXCLUSIVITY_TYPE, EXCLUSIVE_START, EXCLUSIVE_END, EXCLUSIVITY_NOTE, IS_EXCLUSIVE (**TEXT 'Y'/'N'**) | Mirrors the catalog rows, keyed by TITLE_ID. |
| MONETIZATION_TYPES, GAME_MONETIZATION | MONETIZATION_ID, MONETIZATION_NAME; TITLE_ID, MONETIZATION_ID | Business-model tags, lower case (premium, free_to_play, microtransactions, battle_pass, loot_boxes, dlc, season_pass, subscription, ads). A tag carries no money. |
| REVENUE_TYPES | CATEGORY_ID, MONETIZATION_TYPE, CATEGORY_GROUP, DESCRIPTION | What was **sold**, upper case. 13 types: BASE_GAME_DIGITAL (3), BASE_GAME_PHYSICAL (4), DLC (5), EXPANSION, SEASON_PASS (7), BATTLE_PASS (8), COSMETIC_MICROTRANSACTION (9), CONSUMABLE_MICROTRANSACTION (10), LOOT_BOX (11), VIRTUAL_CURRENCY (12), HARDWARE_CONSOLE, HARDWARE_PERIPHERAL, SUBSCRIPTION. **BASE_GAME_PHYSICAL is in CATEGORY_GROUP 'DIGITAL'.** |
| DIGITAL_PRODUCTS | DIGITAL_PRODUCT_ID, TITLE_ID, CATEGORY_ID, PRODUCT_NAME, LIST_PRICE, CURRENCY_CODE, IS_CONSUMABLE, RELEASE_DATE, SKU_CODE, STATUS | Many products per game. SKU_CODE = `<newest-generation TITLE_CODE>-C<CATEGORY_ID, 2 digits><sequence within title and category, 2 digits>`, e.g. `PPSA97384-C0301`. NULL when the game has no PlayStation code. STATUS = LIVE / DELISTED. |
| HARDWARE_PRODUCTS | HARDWARE_PRODUCT_ID, PRODUCT_NAME, PRODUCT_TYPE (CONSOLE / CONTROLLER / VR_HEADSET), PLATFORM_ID, MANUFACTURER, LIST_PRICE, RELEASE_DATE | 20 rows: PS2 to PS5 Pro, DualShock 2 to DualSense Edge, PS VR, PS VR2. MANUFACTURER = 'Sony Interactive Entertainment'. |
| SUBSCRIPTION_PLANS | PLAN_ID, PLAN_NAME, PLAN_TIER, GAME_ID, BILLING_CYCLE, LIST_PRICE, CURRENCY_CODE | 4 annual PlayStation Plus plans: 1 LEGACY, 2 ESSENTIAL, 3 EXTRA, 4 PREMIUM. GAME_ID NULL. |

### Customers and facts

**The same customer key has a different name in every table.**

| Table | Customer key | Other rules |
|---|---|---|
| CUSTOMER_ACCOUNTS | CUSTOMER_ID | PLATFORM_ID = first console; ACCOUNT_CREATED_DATE = first purchase. REGION uses **SIE codes**: SIEA (North America), SIEE, SIEJ, SIEAP, SIELA. STATUS is A (active), S (suspended) or C (closed). |
| HARDWARE_SALES_TRANSACTIONS | BUYER_ID | One row per item: QUANTITY = 1, UNIT_PRICE = GROSS_REVENUE = list price. REGION uses **sales codes**: NA, EU, JP, ASIA, LATAM, matching the buyer's SIE region. |
| DIGITAL_PRODUCT_TRANSACTIONS | PLAYER_ID | One row per purchase. GROSS_REVENUE; PLATFORM_COMMISSION_PCT = 0 on PlayStation, 0.30 elsewhere; NET_DEVELOPER_REVENUE = gross × (1 − pct), which is actually the **publisher's** share. TITLE_ID is **NULL on every 10th row**, but the game is still recoverable through DIGITAL_PRODUCT_ID → DIGITAL_PRODUCTS.TITLE_ID. |
| SUBSCRIPTION_CHARGES | SUBSCRIBER_ID | One annual charge per subscribed year: CHARGE_TIMESTAMP, BILLING_PERIOD_START, BILLING_PERIOD_END (start + 1 year − 1 day), GROSS_REVENUE. |

## Simulating the sales facts

This is the approach the current data was built with. Reuse it so new data has the same shape and realism.

### Scale and configuration

- **As-of date:** 2026-10-08. Nothing is dated after it.
- **Scale divisor:** 1000. Every real-world figure (game revenue, console units, subscriber counts) is divided by 1000.
- **Seed:** 42.

### Randomness

Never use `RANDOM()`. Use a hash of the seed and a key:

```sql
CAST(MOD(ABS(HASH(42, <key>)), 1000000007) AS FLOAT) / 1000000007.0   -- uniform in [0, 1)
```

The key is a short prefix plus IDs, e.g. `'rg' || CUSTOMER_ID` for region. Each decision gets its own prefix, so changing one decision doesn't reshuffle the rest.

### Real-world inputs

| Input | Content |
|---|---|
| Console units shipped per year | PS2 2000-2013 (160M lifetime), PS3 2006-2016 (87.4M), Vita 2011-2018 (15.9M), PS4 2013-2023 (117.2M), PS5 2020-2026 (95.3M) |
| PlayStation Plus subscribers per year | 0.5M (2010) rising to 47M (2021), 46M in 2022, 47M from 2023 to 2026 |
| Monthly revenue per game | where known; otherwise an estimated lifetime revenue per game |
| Launch prices | 49.99 before 2006-11-11, 59.99 before 2020-11-12, then 69.99; per-game overrides allowed |

### 1. Customers and hardware

- **Console units:** spread each year's units (÷ 1000) over its months. Weights by month: Jan .06, Feb .055, Mar .06, Apr .055, May .055, Jun .065, Jul .06, Aug .065, Sep .075, Oct .08, Nov .17, Dec .20. Never before the console's launch.
- **Upgrades:** a new-generation console goes to an existing previous-generation owner with 60% probability, if they have owned that console for at least 365 days. Otherwise it creates a new customer. Chain: PS2 → PS3 → Vita / PS4 → PS5.
- **Region per customer:** SIEA 40%, SIEE 35%, SIEJ 10%, SIEAP 10%, SIELA 5%. Hardware rows use the matching sales code.
- **Console model by date:** for example, PS5 Standard or Digital Edition (70 / 30%) until the Slim, then the Slim or Pro.
- **Extra controllers:** 0, 1 or 2 per console (60 / 30 / 10%), bought within a year of the console.
- **VR:** PS VR goes to about 5,000 PS4 owners, PS VR2 to about 2,000 PS5 owners.
- **Account status:**
  - Active ('A') if the customer made any hardware purchase, digital purchase or subscription charge in the 24 months before the as-of date.
  - Otherwise S or C. A small share of S keeps suspended accounts realistic.

### 2. Digital products per game

Pick a profile from the game's business-model tags, first match wins:

1. loot_boxes → sports packs
2. battle_pass → live battle pass
3. microtransactions → MTX
4. dlc + season_pass → DLC and season pass
5. dlc → DLC
6. otherwise → premium

Products by profile:

| Product | Applies to | Price |
|---|---|---|
| Digital Edition (cat 3) | every game | launch price |
| Physical Edition (cat 4) | priced games on PlayStation | launch price |
| DLC Packs 1-4 | DLC profiles | 14.99 / 19.99 / 14.99 / 29.99, released at +3 / +6 / +12 / +18 months |
| Season Pass | DLC and season pass | 29.99 |
| Cosmetic Bundles 1-12 | MTX and live | 4.99-19.99 |
| Small / Large Boost | MTX, consumable | 1.99 / 4.99 |
| Season N Battle Pass | live, every 3 months | 9.99 |
| Card Packs | sports, consumable | 4.99 / 9.99 |
| Stubs bundles | sports, consumable | 9.99 / 19.99 / 49.99 |

Then assign SKU_CODE as described above.

### 3. Revenue targets

- **Monthly revenue per game:** known monthly figures ÷ 1000. Otherwise the estimated total ÷ 1000, spread over a lifecycle curve:
  - The curve is a launch spike, then decay. Live games get seasonal bumps every 3 months; DLC games get bumps at the DLC months.
  - Horizon: 36 months for premium games, 48 for DLC, 72 for live service.
  - Noise ±10%; November and December × 1.3.
- **Split by category,** using weights per profile and lifecycle stage (launch, ongoing, seasonal, DLC bump, tail).
  - The base game splits into digital and physical by year. Digital share: .05 (≤2012), .25 (≤2016), .45 (≤2019), .65 (≤2022), .75 (2023+).
- **Price:** base-game price drops to 75% after 12 months and 50% after 24.
- **Units:** target ÷ price. Months too small for one unit carry into the next month.

### 4. Digital purchases

- **Products and dates:** one row per unit.
  - Pick a product released by then.
  - 40% of launch-month sales fall in the first week.
  - Base games pick a platform by weight: PS5 .55, PS4 .45, older PlayStation 1.0, PC .20, Xbox .12. PS5 is damped while its installed base is small.
- **Prices:** scale unit prices so each game, month and category hits its target to the cent.
- **Buyers:**
  - Pick from customers who own an eligible console by that date, best of 3 draws, weighted by engagement `1 + 9 * U^3`.
  - A base game is bought once per customer.
  - Add-ons only by owners of the base game, once per product.
  - Consumables may repeat.
- **PC and other non-PlayStation stores:** get their own customer rows, numbered after the PlayStation customers. Regions: SIEA 45%, SIEE 35%, SIEAP 10%, SIEJ 5%, SIELA 5%.
- **TITLE_ID:** NULL on every 10th transaction.

### 5. Subscriptions

- **Who subscribes:** each year's target is subscribers ÷ 1000. Up to 80% of the previous year's subscribers renew; the rest are new PS3/PS4/PS5 owners. Churned subscribers never return.
- **Charges:** one per year, on the anniversary of the first charge.
- **Plans and prices:**

  | When | Plan | Price |
  |---|---|---|
  | Before 2022-06-13 | 1 (Legacy) | 49.99; 59.99 from 2017-09-05 |
  | From 2022-06-13 | 2 / 3 / 4, fixed per customer at 60 / 25 / 15% | 59.99 / 99.99 / 119.99 |
  | From 2023-09-06 | 2 / 3 / 4 | 79.99 / 134.99 / 159.99 |

## Invariants to check before exporting

The ontology, semantic view, agents and eval set depend on these.

- **Design rules:** keep the four rules in [README_ontology_games_challenges.md](README_ontology_games_challenges.md#design-rules): a different kind of complexity per system, nothing hidden behind views, analytic objects reading the complex columns as-is, and every row recoverable.

- **Titles and crosswalk:**
  - Every catalog game has exactly one TITLES row.
  - TITLE_IDs are contiguous from 5001.
  - Some titles have NULL CATALOG_GAME_ID, and each of them resolves through TITLE_CODE_XREF or through name + release year.
  - The Sales names that differ from the catalog are the ones listed on the Game ontology term.
- **Customer keys:** CUSTOMER_ID, PLAYER_ID, BUYER_ID and SUBSCRIBER_ID all reference CUSTOMER_ACCOUNTS.CUSTOMER_ID.
- **Region codes:** SIE codes on customers only, sales codes on hardware only.
- **Flags:** IS_EXCLUSIVE is 'Y'/'N' text in Sales and BOOLEAN in the catalog.
- **Status codes:** Account STATUS is A/S/C; game STATUS is RELEASED/REMASTERED/DELISTED; product STATUS is LIVE/DELISTED.
- **Digital transactions:** TITLE_ID is NULL on every 10th row. Every DIGITAL_PRODUCT_ID exists in DIGITAL_PRODUCTS.
- **SKUs:** SKU_CODE prefixes exist in TITLE_CODE_XREF.
- **Revenue types:** BASE_GAME_PHYSICAL stays in CATEGORY_GROUP 'DIGITAL'.
- **Genres:** GENRE_RULES stays single-parent, and GAME_GENRE_CLASSIFICATION is rebuilt with SP_CLASSIFY_GAMES.
- **Determinism:** re-running the generator gives identical data.
