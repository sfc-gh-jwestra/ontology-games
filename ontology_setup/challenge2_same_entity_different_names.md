# Challenge 2: Same entity, different names across systems

Reference: [Ontology Challenges](README_ontology_challenges.md), "Challenge 2: Same entity, different names across systems".

The same Challenge 2 problem already shows up in ONTOLOGY_DEMO: one real-world thing goes by different names in different schemas. Here are the clearest cases, with real data first and likely external sources second.

## Already in your data

| Ontology class | GAME_CATALOG | GAME_SALES | VIDEOWL (KG) | Notes |
|---|---|---|---|---|
| **Studio / Developer** | `DEVELOPERS.DEVELOPER_NAME`; `STUDIO_ACQUISITIONS` calls it a studio | `NET_DEVELOPER_REVENUE` (actually the publisher's share) | `V_DEVELOPER` **and** `V_SOFTWAREHOUSE` | The KG has two classes for one concept. |
| **Engine vendor** | `ENGINES.DEVELOPER_COMPANY` | — | — | Here "developer" means the engine's maker (Epic, Unity), not the game studio. |
| **Publisher / Manufacturer / Platform holder** | `PUBLISHERS` (Sony, ID 2) | `HARDWARE_PRODUCTS.MANUFACTURER` = "Sony Interactive Entertainment" (free text, no FK) | — | One company playing three roles under three names. |
| **Game / Title / Product** | `GAMES.GAME_NAME` | `DIGITAL_PRODUCTS.PRODUCT_NAME` (one game becomes many SKUs, e.g. Digital Edition, Physical Edition) | `KG_NODE.NAME` | Grain mismatch: SALES sells SKUs, while CATALOG describes games. |
| **Customer / Account / Subscriber** | — | `CUSTOMER_ACCOUNTS`, PS Plus "subscribers" (`PS_PLUS_SUBSCRIBER_HISTORY`), plus buyers in the transaction tables | — | One person is an account, a subscriber and a buyer. |
| **Platform vs storefront** | `PLATFORMS` (hardware family: PS4, PC) | `DIGITAL_PRODUCT_TRANSACTIONS.PLATFORM_ID` actually means the **store** (PSN, Steam, Xbox Store); `CONSOLE_SHIPMENT_HISTORY.GENERATION` | `V_PLATFORM`, `V_MULTIPLATFORM` | "Pc_gaming" is really the Steam/Epic storefront. |
| **Revenue** | — | `MONTHLY_INCOME`, `INCOME`, `GROSS_REVENUE`, `NET_DEVELOPER_REVENUE`, `TARGET_AMOUNT`, `ESTIMATED_TOTAL_REVENUE` | — | Six names. Some are gross, some net of store cut, one is actual dollars rather than 1/1000. |
| **Genre / Category / Type** | `GENRE_RULES.GENRE`, `GAMEPLAY_TYPES`, `GENRE_CATEGORY_MAP.CATEGORY_NAME` | `REVENUE_CATEGORIES` ("category" means a commerce type) | `V_RPG`, `V_ACTIONRPG`, … | "Category" means a genre group in one place and a sales type in another. |
| **Open world** | Three gameplay types: `OpenWorld`, `Open_map`, `free_roaming` | — | `V_OPENWORLD` | Four labels for one concept. |
| **Duplicate KG classes** | — | — | `V_SPORTS` / `V_SPORTIVE` / `VW_ONT_SPORT`; `V_EDUCATIONAL` / `V_EDUCATIVE`; `V_SURVIVAL` / `V_SURVIVALGAME`; `V_PUZZLE` / `VW_ONT_PUZZLEGAME`; `V_STRATEGY` / `VW_ONT_STRATEGIC` | Same class under several names. |
| **Point of view** | `GAMES.POV` | — | `V_POV`, `V_FIRSTPERSON`, `V_THIRDPERSON` | An attribute in one place, a class hierarchy in another. |
| **Multiplayer** | `GAME_MODES.MODE_NAME` / `MAX_PLAYERS`, gameplay types `Co-op` / `PVP` / `Party` | — | `V_MULTIPLAYER`, `V_SINGLE`, `V_PARTY` | Same idea, stored in three different ways. |
| **Franchise / Series / Sequel line** | `FRANCHISES`, `GAME_FRANCHISES`, `GAME_SEQUELS` | `ADD_GAME_TMP.FRANCHISE_NAME` (a copy of the name) | — | See the deferred `merge-sequels-into-franchises` plan. |

The VIDEOWL schema also shows the reverse trap, Challenge 7 in the README: `V_PLATFORM` is hardware but `V_PLATFORMER` is a genre.

## Where real external systems would diverge

If you add messy sources the way the healthcare example does, these are realistic synonyms for the same entities:

| Ontology class | PlayStation Store | Steam | Retail / Circana | Ratings boards | Finance / ERP |
|---|---|---|---|---|---|
| **Game** | Concept / Title ID (`CUSA…`, `PPSA…`) | App ID | SKU / UPC / "title" | Product title | Product line / cost center |
| **Developer** | "Studio" (Insomniac, Santa Monica) | "Developer" | rarely tracked | "Applicant" | Legal entity / subsidiary |
| **Publisher** | "Publisher" / "SIE" | "Publisher" | "Label" / "Manufacturer" | "Company" | Parent company |
| **Customer** | PSN Online ID / account | SteamID | — (anonymous POS) | — | Bill-to customer |
| **Region** | SIEA / SIEE / SIEJ | Store region | NA / EMEA / APAC | ESRB / PEGI / CERO territories | Reporting segment |
| **Age rating** | Content rating | Mature content flags | Box rating | `ESRB M` = `PEGI 18` = `CERO Z` | — |
| **Add-on** | Add-on / entitlement | DLC | Season pass card | — | Deferred revenue item |
| **Release** | Launch / availability date | Release date | Street date | Rating date | Revenue recognition date |

## Strongest candidates for a demo of this challenge

These are the most concrete and already partly present:

1. **Developer, Studio, Software house, Engine developer.** Four names covering two different concepts, so the ontology both merges synonyms and separates the false match.
2. **Platform vs storefront.** PC is a platform, but Steam and Epic are storefronts; PS5 is a platform, while the PlayStation Store is the storefront.
3. **The six revenue measures.** Map them to one Revenue concept with typed properties (gross/net, scale, source).
4. **Customer, Account, Subscriber, Buyer.** Combine with identity resolution (Challenge 3) if you add a PSN source that uses Online IDs.
5. **Rating-board equivalence.** `ESRB M` ≈ `PEGI 18` ≈ `CERO Z`. The `AGE_RATINGS` table already holds several rating systems.
6. **Setting and Theme** are split across CONTEXTS, GAMEPLAY_TYPES and genre, so the same concept has different names in different places.
