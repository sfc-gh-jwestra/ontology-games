# Plan: Business Ontology phased build guide and with/without-ontology evaluation set (revision 4)

## 1. Context

**Inputs:**
- **The guide:** the "Getting Started with Business Ontology" Google Doc (SAP example). Its 8 phases are domains, entities, metrics with formulas, code-mapping terms (`itemKind: TERM`), typed relationships, verify, representations, and the agent (`snowscope_search`, corpus `businessOntology`, plus a semantic view).
- [ontology_setup/README_ontology_challenges.md](ontology_setup/README_ontology_challenges.md): the Challenge 2 canonical-class principle.
- [ontology_setup/messy_data_design.md](ontology_setup/messy_data_design.md): physical locations after the mess.
- [ontology_setup/ontology-overview.md](ontology_setup/ontology-overview.md): classes, genre tree, play modes.
- Skill references `RELATIONSHIP_TYPES.md` and `rules/` (B-00 to B-11, R-07, R-08).

**Account state:**
- Business Ontology is enabled and empty (`SYSTEM$GET_GLOSSARY_SUMMARY()` = 0 domains).
- There are no semantic views.

## 2. Decision log (written verbatim into both docs)

| # | Decision | Reason |
|---|---|---|
| D1 | **One canonical class per real-world entity.** Every local name is a synonym; every system's table or column is a representation. No per-system duplicate nodes. | README Challenge 2: "one canonical class; the mappings collapse the synonyms". The agent must answer without local vocabulary. |
| D2 | **Game (not Title) is the class**, owned by Game Catalog. Title, Store Title and Product Title are synonyms. `TITLES` and `TITLE_CODE_XREF` are representations of Game. | Title and Game are the same thing in two systems. Two nodes plus `EQUIVALENT_TO` would force the agent to know the local word. |
| D3 | The same pattern applies to **Platform** (Console, Store Platform), **Developer** (Studio), **Publisher** (Label, SIE) and **Customer** (Player, Subscriber, Buyer, Account). | Same reason as D1. |
| D4 | **Owner domain = who governs the definition**, not where rows live. One node, one domain; edges and representations may cross schemas. | The API takes one `domainName` per term. Multi-domain membership is not verified, so it is not used. |
| D5 | **Identity = identifier terms, not extra classes.** Game is identified by Catalog Game ID, Sales Title ID and Title Code. Digital Product is identified by SKU Code. The **Game Identity Match Rule** (strong, then medium, then weak) applies to Game and Game Revenue. | Challenges 3 and 4/5. Identifiers are keys of one class, not separate entities. |
| D6 | `EQUIVALENT_TO` is used **only** for SIE Region Code vs Sales Region Code. | These are two distinct code fields with their own value lists that mean the same thing. That is not the same as one entity in two systems. |
| D7 | **Curated genre layer:** 14 genre TERM nodes (6 top-level, 8 subgenres) with synonyms, membership and roll-up rules. The other 32 genres stay values in `GENRE_RULES`, listed in the Genre Rule term. | Genre is the main way catalog questions are asked, and synonyms need nodes. Not all 46: drift against the executable `GENRE_RULES` (B-02), 17 unmatchable rules, and some fail the altitude test (B-05). |
| D9 | **Do NOT fix the RPG gap in `GENRE_RULES`.** The table stays single-parent (RPG rolls up to 0 games by the strict tree). The ontology alone supplies "ActionRPG is also an RPG". | User decision. The gap is a deliberate with/without-ontology test. Do not raise it again. |
| D10 | **Excluded as genres:** Other (a bucket); MMO, LocalMultiplayer, MultiplayerAvailable (play modes, overview §7); LiveService (a business model, covered by the Monetization Model term). | Altitude test (B-05). |
| D11 | **SKUs:** Digital Product (synonym SKU, Add-on) is identified by the **SKU Code** term, which describes the format `<TitleCode>-C<CATEGORY_ID><seq>`. SKU Code is `RELATED_TO` Title Code. Game and Digital Product carry a **grain warning**: one game is sold as many SKUs, so count games, not products. | 354 products (about 3.9 per title, up to 25); 350 have a SKU and 4 do not (PC-only, no store code). The SKU prefix traces back to a Game through the crosswalk. |
| D12 | The **Revenue Type Code** term flags that `BASE_GAME_PHYSICAL` sits in the `DIGITAL` category group. | "Digital revenue by group" silently includes physical editions. |
| D13 | **The `TITLE_CODE_XREF` value is stated as a revenue split** in the Game Revenue description: strong 72 titles / $17,619,373.27; medium (xref) 13 / $1,382,678.74; weak (name+year) 2 / $229,800.00. | It makes the cost of skipping each identity route explicit. |
| D14 | Genre rules go in **descriptions**, not formulas. Only METRIC nodes take a formula. `GENRE_RULES` is named as the executable source. | API constraint; limits drift. |
| D15 | **Representations (Phase 7) are required**, not optional. | They are how D1-D3 work physically: each canonical class is linked to every system's object. |
| D16 | **Documentation only.** Nothing is created in Business Ontology, no semantic view, no agent. | User decision ("Phased doc only"). |

