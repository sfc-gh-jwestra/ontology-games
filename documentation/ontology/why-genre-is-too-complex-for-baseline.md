# Genres: hierarchy, roll-up and revenue

Genre helps answer important game classification questions, and the hardest place for a text-to-SQL agent to get right. The genre data is all there. What the tables don't say is how a genre question should be read: which rows count, how genres roll up, and how a sale links to a game. The semantic view gives the agent column names and join paths, not those rules, so the baseline agent writes SQL that runs cleanly and returns a believable wrong number.

This affects eval questions 4 and 7-9 in [ontology_eval_set.md](ontology_eval_set.md), all tagged C7 (genre) in [README_ontology_games_challenges.md](README_ontology_games_challenges.md).

## How genre is stored

| Object | What it holds |
|---|---|
| `GAME_CATALOG.GENRE_RULES` | 46 genres, each with a single `PARENT_GENRE`, a `RULE_DEFINITION` and `DISJOINT_WITH` |
| `GAME_CATALOG.VW_GENRE_HIERARCHY` | The tree from `GENRE_RULES`: depth, path, leaf flag |
| `GAME_CATALOG.GAME_GENRE_CLASSIFICATION` | One row per game and genre: `MATCH_STATUS` is `FULL`, `PARTIAL`, `NONE` or `UNEVALUABLE` |
| `GAME_CATALOG.VW_GAME_GENRE_ROLLUP` | One row per game per genre it belongs to: each `FULL` genre plus all its ancestors (`GAME_ID`, `ROLLUP_GENRE`, `ROLLUP_DEPTH`; depth 1 = top-level). Distinct per game and genre, so a game counts once per genre. Strict tree only. |

`VW_GAME_GENRE_ROLLUP` is the logical table `GENRE_ROLLUP` in `GAME_CATALOG.SV_GENRE_TAXONOMY`, joined to `GAMES` on `GAME_ID`. `SV_GAMING_CROSS_DOMAIN` imports it, so both demo agents can query it. Neither agent gets data the other can't see; the only difference is the ontology.

## The four traps

### 1. Every genre question first has to resolve each sale to a catalog game

Genre lives only in the catalog, so each Sales title has to be matched to a catalog game. The only title-to-game join in `SV_GAMING_CROSS_DOMAIN` is the catalog ID on the Sales title (`TITLES.CATALOG_GAME_ID`). Titles that match only through the store-code crosswalk (`TITLE_CODE_XREF`), or only by name and release year (Ghost of Yōtei), are dropped. Even when the genre logic is right, revenue comes out low:

| Question | Expected | Catalog-ID join only |
|---|---|---|
| Q7 Action | $14,642,492.04 | $13,217,013.28 |
| Q8 RPG | $13,436,693.28 | $12,278,693.28 |

Fix: the **Game Identity Match Rule** (catalog ID, then crosswalk, then name + year). Only the ontology has it; title-to-game matching was deliberately not added to the semantic view.

### 2. Parent genres have no rows of their own, and the business tree differs from the data tree

Only rules that match game features produce `FULL` rows, so `GROUP BY GENRE` on `GAME_GENRE_CLASSIFICATION` returns leaf and mid-level genres and Action never appears. A parent genre's members are the union of its descendants' members, which is what `GENRE_ROLLUP` computes. Checked on 2026-10-14:

| Genre | Parent | Depth | Leaf | FULL rows |
|---|---|---|---|---|
| Action | Genre | 1 | no | 0 |
| Adventure | Genre | 1 | no | 0 |
| Horror | Genre | 1 | no | 0 |
| RPG | Genre | 1 | no | 0 |
| Simulator | Genre | 1 | no | 0 |
| Strategic | Genre | 1 | yes | 18 |
| ActionRPG | Action | 2 | no | 43 |
| Shooter | Action | 2 | no | 30 |
| FPS | Shooter | 3 | yes | 10 |

These counts are diagnostic only. Per D17 they must not go into ontology text.

The tree is single-parent, and that is deliberate (decision D9, never to be "fixed" in the data):

- In `GENRE_RULES`, ActionRPG's parent is Action, Soulslike's is ActionRPG, and Roguelike's is RPG.
- So `ROLLUP_GENRE = 'RPG'` returns **0 games**, and a baseline that follows the tree reports $0 for Q8.
- The business counts ActionRPG and Soulslike games as RPGs too. That family has **43 games**.
- Nothing in the tables says that. Only the ontology's **RPG** term and **Genre Roll-up Rule** do: RPG = `ROLLUP_GENRE IN ('RPG', 'Roguelike', 'ActionRPG', 'Soulslike')`, counted with `COUNT(DISTINCT GAME_ID)`.

