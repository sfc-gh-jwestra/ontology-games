# Design issue: genre hierarchy and "revenue per genre"

Status: **implemented 2026-10-14**. Original proposal kept below for history.

What was built (plan `genre-hierarchy-revenue-support`):

- `GAME_CATALOG.VW_GAME_GENRE_ROLLUP` (GAME_ID, ROLLUP_GENRE, ROLLUP_DEPTH): strict tree, DISTINCT per (game, genre). `LEAF_GENRE` was dropped because it would duplicate rows and double-count revenue.
- `GAMING_BASELINE_SV`: logical table `GENRE_ROLLUP` + relationship `GENRE_ROLLUP_GAME`.
- Ontology: new TERM **Genre Roll-up Rule** and METRIC **Genre Revenue**, 5 relationships and 4 representations, all ACTIVE (`build/06_genre_rollup.sql`).
- Open question answers:
  - Edges stay `RELATED_TO`; `CUSTOM` was not used.
  - D9 is not applied in the view.
  - Genre Revenue uses gross revenue.
  - Title-to-game matching stays ontology-only; nothing was added to the SV.
- Eval questions 21-23 added to `ontology_eval_set.md`.
- **Description edits:** Genre and the 14 genre terms now point at GENRE_ROLLUP. They were applied with live `SYSTEM$UPDATE_GLOSSARY_TERM`, because `SYSTEM$DRAFT_GLOSSARY_TERM_UPDATE` (edit cards) returns `Unsupported feature` in this account. Using live UPDATE was the user's decision.

The file covers:

1. where the genre hierarchy view is referenced and why the agent can't use any of it
2. the parent-genre row counts I checked today
3. the proposed fix: a roll-up view in the shared semantic view, two new ontology nodes, parent/child edges, full descendant lists and a new eval question
4. three open questions for review

## Problem

Asked for "revenue per genre", an agent returns leaf and mid-level genres only. Parent genres such as Action and RPG never appear as rows.

The governed rule says a parent genre's members are the union of all its descendants' members, computed with the genre hierarchy view (`GAME_CATALOG.VW_GENRE_HIERARCHY`). That view is not a data source the agent can query. Action alone would include ActionRPG, DynamicAdventure, Shooter, Stealth and more, so it would almost certainly rank first overall.

## Where the genre hierarchy view is referenced

| Place | What it says | Can the agent's SQL tool use it? |
|---|---|---|
| **Genre** entity description (`build/build_ontology.py`, Genre entry) | "...GENRE_RULES (single parent PARENT_GENRE...) and VW_GENRE_HIERARCHY (depth, path, leaf)... A parent genre's members are the union of its descendants' members." | No. It is prose. |
| All **14 genre terms**, through the shared `MEMBERSHIP` text in `build_ontology.py` | "a parent's members are the union of its descendants (VW_GENRE_HIERARCHY)" | No. It is prose. |
| **Genre** representation (`REP` in `build_ontology.py`) | Links the Genre entity to the view `VW_GENRE_HIERARCHY` | No. It is catalog metadata, not something the SQL tool can query. |
| Genre-to-genre relationships | Genre `RELATED_TO` the 6 top-level genres; Action `RELATED_TO` Shooter, Fighting, Platformer, Stealth and ActionRPG; ActionRPG `RELATED_TO` RPG; Shooter `HAS_VARIANT` FPS / TPS | Only partly. `RELATED_TO` carries no parent/child direction, and only 14 of the 46 genres are nodes. Survival, DynamicAdventure and the other value-only genres are missing from the graph, so Action's full set of descendants can't be rebuilt from the ontology. |
| Semantic view `yamls/gaming_baseline_sv.yaml` | Has only `GENRE_CLASSIFICATION` (`GAME_GENRE_CLASSIFICATION`), with no hierarchy view or `GENRE_RULES` | This is the only thing the SQL tool sees. |
| Docs | `business_ontology_phases.md` (Genre prompt, the genre roll-up reference, the representations list) and `ontology-overview.md` §3 | Documentation only. |

## Why it fails

1. **The SQL tool can only query semantic-view tables.** The ontology tells the agent "parent = union of descendants via VW_GENRE_HIERARCHY", but that view isn't in the semantic view. The agent knows the rule and has nothing to execute it against.
2. **Parent genres have no rows of their own.** Only rules that match game features produce FULL rows, so `GROUP BY GENRE` returns leaf and mid-level genres and Action never appears. Checked on 2026-10-14:

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

   (These counts are diagnostic only. Per D17 they must not go into ontology text.)