## 3. Content of `ontology_setup/business_ontology_phases.md`

### Intro and "What you'll build"

| Object | Count |
|---|---|
| Domains | 3 |
| Entities | 22 |
| Metrics | 15 |
| Terms | 33 |
| Relationships | about 58 |
| Representations | about 60 (Phase 7) |
| Agent | 1 (Phase 8 follow-on) |

The intro also includes the decision log (section 2).

### Phase 1: Domains
Game Catalog, Game Commerce, Genre Taxonomy.

### Phase 2: Entities (22)

**Canonical classes:**

| Owner domain | Entity | Synonyms | Locations (description and Phase 7) |
|---|---|---|---|
| Game Catalog | **Game** | Title, Store Title, Product Title | `GAME_CATALOG.GAMES` (`GAME_ID`, `GAME_NAME`, DATE `RELEASE_DATE`, `STATUS`); `GAME_SALES.TITLES` (`TITLE_ID` 5001-5090, `TITLE_NAME`, `CATALOG_GAME_ID` NULL for 15, text `RELEASE_DATE`); `GAME_SALES.TITLE_CODE_XREF`. 8 Sales names differ (GT7, Ghost of Yotei, DEATH STRANDING 2, Spider-Man 2, God of War Ragnarok, Ratchet and Clank Rift Apart, The Last of Us Part 1, Demons Souls). **Grain: one game, many SKUs** |
| Game Catalog | **Platform** | Console, Store Platform, System | Both `PLATFORMS` tables (`PS5` / `PlayStation 5`, `Pc_gaming` / `PC (Steam)`, Sales `PLATFORM_CODE`); `PLATFORM_ID` is shared |
| Game Catalog | **Developer** | Studio, Development Studio | `GAMES.DEVELOPER_ID/NAME/IS_INDIE`; `STUDIO_ACQUISITIONS.STUDIO_NAME`; `TITLES.STUDIO` (spaces vs underscores). Not `ENGINES.DEVELOPER_COMPANY` |
| Game Catalog | **Publisher** | Label, Publishing Label, SIE | `GAMES.PUBLISHER_ID/NAME/HQ`; `GAME_FRANCHISES.PUBLISHER_ID`; `TITLES.PUBLISHER_LABEL`; `HARDWARE_PRODUCTS.MANUFACTURER` |
| Game Commerce | **Customer** | Player, Subscriber, Buyer, Account | `CUSTOMER_ACCOUNTS.CUSTOMER_ID`; `DIGITAL_PRODUCT_TRANSACTIONS.PLAYER_ID`; `SUBSCRIPTION_CHARGES.SUBSCRIBER_ID`; `HARDWARE_SALES_TRANSACTIONS.BUYER_ID`. Not `GAME_MODES` player counts |

