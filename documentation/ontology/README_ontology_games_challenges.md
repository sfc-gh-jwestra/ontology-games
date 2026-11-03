# The source data: two complex systems

`bash install.sh` (step 02) loads deliberately complex game-business data from the Parquet files in [`../data/`](../../data/) into two independent source schemas of `ONTOLOGY_DEMO`. The table definitions are in [`../sql/`](../../sql/). The Business Ontology is then built on top in step 04 (see [business_ontology_phases.md](business_ontology_phases.md)).

The data is **simulated**: real game titles, studios and console histories, with synthetic customers and sales. It is intentionally *not* clean:
- Tables are overloaded (one table holds many entity types).
- The same real-world entity is named differently in each system.
- Keys are imperfect, and code conventions diverge.

That complexity is the whole point. It's what a naive `table = class` mapping gets wrong, and what the ontology layer is built to resolve. The schemas, keys and cross-system joins are described in [how-database-is-designed.md](../how-database-is-designed.md).

## Design rules

- **Each system gets a different kind of complexity.** GAME_CATALOG has *overloaded tables*. GAME_SALES has *renamed entities, its own keys and its own codes*.
- **The complexity isn't hidden.** No views, UDFs or procedures smooth it over. The only crosswalk is `TITLE_CODE_XREF`, a store code list that real systems really have.
- **Analytic objects use the data as-is.** The views, dynamic tables and procedures read the irregular columns directly; nothing is cleaned up.
- **Every row stays recoverable.** Every number and name can be reached, the hard way. For example, revenue per catalog game resolves fully through the strong, crosswalk and name + year keys.

Any change to the data must keep these rules.

## The two source systems

| Schema | Represents | "Game" is called | "Studio" is called | "Customer" is called |
|---|---|---|---|---|
| `ONTOLOGY_DEMO.GAME_CATALOG` | Master game catalog: what a game *is* (features, platforms, ratings, genres) | `GAMES.GAME_NAME` (`GAME_ID`) | `GAMES.DEVELOPER_NAME` | n/a ("player" means a headcount in `GAME_MODES`) |
| `ONTOLOGY_DEMO.GAME_SALES` | PlayStation store, hardware and subscription system: how a game *earns money* | `TITLES.TITLE_NAME` (`TITLE_ID`) | `TITLES.STUDIO` | `CUSTOMER_ID` / `PLAYER_ID` / `BUYER_ID` / `SUBSCRIBER_ID` |

**Scale:**
- 90 games, each in both systems under two different keys.
- 289,225 customer accounts.
- About 534k digital purchases, 712k hardware sales and 477k subscription charges.
- 46 genre rules.

Each table's comment (in `sql/<SCHEMA>/tables/`) describes its local vocabulary. The systems share no views or code; the only cross-system links are the imperfect keys in Challenges 3 and 4.

---

## Challenge 1: Overloaded tables (one table, many ontology classes)

The biggest reason `table = class` fails. A single table spans several entity types, so the ontology has to *decompose* one row into several class instances.

| Table | Entity types crammed into one row |
|---|---|
| `GAME_CATALOG.GAMES` | **Game** + **Developer** (`DEVELOPER_ID`, `DEVELOPER_NAME`, `DEVELOPER_IS_INDIE`) + **Publisher** (`PUBLISHER_ID`, `PUBLISHER_NAME`, `PUBLISHER_HQ`) + **Franchise** (`FRANCHISE_NAME`) |
| `GAME_CATALOG.GAME_FRANCHISES` | **Franchise membership** + **Franchise** (`FRANCHISE_NAME`, `FIRST_RELEASE_YEAR`, `PUBLISHER_ID`) + **Sequel graph** (`RELATED_GAME_ID`, `RELATIONSHIP_TYPE`) |
| `GAME_CATALOG.STUDIO_ACQUISITIONS` | **Acquisition** + **Studio** (`STUDIO_NAME`) |