3. **The ontology states the rule in prose and only partly in structure.** The graph has no parent/child edge type, and it has no node for 32 of the genres. The agent can't walk the hierarchy from the ontology either.
4. **Totals can't simply be summed.** One game belongs to several genres; ActionRPG games, for example, count under Action, ActionRPG and RPG. Nothing in the ontology warns that genre revenue doesn't add up to total revenue.

## Proposed fix

### 1. Data: one queryable roll-up object

- Create `GAME_CATALOG.VW_GAME_GENRE_ROLLUP` with one row per (GAME_ID, ROLLUP_GENRE).
- Build it from FULL rows in `GAME_GENRE_CLASSIFICATION`, joined to every ancestor in `VW_GENRE_HIERARCHY`, including the genre itself. An ActionRPG game gets rows for ActionRPG and Action.
- Columns: `GAME_ID`, `ROLLUP_GENRE`, `LEAF_GENRE`, `DEPTH`. Take distinct (GAME_ID, ROLLUP_GENRE) pairs so a game is counted once per genre.
- Follow the **strict single-parent tree only**. RPG still rolls up to 0, so D9 and eval question 13 stay valid tests; only the ontology knows "ActionRPG is also an RPG".
- Add it to `yamls/gaming_baseline_sv.yaml` as `GENRE_ROLLUP`, joined to `GAMES` on `GAME_ID`, and redeploy with `yamls/deploy_yamls.py`.
- Both agents share this semantic view. That keeps the comparison fair, because neither agent gets data the other can't see.

### 2. Ontology: make the hierarchy explicit

- **Genre roll-up rule** (new TERM, Genre Taxonomy):
  - "Revenue or a count for a parent genre = use GENRE_ROLLUP.ROLLUP_GENRE, never GENRE_CLASSIFICATION.GENRE."
  - "RPG = the RPG roll-up plus ActionRPG and Soulslike."
  - "A game counts once per genre, so genre totals overlap and are not additive."
- **Genre Revenue** (new METRIC, Genre Taxonomy):
  - Formula: Game Revenue grouped by GENRE_ROLLUP.ROLLUP_GENRE, counting each game once per genre.
  - Representation on `VW_GAME_GENRE_ROLLUP`.
  - Relationships: Game Revenue `DERIVES` Genre Revenue; Genre Revenue `MEASURES` Genre; Genre roll-up rule `APPLIES_TO` Genre Revenue.
- **Parent/child edges:** change the 6 + 5 genre-to-genre `RELATED_TO` edges to `CUSTOM` with the label `parent_of`. Keep ActionRPG / Soulslike → RPG as `RELATED_TO`, the cross-tree "also an RPG" link. Check first that the CUSTOM label persists (invariant I6: read back).
- **Top-level genre descriptions:** list every descendant value, including the value-only genres. For example, Action = Shooter, FPS, TPS, Fighting, Match, Scrolling, Platformer, Stealth, Survival, ActionRPG, Soulslike, DynamicAdventure. Generate these lists from `VW_GENRE_HIERARCHY` rather than typing them, so they can't drift.
- **Genre entity and `MEMBERSHIP` text:** point to the queryable `GENRE_ROLLUP` instead of the view.
- **Leak guard:** add the Genre Revenue answers to `FORBIDDEN` in `build_ontology.py` once they're computed.
- Apply with `SYSTEM$UPDATE_GLOSSARY_TERM` (description edits) plus new draft, approve and relationship calls. Read everything back.

### 3. Eval set

- Add the question "Which genre has the most revenue?" to `ontology_eval_set.md`, with the expected answer computed from the roll-up.
  - Trap: ranking leaf genres only, so Action is missing.
  - Nodes that fix it: Genre roll-up rule, Genre Revenue.
- Optionally add "How much revenue did RPG games make?". That question combines the roll-up with the D9 cross-tree rule.

## Scope

- 1 new view.
- The semantic view YAML is edited and redeployed.
- 2 new ontology nodes.
- About 11 edge changes and about 6 description updates.
- 1 or 2 new eval questions.

## Open questions

- Is the `CUSTOM` `parent_of` label supported and searchable in this account, or should the edges stay `RELATED_TO` with direction stated in the descriptions?
- Should the roll-up apply D9 inside the view (RPG includes ActionRPG)? That would remove the with/without-ontology difference for RPG, which is why the proposal says no.
- Should genre revenue use gross revenue (Game Revenue), or should a net variant be added?