**Other entities:**
- **Game Catalog:** Franchise (`GAME_FRANCHISES`, also `GAMES.FRANCHISE_NAME`), Engine, Game Mode, Age Rating.
- **Genre Taxonomy:** Genre (the class), Feature Category, Gameplay Type, Mechanic, Context, Narrative Structure.
- **Game Commerce:**
  - Digital Product: synonyms SKU, Add-on; `DIGITAL_PRODUCTS` (`TITLE_ID`, `CATEGORY_ID`, `SKU_CODE`, `STATUS`); grain warning.
  - Hardware Product, Subscription Plan.
  - Digital Transaction (`TITLE_ID` NULL for every 10th row; recover it via `DIGITAL_PRODUCT_ID`).
  - Hardware Sale, Subscription Charge, Revenue Type.

### Phase 3: Metrics (15), with formula, rule and reference answer

| Domain | Metric | Formula | Correct answer / trap |
|---|---|---|---|
| Commerce | Digital Gross Revenue | `SUM(GROSS_REVENUE)` from `DIGITAL_PRODUCT_TRANSACTIONS` | **$19,231,852.01** (trap: filtering `TITLE_ID IS NOT NULL` gives $17,312,180.80) |
| | Net Publisher Revenue | `SUM(NET_DEVELOPER_REVENUE)` | **$19,119,344.99** (the column is misnamed) |
| | Platform Commission Revenue | `SUM(GROSS - NET_DEVELOPER_REVENUE)` | **$112,507.02** |
| | Hardware Revenue | hardware `SUM(GROSS_REVENUE)` | **$175,660,810.62**; NA $70,243,201.72 |
| | Subscription Revenue | subscription `SUM(GROSS_REVENUE)` | **$35,634,616.54** |
| | Total Platform Revenue | Hardware + Commission + Subscription | **$211,407,934.18** (trap: all gross = $230,527,279.17) |
| | Active Customer Count | `STATUS = 'A'` | **96,773** (trap: 289,225); NA (`SIEA`) = 38,699 |
| | Battle Pass Sales Revenue | `REVENUE_TYPES.MONETIZATION_TYPE = 'BATTLE_PASS'` | **$150,389.48** (trap: the 2 battle-pass-model games) |
| | Currently Exclusive Game Count | `IS_EXCLUSIVE = 'Y'` AND (PERMANENT OR TIMED with `EXCLUSIVE_END >= CURRENT_DATE`) | **53 rows** |
| Catalog | Game Revenue | digital gross with Game resolved by `COALESCE(dpt.TITLE_ID, dp.TITLE_ID)`, then the Match Rule | **$19,231,852.01**; strong only $15,861,443.42; the route split is in D13. GT7 $899,999.98; Ghost of Yōtei $198,000 |
| | Developer Revenue | Game Revenue by Developer | Santa Monica $3,419,553.73; Insomniac $3,357,639.53; Polyphony $2,653,560.00 |
| | Franchise Revenue | Game Revenue by Franchise | God of War $3,428,553.73; Marvel's Spider-Man $2,993,639.53 |
| | Active Catalog Game Count | `STATUS <> 'DELISTED'` | **89** of 90 |
| Genre | Genre Match Score | `MET / TOTAL` | member only when FULL (258 of 3,420) |
| | Weighted Overlap | `SUM(overlap * weight)` | cannibalization at >= 0.3 with the same Publisher |

A genre roll-up reference table is included:

| Genre | Games |
|---|---|
| Action | 68 |
| Strategic | 18 |
| Adventure | 13 |
| Horror | 11 |
| Simulator | 1 |
| RPG, strict tree | 0 |
| RPG, ontology-aware | 43 (re-verified in step 7) |

### Phase 4: Terms (33)

- **4a. Identifier and policy (5):**
  - Catalog Game ID
  - Sales Title ID
  - Title Code (PPSA = PS5, CUSA = PS4, NPUA = PS3, PCSA = Vita, SLUS = PS2; none for PC/Switch; 12 titles have several)
  - **SKU Code** (format, category digits = `REVENUE_TYPES.CATEGORY_ID`, prefix = Title Code; 4 products have none)
  - Game Identity Match Rule
