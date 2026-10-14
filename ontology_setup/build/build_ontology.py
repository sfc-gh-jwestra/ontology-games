"""Generate the SQL that builds the ONTOLOGY_DEMO Business Ontology.

Source of truth for the content: ontology_setup/business_ontology_phases.md (decision log D1-D16).
Each payload is serialised once with json.dumps and escaped once for the SQL literal,
as the business-ontology skill requires.

Usage (from the repo root):
    python3 ontology_setup/build/build_ontology.py      # writes ontology_setup/build/*.sql
    snow sql -c JWESTRA_AWS1 -f ontology_setup/build/01_domains_terms.sql
    snow sql -c JWESTRA_AWS1 -f ontology_setup/build/02_relationships.sql
    snow sql -c JWESTRA_AWS1 -f ontology_setup/build/03_representations.sql
"""
import json
from pathlib import Path

OUT = Path(__file__).parent
DB = "ONTOLOGY_DEMO"
CAT, SAL = f"{DB}.GAME_CATALOG", f"{DB}.GAME_SALES"
D_CAT, D_COM, D_GEN = "Game Catalog", "Game Commerce", "Genre Taxonomy"

DOMAINS = [
    (D_CAT, "What a game is: Game, Platform, Developer, Publisher, Franchise, Engine, modes and ratings. "
            "Owns the canonical Game, Platform, Developer and Publisher classes for both systems."),
    (D_COM, "How a game earns money: Customer, products, transactions, subscriptions and revenue types "
            "(GAME_SALES). Owns the canonical Customer class."),
    (D_GEN, "How a game is classified: Genre, its feature dimensions and a curated set of genres."),
]