**Consequences:**
- There is no Developer, Publisher or Franchise table. These classes exist only as columns inside other rows.
- The franchise name is stored twice, in `GAMES` and in `GAME_FRANCHISES`.
- Sequel links can cross franchises: Saros → Returnal, and The Inpatient → Until Dawn.

**Ontology assists by:** defining **Developer**, **Publisher** and **Franchise** as their own canonical classes, with column-level representations on `GAMES`, `GAME_FRANCHISES` and `STUDIO_ACQUISITIONS`. The relationships are Franchise HAS_PART Game, Developer RELATED_TO Game, and Publisher RELATED_TO Franchise / Developer. "Revenue per developer" or "per franchise" then works even though neither has a table.

---

## Challenge 2: Same entity, different names across systems

The classic alignment problem. The ontology defines one canonical class, and synonyms collapse the local names.

| Ontology class | GAME_CATALOG | GAME_SALES |
|---|---|---|
| **Game** | `GAMES` / `GAME_NAME` | `TITLES` / `TITLE_NAME` |
| **Developer** | `GAMES.DEVELOPER_NAME` = `Santa_Monica_Studio`; `STUDIO_ACQUISITIONS.STUDIO_NAME` (a second catalog spelling source) | `TITLES.STUDIO` = `Santa Monica Studio` |
| **Publisher** | `GAMES.PUBLISHER_NAME` = `Sony Interactive Entertainment` | `TITLES.PUBLISHER_LABEL` = `SIE`; `HARDWARE_PRODUCTS.MANUFACTURER` = full name |
| **Customer** | none ("player" is a headcount in `GAME_MODES.MIN_PLAYERS` / `MAX_PLAYERS`) | `CUSTOMER_ACCOUNTS.CUSTOMER_ID`, called `PLAYER_ID` in digital purchases, `BUYER_ID` in hardware sales, `SUBSCRIBER_ID` in subscription charges |
| **Platform** | `PLATFORMS.PLATFORM_NAME` = `PS5`, `Pc_gaming`, `XBOX_ONE` | `PLATFORMS.PLATFORM_NAME` = `PlayStation 5`, `PC (Steam)`; `PLATFORM_CODE` = `PS5`, `PC` |

Developer has no table or key in either system, so studios can only be matched by name. Developer-level answers therefore come from aggregating resolved catalog games (Challenge 3), not from grouping store strings.

The store also spells 8 titles differently from the catalog:

| Catalog `GAME_NAME` | Sales `TITLE_NAME` |
|---|---|
| Gran Turismo 7 | GT7 |
| Ghost of Yōtei | Ghost of Yotei |
| God of War Ragnarök | God of War Ragnarok |
| Death Stranding 2: On the Beach | DEATH STRANDING 2 |
| Marvel's Spider-Man 2 | Spider-Man 2 |
| Ratchet & Clank: Rift Apart | Ratchet and Clank Rift Apart |
| The Last of Us Part I | The Last of Us Part 1 |
| Demon's Souls | Demons Souls |

**Ontology assists by:** mapping each local name to one class.
- Title / Store Title → **Game**
- Studio → **Developer**
- Label / SIE → **Publisher**
- Player / Subscriber / Buyer / Account → **Customer**

Each class has representations in both schemas, so an agent can answer "How much did Gran Turismo 7 make?" or "How many active customers are there?" without knowing the local vocabulary. There is deliberately no separate Title class.

---

## Challenge 3: Identity resolution with imperfect keys

There is no single shared game key. Sales has its own key, `TITLES.TITLE_ID` (5001-5090, assigned in release order), which does **not** equal the catalog `GAME_ID`. Identity has to be resolved from a *hierarchy* of keys, degrading gracefully as they disappear.

| Link strength | Key | Titles resolved |
|---|---|---|
| Strong (direct) | `TITLES.CATALOG_GAME_ID = GAMES.GAME_ID` | 75 |
| Medium (crosswalk) | `TITLE_CODE_XREF.CATALOG_GAME_ID` (Challenge 4) | 13 |
| Weak (fallback) | accent-folded name + release year | 2 |