- **4b. Code mapping (14):**
  - Catalog: Game Lifecycle Status, Franchise Relationship Type, Age Rating System, Monetization Model (includes LiveService), Platform Code.
  - Commerce: Revenue Type Code (with the `BASE_GAME_PHYSICAL` in `DIGITAL` flag), SIE Region Code, Sales Region Code, Account Status, Listing Status, Exclusivity Flag.
  - Genre: POV Code, Genre Match Status, Genre Rule (syntax, `PARENT_GENRE`, disjoint pairs, the 32 value-only genres, and an explicit note that the table is single-parent by design, per D9).
- **4c. Curated genres (14):** synonyms and member counts as in revision 3.
  - Top level: Action, Adventure, RPG, Horror, Simulator, Strategic.
  - Subgenres: Shooter, FPS, TPS, ActionRPG, Soulslike, Fighting, Platformer, Stealth.

### Phase 5: Relationships (about 58)

- **Identity:**
  - Game IDENTIFIED_BY Catalog Game ID, Sales Title ID and Title Code.
  - **Digital Product IDENTIFIED_BY SKU Code.**
  - **SKU Code RELATED_TO Title Code.**
  - Game Identity Match Rule APPLIES_TO Game and Game Revenue.
  - Platform Code CLASSIFIES Platform.
- **Catalog, Commerce, Genre and metric-lineage edges:** as in revision 3.
  - Genre layer: 14 CLASSIFIES Game; Shooter HAS_VARIANT FPS/TPS; RELATED_TO for the subgenre and top-level edges; ActionRPG and Soulslike RELATED_TO RPG.
  - Metric lineage: DERIVES chains from Digital Gross Revenue and into Total Platform Revenue; MEASURES and APPLIES_TO edges.
- **Two mermaid diagrams:**
  - Canonical classes with their identifiers and per-system representations.
  - The genre layer.

### Phases 6-8
- **Phase 6:**
  - Expected counts from `SYSTEM$GET_GLOSSARY_GRAPH()`.
  - Search checks: "title revenue" returns Game / Game Revenue; "souls-like" returns Soulslike; "SKU" returns Digital Product / SKU Code.
- **Phase 7:** representations (required, D15). The lineage example: dropping `TITLE_CODE_XREF` breaks Game, Title Code, SKU Code and Game Revenue.
- **Phase 8:**
  - A naive semantic view (joins only) plus the agent spec with the 3 required settings.
  - The **with/without protocol**: run the same evaluation set on a baseline agent (semantic view only) and a BON agent (semantic view + `snowscope_search`), then score both against the expected answers.

## 4. Content of `ontology_setup/ontology_eval_set.md`

**Columns:** #, question (canonical vocabulary only), challenge, expected answer, naive trap and likely wrong answer, ontology nodes that fix it.

**Scoring rule:** exact match for counts. For currency, match within $0.01.