# (name, domain, kind, synonyms, description[, formula])
TERMS = [
    # ---------------- Phase 2a: canonical classes (D1-D3)
    ("Game", D_CAT, "ENTITY", ["Title", "Store Title", "Product Title"],
     "A video game. Master record GAME_CATALOG.GAMES (GAME_ID, GAME_NAME, RELEASE_DATE as DATE, STATUS, POV). "
     "The Sales system calls a game a TITLE: GAME_SALES.TITLES (TITLE_ID 5001-5090 is a Sales-only key; "
     "CATALOG_GAME_ID links to GAMES.GAME_ID but is NULL for some titles; RELEASE_DATE is text YYYYMMDD). "
     "Store codes are in GAME_SALES.TITLE_CODE_XREF. 8 Sales names differ: GT7 = Gran Turismo 7, "
     "Ghost of Yotei = Ghost of Yōtei, DEATH STRANDING 2 = Death Stranding 2: On the Beach, "
     "Spider-Man 2 = Marvel's Spider-Man 2, God of War Ragnarok = God of War Ragnarök, "
     "Ratchet and Clank Rift Apart = Ratchet & Clank: Rift Apart, The Last of Us Part 1 = The Last of Us Part I, "
     "Demons Souls = Demon's Souls. Match a Title to a Game with the Game Identity Match Rule. "
     "GRAIN: one game is sold as many SKUs (Digital Products); count games, not products. "
     "To count games with sales, resolve each sale to a catalog GAME_ID first, then COUNT(DISTINCT GAME_ID)."),
    ("Platform", D_CAT, "ENTITY", ["Console", "Store Platform", "System"],
     "A hardware platform or storefront a game runs on. Catalog GAME_CATALOG.PLATFORMS (PLATFORM_NAME like PS5, "
     "Pc_gaming, XBOX_ONE). Sales GAME_SALES.PLATFORMS (same PLATFORM_ID values; PLATFORM_NAME like PlayStation 5, "
     "PC (Steam); PLATFORM_CODE like PS5, PC). PLATFORM_ID is the only key shared by both systems. "
     "Not the Platformer genre."),
    ("Developer", D_CAT, "ENTITY", ["Studio", "Development Studio"],
     "The studio that builds a game. No table of its own: GAMES.DEVELOPER_ID, GAMES.DEVELOPER_NAME "
     "(e.g. Santa_Monica_Studio), GAMES.DEVELOPER_IS_INDIE; GAME_CATALOG.STUDIO_ACQUISITIONS.STUDIO_NAME. "
     "Sales calls it TITLES.STUDIO (Santa Monica Studio, spaces instead of underscores). "
     "NOT ENGINES.DEVELOPER_COMPANY, which is the engine vendor."),
    ("Publisher", D_CAT, "ENTITY", ["Label", "Publishing Label", "SIE"],
     "The company that publishes a game. No table of its own: GAMES.PUBLISHER_ID / PUBLISHER_NAME "
     "(Sony Interactive Entertainment) / PUBLISHER_HQ; GAME_FRANCHISES.PUBLISHER_ID. "
     "Sales: TITLES.PUBLISHER_LABEL = 'SIE'; HARDWARE_PRODUCTS.MANUFACTURER = 'Sony Interactive Entertainment'."),
    ("Customer", D_COM, "ENTITY", ["Player", "Subscriber", "Buyer", "Account", "Customer Account"],
     "A person with a platform account. GAME_SALES.CUSTOMER_ACCOUNTS.CUSTOMER_ID. The same key is called "
     "PLAYER_ID in DIGITAL_PRODUCT_TRANSACTIONS, SUBSCRIBER_ID in SUBSCRIPTION_CHARGES and BUYER_ID in "
     "HARDWARE_SALES_TRANSACTIONS. REGION uses SIE Region Codes; STATUS is A/S/C (Account Status). "
     "Not GAME_MODES MIN_PLAYERS/MAX_PLAYERS, which are headcounts."),
    # ---------------- Phase 2b: other entities
    ("Franchise", D_CAT, "ENTITY", ["Series", "Game Series"],
     "A series of related games. No table of its own: GAME_CATALOG.GAME_FRANCHISES (FRANCHISE_ID, FRANCHISE_NAME, "
     "FIRST_RELEASE_YEAR, SEQUENCE_ORDER, PUBLISHER_ID, RELATED_GAME_ID, RELATIONSHIP_TYPE). The name is also "
     "copied in GAMES.FRANCHISE_NAME. Sequel links are RELATED_GAME_ID + RELATIONSHIP_TYPE and may point to a "
     "game in another franchise."),
    ("Engine", D_CAT, "ENTITY", ["Game Engine"],
     "Software engine a game is built with. GAME_CATALOG.ENGINES and GAME_ENGINES (version, custom fork). "
     "ENGINES.DEVELOPER_COMPANY is the engine vendor, not the game's Developer."),
    ("Game Mode", D_CAT, "ENTITY", ["Play Mode"],
     "A way a game can be played. GAME_CATALOG.GAME_MODES (MODE_NAME, MIN_PLAYERS, MAX_PLAYERS, ONLINE_REQUIRED)."),
    ("Age Rating", D_CAT, "ENTITY", ["Content Rating"],
     "Content rating of a game. GAME_CATALOG.AGE_RATINGS (RATING_SYSTEM, RATING_VALUE, MIN_AGE) and GAME_RATINGS."),
    ("Genre", D_GEN, "ENTITY", ["Game Genre", "Game Type"],
     "Classification of a game by its features. GAME_CATALOG.GENRE_RULES (46 rows, single parent PARENT_GENRE, "
     "RULE_DEFINITION, DISJOINT_WITH) and VW_GENRE_HIERARCHY (depth, path, leaf). Membership is inferred per game "
     "in GAME_GENRE_CLASSIFICATION: a game is in a genre only when MATCH_STATUS = 'FULL'. A parent genre's members "
     "are the union of its descendants' members. See the Genre Rule term and the curated genre terms."),
    ("Feature Category", D_GEN, "ENTITY", [],
     "A group of concrete feature values used by genre rules. GAME_CATALOG.GENRE_CATEGORY_MAP "
     "(Combat, Exploration, Multiplayer, Choice, Puzzle...)."),
    ("Gameplay Type", D_GEN, "ENTITY", ["Gameplay"],
     "How a game plays. GAMEPLAY_TYPES + GAME_GAMEPLAY (free_shooting, Co-op, OpenWorld, PVP...)."),
    ("Mechanic", D_GEN, "ENTITY", ["Game Mechanic"],
     "A rule system in a game. MECHANICS + GAME_MECHANICS (permanent_death, crafting, QTE...)."),
    ("Context", D_GEN, "ENTITY", ["Setting", "Theme"],
     "Setting or theme of a game. CONTEXTS + GAME_CONTEXTS (historical, mithical, zombies_invasion...)."),
    ("Narrative Structure", D_GEN, "ENTITY", ["Story Structure"],
     "How a game's story is structured. NARRATIVE_STRUCTURES via GAMES.NARRATIVE_STRUCTURE_ID "
     "(linear, branching, emergent...)."),
    ("Digital Product", D_COM, "ENTITY", ["SKU", "Add-on", "Store Product"],
     "A sellable digital item for a game. GAME_SALES.DIGITAL_PRODUCTS (DIGITAL_PRODUCT_ID, TITLE_ID, CATEGORY_ID, "
     "PRODUCT_NAME, LIST_PRICE, IS_CONSUMABLE, SKU_CODE, STATUS). "
     "GRAIN: many products per game; a product count is not a game count."),
    ("Hardware Product", D_COM, "ENTITY", ["Console SKU", "Peripheral"],
     "A console or peripheral. GAME_SALES.HARDWARE_PRODUCTS (PLATFORM_ID, MANUFACTURER, LIST_PRICE)."),
    ("Subscription Plan", D_COM, "ENTITY", ["PlayStation Plus Plan", "PS Plus Tier"],
     "A subscription offering. GAME_SALES.SUBSCRIPTION_PLANS (PlayStation Plus tiers, annual billing)."),
    ("Digital Transaction", D_COM, "ENTITY", ["Digital Purchase"],
     "A purchase of a digital product. GAME_SALES.DIGITAL_PRODUCT_TRANSACTIONS (PLAYER_ID = customer; TITLE_ID is "
     "NULL for every 10th row - recover the game via DIGITAL_PRODUCT_ID -> DIGITAL_PRODUCTS.TITLE_ID; GROSS_REVENUE, "
     "PLATFORM_COMMISSION_PCT, NET_DEVELOPER_REVENUE = publisher share)."),
    ("Hardware Sale", D_COM, "ENTITY", ["Hardware Purchase"],
     "A purchase of a hardware product. GAME_SALES.HARDWARE_SALES_TRANSACTIONS (BUYER_ID = customer, REGION in "
     "NA/EU/JP/ASIA/LATAM, GROSS_REVENUE)."),
    ("Subscription Charge", D_COM, "ENTITY", ["Subscription Payment"],
     "A billing event for a subscription. GAME_SALES.SUBSCRIPTION_CHARGES (SUBSCRIBER_ID = customer, PLAN_ID, "
     "billing period, GROSS_REVENUE)."),
    ("Revenue Type", D_COM, "ENTITY", ["Revenue Category", "Sales Category"],
     "What kind of thing was sold. GAME_SALES.REVENUE_TYPES (CATEGORY_ID, MONETIZATION_TYPE = what was sold, "
     "CATEGORY_GROUP = DIGITAL / HARDWARE / SUBSCRIPTION)."),

    # ---------------- Phase 3: metrics
    ("Digital Gross Revenue", D_COM, "METRIC", ["Digital Revenue", "Digital Sales"],
     "Gross value of all digital store sales, before platform commission. Grain: one row per purchase in "
     "DIGITAL_PRODUCT_TRANSACTIONS. Include every row: do NOT filter TITLE_ID IS NOT NULL; about 1 in 10 rows has no "
     "TITLE_ID but still belongs to a game through DIGITAL_PRODUCT_ID -> DIGITAL_PRODUCTS.TITLE_ID. Region: join "
     "PLAYER_ID to CUSTOMER_ACCOUNTS (SIE Region Code). Additive across games, products, customers and time. "
     "Includes physical editions sold as BASE_GAME_PHYSICAL (see Revenue Type Code).",
     "SUM(GROSS_REVENUE) FROM ONTOLOGY_DEMO.GAME_SALES.DIGITAL_PRODUCT_TRANSACTIONS"),
    ("Net Publisher Revenue", D_COM, "METRIC", ["Publisher Share", "Net Revenue After Commission"],
     "Net digital revenue the Publisher keeps after the store commission. Grain: one row per digital purchase. "
     "The column is named NET_DEVELOPER_REVENUE but it is the PUBLISHER share, not the Developer's (developers are "
     "studios owned by the publisher and get no separate share). Do not report gross for this question. Same row "
     "rules as Digital Gross Revenue (keep rows with NULL TITLE_ID). Additive.",
     "SUM(NET_DEVELOPER_REVENUE) FROM ONTOLOGY_DEMO.GAME_SALES.DIGITAL_PRODUCT_TRANSACTIONS"),
    ("Platform Commission Revenue", D_COM, "METRIC", ["Store Commission", "Store Cut"],
     "The store's cut of digital sales: gross minus the publisher share, per purchase (PLATFORM_COMMISSION_PCT is "
     "the rate). Grain: one row per digital purchase. This is the only part of digital sales the platform keeps. "
     "Additive.",
     "SUM(GROSS_REVENUE - NET_DEVELOPER_REVENUE) FROM ONTOLOGY_DEMO.GAME_SALES.DIGITAL_PRODUCT_TRANSACTIONS"),
    ("Hardware Revenue", D_COM, "METRIC", ["Console Revenue"],
     "Gross sales of consoles and peripherals. Grain: one row per hardware purchase in HARDWARE_SALES_TRANSACTIONS "
     "(BUYER_ID = customer, linked to HARDWARE_PRODUCTS). Region: filter this table's own REGION column, which uses "
     "Sales Region Codes NA/EU/JP/ASIA/LATAM; the SIE codes (SIEA...) are for customers and match nothing here. "
     "Platform keeps all of it. Additive.",
     "SUM(GROSS_REVENUE) FROM ONTOLOGY_DEMO.GAME_SALES.HARDWARE_SALES_TRANSACTIONS"),
    ("Subscription Revenue", D_COM, "METRIC", ["PlayStation Plus Revenue"],
     "Gross PlayStation Plus billing. Grain: one row per subscription charge in SUBSCRIPTION_CHARGES (SUBSCRIBER_ID = "
     "customer, PLAN_ID = Subscription Plan, billing period dates). Gross; no commission is deducted. No region "
     "column: for region join SUBSCRIBER_ID to CUSTOMER_ACCOUNTS (SIE Region Code). Platform keeps all of it. Additive.",
     "SUM(GROSS_REVENUE) FROM ONTOLOGY_DEMO.GAME_SALES.SUBSCRIPTION_CHARGES"),
    ("Total Platform Revenue", D_COM, "METRIC", ["Platform Revenue"],
     "What the platform keeps business-wide = Hardware Revenue + Platform Commission Revenue + Subscription Revenue. "
     "Digital contributes ONLY the commission; the publisher share is not platform revenue. Pitfall: summing every "
     "GROSS_REVENUE column (including full digital gross) overstates it. Additive across the three parts.",
     "Hardware Revenue + Platform Commission Revenue + Subscription Revenue"),
    ("Active Customer Count", D_COM, "METRIC", ["Active Customers", "Active Players"],
     "Customers whose account is active (Account Status 'A'); excludes S (suspended) and C (closed). Grain: one row "
     "per customer in CUSTOMER_ACCOUNTS. STATUS here means account status, not game or listing status. Region: "
     "REGION uses SIE Region Codes (North America = 'SIEA', not 'NA'). Count, additive across regions.",
     "COUNT(*) FROM ONTOLOGY_DEMO.GAME_SALES.CUSTOMER_ACCOUNTS WHERE STATUS = 'A'"),
    ("Battle Pass Sales Revenue", D_COM, "METRIC", ["Battle Pass Revenue"],
     "Gross revenue from battle passes actually SOLD: digital purchases whose product's Revenue Type Code is "
     "BATTLE_PASS. Not the same as games tagged with a battle_pass business model in MONETIZATION_TYPES, which is a "
     "tag with no money attached. Grain: one row per digital purchase. Additive.",
     "SUM(t.GROSS_REVENUE) FROM DIGITAL_PRODUCT_TRANSACTIONS t JOIN DIGITAL_PRODUCTS p USING (DIGITAL_PRODUCT_ID) "
     "JOIN REVENUE_TYPES r ON r.CATEGORY_ID = p.CATEGORY_ID WHERE r.MONETIZATION_TYPE = 'BATTLE_PASS'"),
    ("Currently Exclusive Game Count", D_COM, "METRIC", ["Current Exclusives"],
     "Game-platform pairs exclusive today. Grain: one row per game and platform in Sales GAME_PLATFORMS. "
     "IS_EXCLUSIVE is text 'Y'/'N' in Sales (BOOLEAN in Catalog), so compare to 'Y'. Timed exclusives count only "
     "while EXCLUSIVE_END is today or later. Counts pairs, not games.",
     "COUNT(*) FROM ONTOLOGY_DEMO.GAME_SALES.GAME_PLATFORMS WHERE IS_EXCLUSIVE = 'Y' AND (EXCLUSIVITY_TYPE = 'PERMANENT' "
     "OR (EXCLUSIVITY_TYPE = 'TIMED' AND EXCLUSIVE_END >= CURRENT_DATE))"),
    ("Game Revenue", D_CAT, "METRIC", ["Title Revenue", "Revenue per Game"],
     "Revenue per catalog Game. Title per row = COALESCE(t.TITLE_ID, p.TITLE_ID); resolve each title to a Game via "
     "TITLES.CATALOG_GAME_ID, then TITLE_CODE_XREF.CATALOG_GAME_ID, then name + release year (Game Identity Match Rule). "
     "Grain: one row per digital purchase, grouped to a catalog GAME_ID. Gross, additive across games; summed over "
     "all games it equals Digital Gross Revenue. Pitfall: joining on TITLES.CATALOG_GAME_ID alone drops every title "
     "that only the crosswalk or the name + year route can resolve. Find a game by its catalog name or a Sales "
     "alias (see Game).",
     "SUM(t.GROSS_REVENUE) FROM DIGITAL_PRODUCT_TRANSACTIONS t JOIN DIGITAL_PRODUCTS p USING (DIGITAL_PRODUCT_ID) "
     "GROUP BY resolved catalog GAME_ID"),
    ("Developer Revenue", D_CAT, "METRIC", ["Studio Revenue"],
     "Game Revenue per Developer: resolve each sale to a catalog Game first (Game Identity Match Rule), then group "
     "by GAMES.DEVELOPER_NAME. Developer has no table of its own; Sales TITLES.STUDIO is the same studio spelled "
     "with spaces. Gross, additive across developers.",
     "Game Revenue GROUP BY GAMES.DEVELOPER_NAME"),
    ("Franchise Revenue", D_CAT, "METRIC", ["Series Revenue"],
     "Game Revenue per Franchise: resolve each sale to a catalog Game first (Game Identity Match Rule), then group "
     "by franchise name (GAMES.FRANCHISE_NAME or GAME_FRANCHISES.FRANCHISE_NAME). Franchise has no table of its own. "
     "Gross, additive across franchises.",
     "Game Revenue GROUP BY GAME_FRANCHISES.FRANCHISE_NAME"),
    ("Active Catalog Game Count", D_CAT, "METRIC", ["Active Games", "Live Games"],
     "Catalog games that are not delisted (Game Lifecycle Status <> 'DELISTED'). Grain: one row per game in "
     "GAME_CATALOG.GAMES. Use GAMES.STATUS, not the account or listing STATUS columns. Count.",
     "COUNT(*) FROM ONTOLOGY_DEMO.GAME_CATALOG.GAMES WHERE STATUS <> 'DELISTED'"),
    ("Genre Match Score", D_GEN, "METRIC", [],
     "Share of a genre rule's conditions a game meets. A game is a MEMBER of a genre only when MATCH_STATUS = 'FULL' "
     "PARTIAL is not membership. Grain: one row per game and genre. Not additive.",
     "MET_CONDITIONS / TOTAL_CONDITIONS FROM ONTOLOGY_DEMO.GAME_CATALOG.GAME_GENRE_CLASSIFICATION"),
    ("Weighted Overlap", D_GEN, "METRIC", ["Game Similarity"],
     "Similarity between two games (GAME_SIMILARITY_SCORES.WEIGHTED_OVERLAP). Cannibalization candidates: same "
     "Publisher and >= 0.3. Not additive.",
     "SUM(dimension overlap * SIMILARITY_WEIGHTS.WEIGHT)"),

    # ---------------- Phase 4a: identifier and policy terms
    ("Catalog Game ID", D_CAT, "TERM", ["GAME_ID"],
     "Catalog key of a Game: GAME_CATALOG.GAMES.GAME_ID. Also stored as GAME_SALES.TITLES.CATALOG_GAME_ID "
     "(NULL for some titles) and GAME_SALES.TITLE_CODE_XREF.CATALOG_GAME_ID."),
    ("Game Identity Match Rule", D_CAT, "TERM", ["Title to Game Match"],
     "Policy for resolving a Sales title to a catalog Game, in order: (1) strong: TITLES.CATALOG_GAME_ID; "
     "(2) medium: TITLE_CODE_XREF.CATALOG_GAME_ID for the title; (3) weak: accent-folded lower-case name equal AND same "
     "release year (TITLES.RELEASE_DATE is text YYYYMMDD and may be the JP date). Apply all three routes; "
     "skipping (2) and (3) leaves titles unmatched and undercounts revenue."),
    ("Sales Title ID", D_COM, "TERM", ["TITLE_ID"],
     "GAME_SALES.TITLES.TITLE_ID (5001-5090), a Sales-only key that does NOT equal GAME_ID. Used in DIGITAL_PRODUCTS, "
     "Sales GAME_PLATFORMS, Sales GAME_MONETIZATION, DIGITAL_PRODUCT_TRANSACTIONS (NULL for every 10th row) and the "
     "revenue views."),
    ("Title Code", D_COM, "TERM", ["Store Code", "PlayStation Store Code", "CUSA Code", "PPSA Code"],
     "GAME_SALES.TITLE_CODE_XREF.TITLE_CODE, the PlayStation Store code per game and platform. Prefix: PPSA = PS5, "
     "CUSA = PS4, NPUA = PS3, PCSA = PS Vita, SLUS = PS2. PC and Switch releases have no code. 100 codes; 12 games have "
     "more than one. TITLE_CODE_XREF.CATALOG_GAME_ID is the only route to the catalog for some titles."),
    ("SKU Code", D_COM, "TERM", ["Product Code"],
     "GAME_SALES.DIGITAL_PRODUCTS.SKU_CODE, format <TitleCode>-C<CC><SS>: prefix = the game's newest-generation "
     "Title Code, CC = REVENUE_TYPES.CATEGORY_ID (2 digits), SS = sequence within that title and category. "
     "Example PPSA97384-C0301 = Horizon Forbidden West, BASE_GAME_DIGITAL. Decode a SKU by matching its prefix to "
     "TITLE_CODE_XREF.TITLE_CODE and its CC to REVENUE_TYPES.CATEGORY_ID. Some products have no SKU (their game has "
     "no PlayStation code)."),

    # ---------------- Phase 4b: code-mapping terms
    ("Game Lifecycle Status", D_CAT, "TERM", [],
     "GAMES.STATUS: RELEASED, REMASTERED, DELISTED (Concord). Different from Account Status and Listing Status, "
     "which share the column name STATUS."),
    ("Franchise Relationship Type", D_CAT, "TERM", ["Sequel Type"],
     "GAME_FRANCHISES.RELATIONSHIP_TYPE: original, sequel, prequel, spinoff, remake, spiritual_successor. "
     "RELATED_GAME_ID may point to another franchise (Saros -> Returnal, The Inpatient -> Until Dawn)."),
    ("Age Rating System", D_CAT, "TERM", ["ESRB", "PEGI", "CERO"],
     "AGE_RATINGS.RATING_SYSTEM / RATING_VALUE. Approximate equivalents: ESRB E = PEGI 3 = CERO A; ESRB T is about "
     "PEGI 16 / CERO C; ESRB M = PEGI 18 = CERO Z."),
    ("Monetization Model", D_CAT, "TERM", ["Business Model"],
     "MONETIZATION_TYPES.MONETIZATION_NAME (both systems; lower case): premium, free_to_play, microtransactions, "
     "battle_pass, loot_boxes, dlc, subscription, ads, season_pass. A business-model TAG on a game; nothing priced. "
     "LiveService is a business model, not a genre. Do not confuse with Revenue Type Code (same words, what was sold)."),
    ("Platform Code", D_CAT, "TERM", ["Platform Name"],
     "One platform, two naming conventions. Catalog PLATFORMS.PLATFORM_NAME: PS5, PS4, PS3, PS2, PS_Vita, Pc_gaming, "
     "XBOX_ONE, Xbox_Series, Nintendo_Switch... Sales PLATFORMS.PLATFORM_CODE / PLATFORM_NAME: PS5 / PlayStation 5, "
     "PS4 / PlayStation 4, PSV / PlayStation Vita, PC / PC (Steam), NSW / Nintendo Switch... Join on PLATFORM_ID."),
    ("Revenue Type Code", D_COM, "TERM", ["Sold Item Type"],
     "REVENUE_TYPES.MONETIZATION_TYPE (upper case, 13 values): BASE_GAME_DIGITAL, BASE_GAME_PHYSICAL, DLC, EXPANSION, "
     "SEASON_PASS, BATTLE_PASS, COSMETIC_MICROTRANSACTION, CONSUMABLE_MICROTRANSACTION, LOOT_BOX, VIRTUAL_CURRENCY, "
     "HARDWARE_CONSOLE, HARDWARE_PERIPHERAL, SUBSCRIPTION. What was actually SOLD. WARNING: BASE_GAME_PHYSICAL is in "
     "CATEGORY_GROUP 'DIGITAL', so digital by group includes physical editions."),
    ("SIE Region Code", D_COM, "TERM", ["Customer Region"],
     "CUSTOMER_ACCOUNTS.REGION: SIEA = North America, SIEE = Europe, SIEJ = Japan, SIEAP = Asia-Pacific, "
     "SIELA = Latin America."),
    ("Sales Region Code", D_COM, "TERM", ["Hardware Region"],
     "HARDWARE_SALES_TRANSACTIONS.REGION: NA = North America, EU = Europe, JP = Japan, ASIA = Asia-Pacific, "
     "LATAM = Latin America."),
    ("Account Status", D_COM, "TERM", [],
     "CUSTOMER_ACCOUNTS.STATUS: A = active, S = suspended, C = closed. Active customers = 'A' only."),
    ("Listing Status", D_COM, "TERM", [],
     "DIGITAL_PRODUCTS.STATUS: LIVE, DELISTED (store availability of a product)."),
    ("Exclusivity Flag", D_COM, "TERM", [],
     "Sales GAME_PLATFORMS.IS_EXCLUSIVE is text 'Y'/'N' (Catalog uses BOOLEAN). Currently exclusive = PERMANENT, "
     "or TIMED with EXCLUSIVE_END >= today."),
    ("POV Code", D_GEN, "TERM", ["Point of View", "Perspective"],
     "GAMES.POV: 1P = first person, 3P = third person."),
    ("Genre Match Status", D_GEN, "TERM", [],
     "GAME_GENRE_CLASSIFICATION.MATCH_STATUS: FULL = member; PARTIAL, NONE, UNEVALUABLE = not a member."),
    ("Genre Rule", D_GEN, "TERM", ["Genre Definition"],
     "GENRE_RULES is the executable source (used by SP_CLASSIFY_GAMES). RULE_DEFINITION syntax: hasX VALUE v (exact "
     "value), hasX SOME Category (any value in a GENRE_CATEGORY_MAP category), MIN/MAX (player count), NOT(...), "
     "INTERSECTION(...) = AND. PARENT_GENRE is single-parent BY DESIGN: ActionRPG and Soulslike sit under Action, so the strict tree alone finds no RPG members; the ontology links them to RPG. Disjoint pairs: FPS-TPS, MMO-LocalMultiplayer, "
     "Cozy-Horror, Artistic-Realistic, MMO-SinglePlayer. Genres held as values only (no node): DynamicAdventure, "
     "Survival, Explorative, FamiliarExploration, FantasyExploration, InteractiveMovie, Metroidvania, VisualNovel, Gore, "
     "Psychological, SurvivalHorror, Roguelike, Tactic, BattleRoyale, Match, Scrolling, DatingSim, DrivingSim, JobSim, "
     "Management, SandBox, Sport, Artistic, Educational, PuzzleGame, Cozy, Other, LiveService, MultiplayerAvailable, "
     "MMO, LocalMultiplayer, Genre (root)."),
]