**Intentional degradations:**
- `TITLES.CATALOG_GAME_ID` is **NULL for 15 titles**: every 7th title, plus Ghost of Yotei and Uncharted: Legacy of Thieves Collection.
- `DIGITAL_PRODUCT_TRANSACTIONS.TITLE_ID` is **NULL on every 10th purchase** (53,444 rows). The game can be recovered only through `DIGITAL_PRODUCT_ID` → `DIGITAL_PRODUCTS.TITLE_ID`.
- **Ghost of Yōtei** and **Uncharted: Legacy of Thieves Collection** have no catalog ID and no store code.
  - Ghost of Yōtei matches only on its name with accents folded (`COLLATE(..., 'en-ci-ai')`) plus the release year.
  - Uncharted needs its text JP release date parsed.
- `TITLES.RELEASE_DATE` is text (`YYYYMMDD`), and for 3 titles it is the **Japanese date**, one day earlier.

**Ontology assists by:** linking the identifier terms **Catalog Game ID**, **Sales Title ID** and **Title Code** to Game (IDENTIFIED_BY), plus a **Game Identity Match Rule** (strong → medium → weak) that applies to Game Revenue. Joining on `CATALOG_GAME_ID` alone loses 15 titles' revenue.

---

## Challenge 4: Game identity via code crosswalk

The store identifies games by **PlayStation Store title codes**, which the catalog doesn't have.

| Aspect | GAME_CATALOG | GAME_SALES |
|---|---|---|
| Code | `GAME_ID` (numeric) | `TITLE_CODE` per platform: `PPSA#####` (PS5), `CUSA#####` (PS4), `NPUA#####` (PS3), `PCSA#####` (Vita), `SLUS#####` (PS2) |
| Product code | n/a | `DIGITAL_PRODUCTS.SKU_CODE` = `<newest-generation title code>-C<CATEGORY_ID><seq>`, e.g. `PPSA97384-C0301` |

`GAME_SALES.TITLE_CODE_XREF` (100 rows; `TITLE_CODE`, `TITLE_ID`, `PLATFORM_CODE`, `CATALOG_GAME_ID`) is the **title code ↔ catalog game crosswalk** that stitches them together.

**Extra difficulty:**
- PC and Switch releases have no code, so 4 products have no SKU.
- For 13 titles the crosswalk is the **only** route from a sale to the catalog. Decoding a SKU means matching its prefix to `TITLE_CODE`, then following the crosswalk to the game, and matching its `C<CC>` part to `REVENUE_TYPES.CATEGORY_ID`.

**Ontology assists by:** defining **Title Code** and **SKU Code** as identifier terms (Digital Product IDENTIFIED_BY SKU Code; SKU Code RELATED_TO Title Code), with representations on `TITLE_CODE_XREF`. A SKU like `CUSA86252-C1101` then resolves to a game and product type. Catalog-only attributes then reach crosswalk-only titles too: "How much revenue have games built on the Naughty Dog engine made?" needs the crosswalk for both The Last of Us Part II titles.

---

## Challenge 5: Divergent code and value conventions

Same concept, different encodings: silent wrong answers if joined naively.

| Concept | Convention A | Convention B |
|---|---|---|
| Region | `CUSTOMER_ACCOUNTS.REGION`: SIE codes `SIEA`, `SIEE`, `SIEJ`, `SIEAP`, `SIELA` | `HARDWARE_SALES_TRANSACTIONS.REGION`: `NA`, `EU`, `JP`, `ASIA`, `LATAM`. **Two conventions inside Sales.** |
| Platform | Catalog `PLATFORM_NAME` = `PS5`, `Pc_gaming` | Sales `PLATFORM_NAME` = `PlayStation 5`, `PC (Steam)`, plus `PLATFORM_CODE` = `PS5`, `PSV`, `PC`, `NSW` |
| Exclusive flag | Catalog `GAME_PLATFORMS.IS_EXCLUSIVE` BOOLEAN | Sales `GAME_PLATFORMS.IS_EXCLUSIVE` text `'Y'` / `'N'` |
| Release date | Catalog `GAMES.RELEASE_DATE` DATE (worldwide) | Sales `TITLES.RELEASE_DATE` text `'YYYYMMDD'` (sometimes the JP date) |
| Monetization vocabulary | `MONETIZATION_TYPES.MONETIZATION_NAME` lower case (`battle_pass`) | `REVENUE_TYPES.MONETIZATION_TYPE` upper case (`BATTLE_PASS`) |