| # | Question | Challenge | Expected | Naive trap |
|---|---|---|---|---|
| 1 | Total digital game revenue? | C3 | $19,231,852.01 | drops untitled transactions: $17,312,180.80 |
| 2 | Revenue for Gran Turismo 7? | C2 | $899,999.98 | Sales name is "GT7": $0 / not found |
| 3 | Revenue for Ghost of Yōtei? | C2/C3 weak key | $198,000.00 | no catalog ID, no store code, accent: $0 |
| 4 | Revenue for every catalog game (total)? | C3/C4-5 | $19,231,852.01 | strong key only: $15,861,443.42 |
| 5 | Top developer by revenue? | C1/C2 | Santa Monica Studio, $3,419,553.73 | Developer has no table; Sales calls it Studio |
| 6 | Revenue for the God of War franchise? | C1 | $3,428,553.73 | Franchise has no table |
| 7 | How many active customers? | C7 | 96,773 | all accounts: 289,225 |
| 8 | Active customers in North America? | C6 | 38,699 | `REGION = 'NA'`: 0 |
| 9 | Hardware revenue in North America? | C6 | $70,243,201.72 | `REGION = 'SIEA'`: $0 |
| 10 | Revenue from battle passes? | C7 | $150,389.48 | answers "2 games" (business-model tag) |
| 11 | Net publisher revenue from digital sales? | C7 | $19,119,344.99 | calls it developer revenue / mixes up developers |
| 12 | Total revenue the platform keeps? | metric | $211,407,934.18 | sums all gross: $230,527,279.17 |
| 13 | How many RPG games are there? | genre / D9 | 43 (re-verified) | strict tree: 0 |
| 14 | How many first-person shooters? | genre synonym | 10 | "first-person" is not a genre value |
| 15 | How many game-platform pairs are currently exclusive? | C6 | 53 | `IS_EXCLUSIVE = TRUE` fails (Y/N text) |
| 16 | How many active (not delisted) games are in the catalog? | C7 | 89 | 90 |
| 17 | How many games did we sell digitally? | grain (D11) | 90 games (computed in step 7) | counts products: 354 |
| 18 | Which game and product type is SKU `<sample>`? | C4-5 / D11 | filled in at step 7 from live data | cannot read the SKU code |
| 19 | Which game has store code `<sample CUSA code>`? | C4-5 | filled in at step 7 (a medium-route title) | no idea the crosswalk exists |
| 20 | What breaks if TITLE_CODE_XREF is dropped? | governance | Game, Title Code, SKU Code, Game Revenue | cannot answer (no representations) |

**Also in the file:**
- A "how to run" section for the baseline vs BON agent, with a results template (correct / incorrect per agent).
- The reference SQL for each expected answer, taken from the step 7 queries.

## 5. Implementation steps

1. Write the decision log (D1-D16) and the intro / counts in `business_ontology_phases.md`.
2. Write Phases 1-3: domains, canonical-class and other entities, metrics, genre roll-up table.
3. Write Phase 4: identifier/policy terms (including SKU Code), code-mapping terms, 14 genre terms.
4. Write Phase 5 relationships and the two mermaid diagrams, then Phases 6-8 (verify, required representations, agent and with/without protocol).
5. Write `ontology_eval_set.md`: 20 questions, expected vs naive answers, the nodes that fix each, reference SQL, results template.
6. Update [ontology_setup/ontology-overview.md](ontology_setup/ontology-overview.md):
   - §8 points to both docs.
   - Record the curated-genre, SKU and canonical-class decisions.
   - Add project memory for D9 ("never fix or raise the RPG gap in GENRE_RULES") and pointers to the docs.
7. Verify with read-only queries:
   - All tables/columns exist.
   - Recompute every expected and naive answer, filling the step 7 placeholders (#13, #14, #17, #18, #19).
   - Relationship types are in the vocabulary.
   - Synonym uniqueness.
   - Counts tables match the content.

## 6. Verification

- Every expected answer in both docs matches a live read-only query. Every naive answer reproduces the stated trap.
- **Decision checks:**
  - No duplicate per-system nodes (D1-D3).
  - EQUIVALENT_TO only for the regions (D6).
  - HAS_VARIANT only for Shooter to FPS/TPS (D8).
  - No CUSTOM.
  - `GENRE_RULES` is unchanged (D9; compare its hash with the current one).
- No Snowflake objects are created (D16). The glossary summary still shows 0 domains.

## 7. Critical Files

- ontology_setup/business_ontology_phases.md - phased build guide plus decision log
- ontology_setup/ontology_eval_set.md - with/without-ontology test questions and answers
- [ontology_setup/messy_data_design.md](ontology_setup/messy_data_design.md) - physical locations behind synonyms and representations
- [ontology_setup/ontology-overview.md](ontology_setup/ontology-overview.md) - prior analysis; §8 repointed