# ---------------- Phase 4c: curated genre terms (D7)
MEMBERSHIP = ("Membership: FULL match in GAME_GENRE_CLASSIFICATION; a parent's members are the union of its "
              "descendants (VW_GENRE_HIERARCHY). Source value GENRE_RULES.GENRE = '{v}'.")
GENRES = [
    ("Action", ["action games"], "Top-level. Members = union of Shooter, Fighting, Platformer, Stealth, Survival, "
     "ActionRPG, DynamicAdventure and their subgenres."),
    ("Adventure", ["adventure games"], "Top-level. Includes Explorative, InteractiveMovie, Metroidvania, VisualNovel."),
    ("RPG", ["role-playing game", "roleplaying game"], "Top-level. Members = RPG + Roguelike + ActionRPG + Soulslike. "
     "ActionRPG and Soulslike sit under Action in GENRE_RULES; always include them. Count distinct games."),
    ("Horror", ["horror games"], "Top-level. Includes Gore, Psychological, SurvivalHorror. Disjoint with Cozy."),
    ("Simulator", ["sim", "simulation game"], "Top-level. Includes DatingSim, DrivingSim, JobSim, Management, SandBox, "
     "Sport. Most sim rules are unmet by the data."),
    ("Strategic", ["strategy", "strategy game"], "Top-level leaf."),
    ("Shooter", ["shooter games", "gunplay"], "Parent Action. Rule hasGameplay VALUE free_shooting. Variants "
     "FPS and TPS (axis: point of view)."),
    ("FPS", ["first-person shooter", "first person shooter"], "Variant of Shooter with POV 1P. Disjoint with TPS. "
     "Use GENRE = 'FPS'; 'first-person shooter' is not a stored value."),
    ("TPS", ["third-person shooter", "third person shooter"], "Variant of Shooter with POV 3P."),
    ("ActionRPG", ["action RPG", "ARPG"], "Parent Action; also an RPG."),
    ("Soulslike", ["Soulsborne", "souls-like"], "Parent ActionRPG; also an RPG. Its rule needs melee_combat and "
     "a difficulty attribute that do not exist in the data, so it has no FULL matches."),
    ("Fighting", ["fighter", "versus fighting"], "Parent Action. Includes Match, Scrolling."),
    ("Platformer", ["platform game", "platforming"], "Parent Action. Not the Platform entity."),
    ("Stealth", ["stealth action"], "Parent Action."),
]
for name, syns, desc in GENRES:
    TERMS.append((name, D_GEN, "TERM", syns, f"Genre. {desc} {MEMBERSHIP.format(v=name)}"))