**Ontology assists by:** code-mapping terms (**SIE Region Code**, **Sales Region Code** with SIE Region Code EQUIVALENT_TO Sales Region Code, **Platform Code**, **Exclusivity Flag**). "Customers in North America" then filters `SIEA`, "hardware revenue in North America" filters `NA`, and "currently exclusive" compares `'Y'` instead of `TRUE`.

---

## Challenge 6: Overloaded column *names* (same name, different meaning)

Several column names appear in many tables and mean something different each time: a trap for keyword-driven agents.

| Name | Meaning A | Meaning B | Meaning C |
|---|---|---|---|
| `STATUS` | `GAMES.STATUS`: game lifecycle (`RELEASED`, `REMASTERED`, `DELISTED` = Concord) | `CUSTOMER_ACCOUNTS.STATUS`: account `A` / `S` / `C` | `DIGITAL_PRODUCTS.STATUS`: store listing `LIVE` / `DELISTED` |
| `MONETIZATION_*` | `MONETIZATION_TYPES` (both systems): the **business model** tagged on a game; nothing priced | `REVENUE_TYPES.MONETIZATION_TYPE`: **what was actually sold**, on priced products | n/a |
| `*CATEGORY*` | `GENRE_CATEGORY_MAP.CATEGORY_NAME`: a genre feature group | `ACCESSIBILITY_FEATURES.FEATURE_CATEGORY` | `REVENUE_TYPES.CATEGORY_GROUP`: DIGITAL / HARDWARE / SUBSCRIPTION, where **BASE_GAME_PHYSICAL is in DIGITAL** |
| `*DEVELOPER*` | `GAMES.DEVELOPER_NAME`: the studio | `DIGITAL_PRODUCT_TRANSACTIONS.NET_DEVELOPER_REVENUE`: really the **publisher's** share after the store cut | `ENGINES.DEVELOPER_COMPANY`: the engine vendor; for in-house engines it holds a studio name (e.g. `Santa_Monica_Studio`) |

**Ontology assists by:** binding each column to a typed term:
- **Game Lifecycle Status**, **Account Status** and **Listing Status**.
- **Monetization Model** vs **Revenue Type Code**, so "battle pass revenue" sums sold battle passes, not tagged games.
- **Net Publisher Revenue** as a metric.
- **Engine**, which states that `ENGINES.DEVELOPER_COMPANY` is the engine vendor, not the game's Developer.

This removes the ambiguity of the shared names.

---

## Challenge 7: Hierarchy roll-ups (parent genres)

The structural challenge here is a **hierarchy**.

- Genre membership is inferred per game (`GAME_GENRE_CLASSIFICATION`, `MATCH_STATUS = 'FULL'`) from feature rules in `GENRE_RULES`. The rules form a single-parent tree (`PARENT_GENRE`, `VW_GENRE_HIERARCHY`).
- **Parent genres have no rows of their own.** Action, RPG and Adventure match nothing directly, so "revenue per genre" naively lists only leaf and mid-level genres.
- The strict tree also puts ActionRPG and Soulslike under Action, so **RPG rolls up to 0 games** (kept on purpose as a test).

**Ontology assists by:**
- Curated genre terms with synonyms (FPS = first-person shooter; Shooter HAS_VARIANT FPS / TPS).
- A **Genre Roll-up Rule**: parents use `VW_GAME_GENRE_ROLLUP`, and RPG also includes ActionRPG and Soulslike.
- A **Genre Revenue** metric that warns genre totals overlap and are not additive.
