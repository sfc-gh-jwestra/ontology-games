# Genre hierarchy and "which genre has the most revenue"

## Context

### How ~/Projects/gaming answers it
- No semantic view has both genre and revenue. `GAMES_ROUTER_AGENT` (`agent/GAMES_ROUTER_AGENT.sql:13`) says to call both sub-agents "and combine the results", so the language model joins genre to revenue in its head (`requirements/questions.md:460` calls it "the cross-domain join problem").
- `GENRE_RULES.PARENT_GENRES` (JSON array) is stored but never read: no recursive CTE, ancestor table or hierarchy view, and `SP_CLASSIFY_GAMES` ignores parents.
- Result: rankings cover only directly-matched genres, with full revenue credited to every FULL genre. Parent genres never appear. It is not a reference for hierarchy correctness.

### What's different here
- `GENRE_RULES.PARENT_GENRE` is single-parent and `VW_GENRE_HIERARCHY` walks it recursively, but `GAMING_BASELINE_SV` includes only the flat `GAME_GENRE_CLASSIFICATION`, so neither agent's SQL can roll up. Parent genres have 0 FULL rows.
- Revenue goes through the title -> game identity traps (strong CATALOG_GAME_ID, medium TITLE_CODE_XREF, weak name + year). The SV models only the strong join.
- The Business Ontology has no parent-of / subClassOf relationship type, so the hierarchy is RELATED_TO edges plus description text.

### Decisions
- **Keep the Genre Taxonomy sub-domain.** SQL computes the hierarchy; the ontology supplies the rules SQL can't infer (FULL = member, roll up to ancestors, count distinct games, non-additive genre revenue, Shooter -> FPS/TPS, ActionRPG/Soulslike also RPG). Removing it removes the D9 with/without test.
- **Title-to-game matching stays strictly in the ontology** (user decision). No resolution view and no xref/weak joins are added to the semantic view; the baseline SV keeps only the strong `TITLE_GAME` join.
- GENRE_RULES is not changed (D9).

## Accurate answer semantics (documented in the ontology)
1. A game is in genre G if it is FULL in G or any descendant of G (strict tree), plus the ontology cross-links (ActionRPG and Soulslike also count toward RPG).
2. Genre revenue = SUM of revenue over DISTINCT games in that set. Each genre gets the game's full revenue, so genre totals don't sum to total revenue.
3. Revenue must resolve title -> game strong -> medium -> weak (existing identity rules in the ontology; same CTE as eval Q4/Q15).
4. "Which genre" defaults to top-level genres (depth 1); subgenres only when asked.

## Implementation steps

1. **Roll-up view** `ONTOLOGY_DEMO.GAME_CATALOG.VW_GAME_GENRE_ROLLUP` in `sql/game_catalog/views/VW_GAME_GENRE_ROLLUP.sql`.
   - Columns: GAME_ID, ROLLUP_GENRE, LEAF_GENRE, ROLLUP_DEPTH.
   - Recursive CTE over GENRE_RULES (genre -> every ancestor including itself), joined to FULL rows of GAME_GENRE_CLASSIFICATION.
   - Strict tree only; no RPG cross-links, so RPG stays 0 in SQL alone.
2. **Semantic view** `yamls/gaming_baseline_sv.yaml`:
   - Add table `GENRE_ROLLUP` (on VW_GAME_GENRE_ROLLUP): dimensions ROLLUP_GENRE, LEAF_GENRE, ROLLUP_DEPTH; metric `ROLLUP_GAME_COUNT = COUNT(DISTINCT GAME_ID)`.
   - Relationship GENRE_ROLLUP.GAME_ID -> GAMES.GAME_ID.
   - Neutral descriptions (D17 leak guard): no RPG cross-link text, no identity-resolution hints.
3. **Ontology** `ontology_setup/build/build_ontology.py`:
   - New TERM "Genre Roll-up Rule" (semantics 1, 2 and 4), DESCRIBES `VW_GAME_GENRE_ROLLUP`.
   - New METRIC "Genre Revenue": SUM of gross revenue over distinct games in the genre set, resolved via the title -> game identity rules, non-additive across genres. Represent it on `DIGITAL_PRODUCT_TRANSACTIONS.GROSS_REVENUE` and `VW_GAME_GENRE_ROLLUP.ROLLUP_GENRE`; MEASURES Genre; RELATED_TO the existing Game identity term(s).
   - Update the Genre entity and RPG term descriptions to point at GENRE_ROLLUP for parent genres and to add ActionRPG/Soulslike games to RPG, counted distinct.
   - Keep RELATED_TO edges (no CUSTOM type). Add leak-guard entries for the new answer numbers.
   - Regenerate the 01-05 SQL; apply only the new or changed terms, relationships and associations.
4. **Eval set** `ontology_setup/ontology_eval_set.md`: add reference SQL with correct vs naive answers for
   - "Which genre has the most revenue?" (top-level, distinct games, fully resolved revenue)
   - "How much revenue did RPG games make?" (naive 0 by the strict tree; correct with cross-links)
   - "Revenue by Action subgenre"
   - Compute answers with read-only SQL against ONTOLOGY_DEMO. Record naive variants: leaf-only, strong-join-only revenue, and summing genre totals.
   - Mark `genre-hierarchy-design-issue.md` resolved with these decisions.
5. **Deploy and compare**: create the view, `python3 yamls/deploy_yamls.py`, run the new build SQL, then ask GAMING_BASELINE_AGENT and GAMING_BON_AGENT the new questions.

## Verification
- `SELECT ROLLUP_GENRE, COUNT(DISTINCT GAME_ID) FROM VW_GAME_GENRE_ROLLUP WHERE ROLLUP_DEPTH = 1 GROUP BY 1` matches `business_ontology_phases.md:285-295` (Action 68, Strategic 18, Adventure 13, Horror 11, Simulator 1, RPG 0).
- RPG with cross-links = 43 distinct games (eval Q13).
- Fully resolved revenue total = $19,231,852.01 (eval Q4); the strong-join-only total = $15,861,443.42 stays the naive baseline answer.
- build_ontology.py leak guard passes; the SV YAML contains no identity-resolution or RPG cross-link hints.
- Baseline agent: parent genres appear, but RPG is 0 and revenue is undercounted. BON agent: matches the reference answers. Existing eval questions don't regress.

## Critical files
- [sql/game_catalog/views/VW_GENRE_HIERARCHY.sql](sql/game_catalog/views/VW_GENRE_HIERARCHY.sql) - recursive pattern to reuse
- [yamls/gaming_baseline_sv.yaml](yamls/gaming_baseline_sv.yaml) - add GENRE_ROLLUP table and relationship
- [ontology_setup/build/build_ontology.py](ontology_setup/build/build_ontology.py) - roll-up TERM, Genre Revenue METRIC, descriptions, leak guard
- [ontology_setup/ontology_eval_set.md](ontology_setup/ontology_eval_set.md) - new genre revenue questions
- [ontology_setup/genre-hierarchy-design-issue.md](ontology_setup/genre-hierarchy-design-issue.md) - mark resolved