# ---------------- Phase 5: relationships (source, type, target)
REL = []
def r(src, typ, *targets):
    for t in targets:
        REL.append((src, t, typ))

# identity
r("Game", "IDENTIFIED_BY", "Catalog Game ID", "Sales Title ID", "Title Code")
r("Digital Product", "IDENTIFIED_BY", "SKU Code")
r("SKU Code", "RELATED_TO", "Title Code")
r("Game Identity Match Rule", "APPLIES_TO", "Game", "Game Revenue")
r("Platform Code", "CLASSIFIES", "Platform")
# catalog
r("Franchise", "HAS_PART", "Game")
r("Game", "HAS_PART", "Game Mode")
r("Developer", "RELATED_TO", "Game")
r("Publisher", "RELATED_TO", "Franchise", "Developer")
r("Engine", "RELATED_TO", "Game")
r("Platform", "RELATED_TO", "Game")
r("Age Rating", "CLASSIFIES", "Game")
r("Age Rating System", "CLASSIFIES", "Age Rating")
r("Game Lifecycle Status", "CLASSIFIES", "Game")
r("Franchise Relationship Type", "CLASSIFIES", "Game")
# commerce
r("Game", "RELATED_TO", "Digital Product")
r("Platform", "RELATED_TO", "Customer", "Hardware Product")
r("Customer", "RELATED_TO", "Digital Transaction", "Hardware Sale", "Subscription Charge")
r("Digital Product", "RELATED_TO", "Digital Transaction")
r("Hardware Product", "RELATED_TO", "Hardware Sale")
r("Subscription Plan", "RELATED_TO", "Subscription Charge")
r("Revenue Type", "CLASSIFIES", "Digital Product")
r("Revenue Type Code", "CLASSIFIES", "Revenue Type")
r("Account Status", "CLASSIFIES", "Customer")
r("Listing Status", "CLASSIFIES", "Digital Product")
r("SIE Region Code", "CLASSIFIES", "Customer")
r("Sales Region Code", "CLASSIFIES", "Hardware Sale")
r("SIE Region Code", "EQUIVALENT_TO", "Sales Region Code")
r("Monetization Model", "RELATED_TO", "Revenue Type Code")
# genre
r("Feature Category", "CLASSIFIES", "Gameplay Type", "Mechanic", "Context")
for f in ("Gameplay Type", "Mechanic", "Context", "Narrative Structure", "POV Code", "Genre"):
    r(f, "CLASSIFIES", "Game")