### 3. Genre names and match quality need interpreting

- **Synonyms (Q4):** "first-person shooter" is not a value in the data; it's stored as `FPS`. The baseline may sum all shooters instead, or find nothing. The ontology's **FPS** term carries the synonym.
- **Match quality:** only `FULL` means the game is in that genre. Without that rule the agent may count partial matches, or every game that was evaluated.

### 4. Genre totals are not additive (Q7, Q9)

A game counts in every genre it belongs to; an ActionRPG game counts under ActionRPG, Action and RPG. The baseline tends to either:

- group by the genre the game was classified into directly (Q7 then reports ActionRPG instead of Action), or
- add the subgenres together and report about $30.6M for Action, more than total revenue ($19,231,852.01).

The ontology's **Genre Revenue** metric says these totals overlap and must never be summed.

## What the ontology adds

All in the Genre Taxonomy domain (`scripts/build_ontology.py`):

| Node | Kind | What it tells the agent |
|---|---|---|
| **Genre** | Class | Where genre lives, `FULL`-only membership, and to use `GENRE_ROLLUP.ROLLUP_GENRE` for any parent or top-level genre |
| **Genre Roll-up Rule** | Rule | Use `ROLLUP_GENRE`, never `GENRE_CLASSIFICATION.GENRE`, for parents; add RPG members by hand; per-genre totals overlap; "which genre" means top-level (`ROLLUP_DEPTH = 1`, plus RPG) |
| **Genre Revenue** | Metric | Game Revenue joined to `GENRE_ROLLUP` and grouped by `ROLLUP_GENRE`; gross; not additive. Resolves each sale with the Game Identity Match Rule first |
| 14 curated genre terms | Term | 6 top-level (Action, Adventure, RPG, Horror, Simulator, Strategic) and 8 subgenres, with synonyms (FPS = first-person shooter) and their roll-up query. The other 32 genres stay as values in `GENRE_RULES`, listed in the Genre Rule term (D7) |

Relationships: Game Revenue `DERIVES` Genre Revenue; Genre Revenue `MEASURES` Genre; Genre Roll-up Rule `APPLIES_TO` Genre and Genre Revenue; Game Identity Match Rule `APPLIES_TO` Genre Revenue; Shooter `HAS_VARIANT` FPS and TPS (one point-of-view axis). Every other genre-to-genre edge is `RELATED_TO`, read as "subgenre of" (D8): Genre to the 6 top-level genres; Action to Shooter, Fighting, Platformer, Stealth and ActionRPG; ActionRPG to Soulslike; and the cross-tree "also an RPG" links ActionRPG and Soulslike to RPG.

## History

- **Before 2026-10-14:** asked for revenue per genre, agents returned only leaf and mid-level genres. The roll-up rule existed only as prose pointing at `VW_GENRE_HIERARCHY`, which no semantic view exposed, so the agent knew the rule but had nothing to run it against.
- **2026-10-14:** built `VW_GAME_GENRE_ROLLUP` and added it to the semantic view (now `SV_GENRE_TAXONOMY`); added the Genre Roll-up Rule and Genre Revenue nodes with their relationships and representations; pointed the Genre description and the 14 genre terms at `GENRE_ROLLUP`; added the genre eval questions (now Q7-Q9).
- **Decisions made then:** the view follows the strict tree (D9 is not applied in it, so RPG stays a with/without-ontology test); a `LEAF_GENRE` column was dropped because it would duplicate rows and double-count revenue; Genre Revenue is gross; title-to-game matching stays ontology-only.

## Open items

- **Parent/child edges.** The subgenre links are `RELATED_TO`, which is symmetric and carries no direction. Snowflake's [Business Ontology relationships](https://docs.snowflake.com/en/LIMITEDACCESS/snowflake-horizon/business-ontology-relationships) guidance says `RELATED_TO` should be used sparingly and that a subtype link should be a `CUSTOM` relationship with an explicit label (for example "is a subgenre of"). The project chose not to use `CUSTOM` (D8). Changing it would mean editing `build_ontology.py`, rebuilding (install 04b), waiting for the search index, and re-running the batch eval.
- **Value-only genres.** 32 of the 46 genres (Survival, DynamicAdventure and others) aren't ontology nodes, so the full descendant set can't be rebuilt from the graph alone. `GENRE_ROLLUP` covers this for queries.
- **Net genre revenue.** Only a gross Genre Revenue metric exists.
