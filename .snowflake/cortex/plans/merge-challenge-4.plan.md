---
name: "merge-challenge-4"
created: "2026-10-27T15:45:37.339Z"
status: pending
---

# Plan: Remove Challenge 4, merge its overlaps, renumber C5-C8

## Context

Challenge 4 has four rows. Each already has a home elsewhere in the doc, or is already covered by the ontology:

| C4 content                                                                                | Where it goes                                              | Why                                                    |
| ----------------------------------------------------------------------------------------- | ---------------------------------------------------------- | ------------------------------------------------------ |
| `GAMES.DEVELOPER_NAME` (`Santa_Monica_Studio`) vs `TITLES.STUDIO` (`Santa Monica Studio`) | already Challenge 2's Developer row                        | exact duplicate                                        |
| `STUDIO_ACQUISITIONS.STUDIO_NAME` (third spelling source)                                 | Challenge 2's Developer row                                | same entity, different name                            |
| `ENGINES.DEVELOPER_COMPANY` (engine vendor; for in-house engines it holds a studio name)  | Challenge 7's `*DEVELOPER*` row, which already lists it    | same name, different meaning                           |
| "Developer has no table or key; aggregate over resolved catalog games"                    | Challenge 2's Developer row, plus a pointer to Challenge 3 | name-only matching depends on game identity resolution |

**No ontology changes needed.** In `scripts/build_ontology.py`, the Developer term already names `STUDIO_ACQUISITIONS.STUDIO_NAME` and says "NOT ENGINES.DEVELOPER\_COMPANY, which is the engine vendor" (lines 48-50). The Engine term says the same (lines 66-68). No challenge numbers appear in the ontology text, so `install/04a` and `04b` don't change.

**Renumbering:** C5 crosswalk becomes C4, C6 codes becomes C5, C7 overloaded names becomes C6, and C8 hierarchy becomes C7. The old "C4/5" and "4/5" labels (a holdover from the healthcare numbering, where 4 and 5 were the crosswalk) become plain "C4". The healthcare original (`README_ontology_challenges.md`) keeps its own numbering. Its "Challenge 8: wide vs long grain" reference in our C8 intro stays as "the healthcare example's Challenge 8".

**The app** groups the question dropdown by the eval's Challenge column (`app/frontend/src/App.tsx:88`). Making every tag start with its challenge code gives clean groups.

## Live references to update (from a repo-wide grep)

- `documentation/README_ontology_games_challenges.md`: headings 1-8; line 33 "Challenges 3 and 5"; line 98 "(Challenge 5)"; the C8 intro.
- `documentation/ontology_eval_set.md`: the challenge tags on Q1 (`C3 + C4/5 crosswalk`), Q10 (`C6`), Q3 and Q13 (`C7`), and the untagged genre questions Q4 and Q7-Q9.
- `documentation/business_ontology_phases.md:62`: D5 "Challenges 3 and 4/5".
- `documentation/ontology-overview.md:10` ("Challenges 1-7", meaning the messy data) and `:343` ("Challenge 7").
- `README.md:89`: "the 8 data challenges".
- **Left as is:** `.snowflake/cortex/plans/*.plan.md`, which are historical records of past work.

## Implementation steps

1. **Merge C4 into C2** (challenges doc, Developer row and text below the table):

   - Developer row: catalog `GAMES.DEVELOPER_NAME` = `Santa_Monica_Studio` and `STUDIO_ACQUISITIONS.STUDIO_NAME`; sales `TITLES.STUDIO` = `Santa Monica Studio`.
   - Add one sentence: "Developer has no table or key in either system, so studios match by name only. Developer-level answers come from aggregating resolved catalog games (Challenge 3), not from grouping store strings."

2. **Merge C4 into C7** (becomes C6):

   - In the `*DEVELOPER*` row's Meaning C, add: "for in-house engines it holds a studio name (e.g. `Santa_Monica_Studio`)".
   - Add a bullet under "Ontology assists by": "**Engine** says `ENGINES.DEVELOPER_COMPANY` is the engine vendor, not the game's Developer."

3. **Delete the Challenge 4 section**, then renumber the headings: 5 becomes 4, 6 becomes 5, 7 becomes 6, 8 becomes 7.

   - Line 33: "Challenges 3 and 5" becomes "Challenges 3 and 4".
   - Line 98: "(Challenge 5)" becomes "(Challenge 4)".

4. **Eval set tags** (`documentation/ontology_eval_set.md`), each starting with its main challenge:

   - Q1 `C3 + C4 crosswalk`
   - Q2 `C1 overloaded + C2`
   - Q3 `C6 misnamed column + C3`
   - Q4 `C7 genre synonym + C3 identity`
   - Q5 `C3 imperfect keys + grain (D11)`
   - Q6 `C4 crosswalk (governance, D15)`
   - Q7 `C7 genre roll-up + C3 identity`
   - Q8 `C7 genre roll-up (D9) + C3 identity`
   - Q9 `C7 genre hierarchy`
   - Q10 `C5 codes + synonym`
   - Q11 `C2 + C3 weak key`
   - Q12 `control (C3 imperfect keys)`
   - Q13 `control (C6 overloaded names)`

5. **Other docs:**

   - `business_ontology_phases.md` D5: "Challenges 3 and 4".
   - `ontology-overview.md`: "Challenges 1-6" (the messy data covers the old 1-7, which is the new 1-6), and "Challenge 6" at line 343.
   - `README.md`: "the 7 data challenges".

6. **Memory:** add one line to the project MEMORY.md noting that C4 was merged and C5-C8 renumbered to C4-C7, so later sessions don't use the old numbers.

## Verification

- Grep for `Challenge 8`, `C8`, `4/5` and `Challenge [4-7]` outside `.snowflake/plans`. Every remaining hit must match the new numbering, or be the deliberate healthcare "Challenge 8" mention.
- Check the challenges doc has headings 1-7 in order and no Studio-identity section.
- `python3 app/backend/test_questions.py` (it parses the Challenge column).
- Leak check: `cd scripts && python3 -c "import build_ontology as b; b.validate()"`. It should be unaffected; this confirms no ontology text changed.
- Optionally open the app (`bash app/dev.sh --mock`) and check the dropdown groups by C1-C7.

## Critical files

- documentation/README\_ontology\_games\_challenges.md: merge, delete and renumber
- documentation/ontology\_eval\_set.md: challenge tags for all 13 questions
- documentation/business\_ontology\_phases.md: D5 reference
- documentation/ontology-overview\.md: challenge range and Challenge 7 reference
- README.md: challenge count