r("Genre Rule", "APPLIES_TO", "Genre")
r("Genre Match Status", "APPLIES_TO", "Genre")
for g, _, _ in GENRES:
    r(g, "CLASSIFIES", "Game")
r("Shooter", "HAS_VARIANT", "FPS", "TPS")
r("Genre", "RELATED_TO", "Action", "Adventure", "RPG", "Horror", "Simulator", "Strategic")
r("Action", "RELATED_TO", "Shooter", "Fighting", "Platformer", "Stealth", "ActionRPG")
r("ActionRPG", "RELATED_TO", "Soulslike", "RPG")
r("Soulslike", "RELATED_TO", "RPG")
# metric lineage
r("Digital Gross Revenue", "DERIVES", "Net Publisher Revenue", "Platform Commission Revenue", "Game Revenue")
r("Game Revenue", "DERIVES", "Developer Revenue", "Franchise Revenue")
for m in ("Hardware Revenue", "Platform Commission Revenue", "Subscription Revenue"):
    r(m, "DERIVES", "Total Platform Revenue")
r("Game Revenue", "MEASURES", "Game")
r("Active Customer Count", "MEASURES", "Customer")
r("Active Catalog Game Count", "MEASURES", "Game")
r("Battle Pass Sales Revenue", "MEASURES", "Digital Product")
r("Genre Match Score", "MEASURES", "Genre")
r("Weighted Overlap", "MEASURES", "Game")
r("Account Status", "APPLIES_TO", "Active Customer Count")
r("Game Lifecycle Status", "APPLIES_TO", "Active Catalog Game Count")

# ---------------- Phase 7: representations (term, schema-qualified object, column or None)
def T(fqn):
    return {"refType": "TABLE", "fqn": fqn, "objectName": fqn.split(".")[-1]}
def V(fqn):
    return {"refType": "VIEW", "fqn": fqn, "objectName": fqn.split(".")[-1]}
def C(fqn, col):
    return {"refType": "COLUMN", "fqn": fqn, "dimensionName": col}

REP = [
    ("Game", T(f"{CAT}.GAMES")), ("Game", T(f"{SAL}.TITLES")), ("Game", T(f"{SAL}.TITLE_CODE_XREF")),
    ("Platform", T(f"{CAT}.PLATFORMS")), ("Platform", T(f"{SAL}.PLATFORMS")),
    ("Developer", C(f"{CAT}.GAMES", "DEVELOPER_NAME")), ("Developer", C(f"{CAT}.STUDIO_ACQUISITIONS", "STUDIO_NAME")),
    ("Developer", C(f"{SAL}.TITLES", "STUDIO")),
    ("Publisher", C(f"{CAT}.GAMES", "PUBLISHER_NAME")), ("Publisher", C(f"{CAT}.GAME_FRANCHISES", "PUBLISHER_ID")),
    ("Publisher", C(f"{SAL}.TITLES", "PUBLISHER_LABEL")), ("Publisher", C(f"{SAL}.HARDWARE_PRODUCTS", "MANUFACTURER")),
    ("Customer", T(f"{SAL}.CUSTOMER_ACCOUNTS")), ("Customer", C(f"{SAL}.DIGITAL_PRODUCT_TRANSACTIONS", "PLAYER_ID")),
    ("Customer", C(f"{SAL}.SUBSCRIPTION_CHARGES", "SUBSCRIBER_ID")),
    ("Customer", C(f"{SAL}.HARDWARE_SALES_TRANSACTIONS", "BUYER_ID")),
    ("Franchise", T(f"{CAT}.GAME_FRANCHISES")), ("Franchise", C(f"{CAT}.GAMES", "FRANCHISE_NAME")),
    ("Engine", T(f"{CAT}.ENGINES")), ("Game Mode", T(f"{CAT}.GAME_MODES")), ("Age Rating", T(f"{CAT}.AGE_RATINGS")),
    ("Genre", T(f"{CAT}.GENRE_RULES")), ("Genre", V(f"{CAT}.VW_GENRE_HIERARCHY")),
    ("Genre", T(f"{CAT}.GAME_GENRE_CLASSIFICATION")),
    ("Feature Category", T(f"{CAT}.GENRE_CATEGORY_MAP")), ("Gameplay Type", T(f"{CAT}.GAMEPLAY_TYPES")),
    ("Mechanic", T(f"{CAT}.MECHANICS")), ("Context", T(f"{CAT}.CONTEXTS")),
    ("Narrative Structure", T(f"{CAT}.NARRATIVE_STRUCTURES")),
    ("Digital Product", T(f"{SAL}.DIGITAL_PRODUCTS")), ("Hardware Product", T(f"{SAL}.HARDWARE_PRODUCTS")),
    ("Subscription Plan", T(f"{SAL}.SUBSCRIPTION_PLANS")),
    ("Digital Transaction", T(f"{SAL}.DIGITAL_PRODUCT_TRANSACTIONS")),
    ("Hardware Sale", T(f"{SAL}.HARDWARE_SALES_TRANSACTIONS")),
    ("Subscription Charge", T(f"{SAL}.SUBSCRIPTION_CHARGES")), ("Revenue Type", T(f"{SAL}.REVENUE_TYPES")),
    # terms -> columns
    ("Catalog Game ID", C(f"{CAT}.GAMES", "GAME_ID")), ("Catalog Game ID", C(f"{SAL}.TITLES", "CATALOG_GAME_ID")),
    ("Catalog Game ID", C(f"{SAL}.TITLE_CODE_XREF", "CATALOG_GAME_ID")),
    ("Sales Title ID", C(f"{SAL}.TITLES", "TITLE_ID")),
    ("Title Code", C(f"{SAL}.TITLE_CODE_XREF", "TITLE_CODE")),
    ("SKU Code", C(f"{SAL}.DIGITAL_PRODUCTS", "SKU_CODE")),
    ("Game Identity Match Rule", C(f"{SAL}.TITLES", "CATALOG_GAME_ID")),
    ("Game Identity Match Rule", C(f"{SAL}.TITLE_CODE_XREF", "CATALOG_GAME_ID")),
    ("Game Lifecycle Status", C(f"{CAT}.GAMES", "STATUS")),
    ("Franchise Relationship Type", C(f"{CAT}.GAME_FRANCHISES", "RELATIONSHIP_TYPE")),
    ("Age Rating System", C(f"{CAT}.AGE_RATINGS", "RATING_SYSTEM")),
    ("Monetization Model", C(f"{CAT}.MONETIZATION_TYPES", "MONETIZATION_NAME")),
    ("Monetization Model", C(f"{SAL}.MONETIZATION_TYPES", "MONETIZATION_NAME")),
    ("Platform Code", C(f"{CAT}.PLATFORMS", "PLATFORM_NAME")), ("Platform Code", C(f"{SAL}.PLATFORMS", "PLATFORM_CODE")),
    ("Platform Code", C(f"{SAL}.PLATFORMS", "PLATFORM_NAME")),
    ("Revenue Type Code", C(f"{SAL}.REVENUE_TYPES", "MONETIZATION_TYPE")),
    ("SIE Region Code", C(f"{SAL}.CUSTOMER_ACCOUNTS", "REGION")),
    ("Sales Region Code", C(f"{SAL}.HARDWARE_SALES_TRANSACTIONS", "REGION")),
    ("Account Status", C(f"{SAL}.CUSTOMER_ACCOUNTS", "STATUS")),
    ("Listing Status", C(f"{SAL}.DIGITAL_PRODUCTS", "STATUS")),
    ("Exclusivity Flag", C(f"{SAL}.GAME_PLATFORMS", "IS_EXCLUSIVE")),
    ("POV Code", C(f"{CAT}.GAMES", "POV")),
    ("Genre Match Status", C(f"{CAT}.GAME_GENRE_CLASSIFICATION", "MATCH_STATUS")),
    ("Genre Rule", C(f"{CAT}.GENRE_RULES", "RULE_DEFINITION")),
] + [(g, C(f"{CAT}.GENRE_RULES", "GENRE")) for g, _, _ in GENRES]

# Metric representations: the column each metric measures (D17 follow-up).
DPT, HST, SCH = f"{SAL}.DIGITAL_PRODUCT_TRANSACTIONS", f"{SAL}.HARDWARE_SALES_TRANSACTIONS", f"{SAL}.SUBSCRIPTION_CHARGES"
METRIC_REP = [
    ("Digital Gross Revenue", C(DPT, "GROSS_REVENUE")),
    ("Net Publisher Revenue", C(DPT, "NET_DEVELOPER_REVENUE")),
    ("Platform Commission Revenue", C(DPT, "PLATFORM_COMMISSION_PCT")),
    ("Hardware Revenue", C(HST, "GROSS_REVENUE")),
    ("Subscription Revenue", C(SCH, "GROSS_REVENUE")),
    ("Total Platform Revenue", T(HST)), ("Total Platform Revenue", T(DPT)), ("Total Platform Revenue", T(SCH)),
    ("Active Customer Count", C(f"{SAL}.CUSTOMER_ACCOUNTS", "STATUS")),
    ("Battle Pass Sales Revenue", C(DPT, "GROSS_REVENUE")),
    ("Currently Exclusive Game Count", C(f"{SAL}.GAME_PLATFORMS", "IS_EXCLUSIVE")),
    ("Game Revenue", C(DPT, "GROSS_REVENUE")),
    ("Developer Revenue", C(f"{CAT}.GAMES", "DEVELOPER_NAME")),
    ("Franchise Revenue", C(f"{CAT}.GAMES", "FRANCHISE_NAME")),
    ("Active Catalog Game Count", C(f"{CAT}.GAMES", "STATUS")),
    ("Genre Match Score", C(f"{CAT}.GAME_GENRE_CLASSIFICATION", "MATCH_STATUS")),
    ("Weighted Overlap", C(f"{CAT}.GAME_SIMILARITY_SCORES", "WEIGHTED_OVERLAP")),
]

# D17: no eval answers or trap values in ontology text. Values from ontology_eval_set.md.
FORBIDDEN = [
    "19,231,852", "17,312,180", "15,861,443", "899,999", "198,000", "3,419,553", "2,919,819", "3,428,553",
    "96,773", "289,225", "38,699", "70,243,201", "150,389", "19,119,344", "211,407,934", "230,527,279",
    "203,000", "175,660,810", "35,634,616", "112,507", "7,881,147", "1,612,478", "CUSA86252",
]
FORBIDDEN_WORDS = ["Correct:", "Wrong ("]
FORBIDDEN_COUNTS = [" 43 ", " 10 games", " 53", " 89 ", " 87 ", " 351", " games:", " 0 games"]


def check_leaks(name, text):
    flat = text.replace(",", "")
    for v in FORBIDDEN:
        assert v not in text and v.replace(",", "") not in flat, f"{name}: leaks {v}"
    for w in FORBIDDEN_WORDS + FORBIDDEN_COUNTS:
        assert w not in text, f"{name}: contains {w!r}"


def lit(s):
    """Escape once for a SQL single-quoted literal."""
    return "'" + s.replace("\\", "\\\\").replace("'", "''") + "'"


def main():
    names = [t[0] for t in TERMS]
    assert len(names) == len(set(names)), "duplicate term names"
    syns = [s.lower() for t in TERMS for s in t[3]]
    assert len(syns) == len(set(syns)), "a synonym appears on more than one node"
    for s, t, _ in REL:
        assert s in names and t in names, f"unknown endpoint {s} -> {t}"
    for term, _ in REP + METRIC_REP:
        assert term in names, f"unknown representation term {term}"
    for t in TERMS:
        check_leaks(t[0], t[4])
    for name, desc in DOMAINS:
        check_leaks(name, desc)

    lines = ["-- Generated by build_ontology.py. Phases 1-4: domains, then draft + approve every term."]
    for name, desc in DOMAINS:
        lines.append(f"SELECT SYSTEM$CREATE_GLOSSARY_DOMAIN({lit(name)}, {lit(desc)});")
    for t in TERMS:
        name, domain, kind, synonyms, desc = t[:5]
        payload = {"name": name, "domainName": domain, "itemKind": kind, "description": desc}
        if synonyms:
            payload["synonyms"] = synonyms
        if kind == "METRIC":
            payload["formula"] = t[5]
        lines.append(f"SELECT SYSTEM$DRAFT_GLOSSARY_TERM({lit(json.dumps(payload, ensure_ascii=False))});")
    for name in names:
        lines.append(f"SELECT SYSTEM$APPROVE_GLOSSARY_TERM({lit(name)});")
    (OUT / "01_domains_terms.sql").write_text("\n".join(lines) + "\n")

    rel_lines = ["-- Generated by build_ontology.py. Phase 5: direct ACTIVE relationships."]
    rel_lines += [f"SELECT SYSTEM$CREATE_GLOSSARY_RELATIONSHIP({lit(s)}, {lit(t)}, {lit(typ)});" for s, t, typ in REL]
    (OUT / "02_relationships.sql").write_text("\n".join(rel_lines) + "\n")

    rep_lines = ["-- Generated by build_ontology.py. Phase 7: representations."]
    rep_lines += [f"SELECT SYSTEM$CREATE_GLOSSARY_ASSOCIATION({lit(term)}, {lit(json.dumps(ref))}, 'DESCRIBES');"
                  for term, ref in REP]
    (OUT / "03_representations.sql").write_text("\n".join(rep_lines) + "\n")

    upd = ["-- Generated by build_ontology.py. D17: rewrite descriptions in place (no answers in ontology text)."]
    for t in TERMS:
        patch = {"description": t[4]}
        if t[2] == "METRIC":
            patch["formula"] = t[5]
        upd.append(f"SELECT SYSTEM$UPDATE_GLOSSARY_TERM({lit(t[0])}, {lit(json.dumps(patch, ensure_ascii=False))});")
    (OUT / "04_update_descriptions.sql").write_text("\n".join(upd) + "\n")

    mrep = ["-- Generated by build_ontology.py. Metric representations."]
    mrep += [f"SELECT SYSTEM$CREATE_GLOSSARY_ASSOCIATION({lit(term)}, {lit(json.dumps(ref))}, 'DESCRIBES');"
             for term, ref in METRIC_REP]
    (OUT / "05_metric_representations.sql").write_text("\n".join(mrep) + "\n")

    kinds = {k: sum(1 for t in TERMS if t[2] == k) for k in ("ENTITY", "METRIC", "TERM")}
    print(f"domains={len(DOMAINS)} terms={len(TERMS)} {kinds} relationships={len(REL)} representations={len(REP) + len(METRIC_REP)}")


if __name__ == "__main__":
    main()
