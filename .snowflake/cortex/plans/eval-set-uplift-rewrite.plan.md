# Plan: Rewrite the eval set for ontology uplift

## Context

### Re-run of the "BOTH CORRECT" questions on the baseline (2026-10-15)
Run as `ONTOLOGY_APP_ROLE` with no secondary roles, using `DATA_AGENT_RUN` on `GAMING_BASELINE_AGENT`. Questions were asked verbatim.

| Q | Baseline answer | Expected | Result |
|---|---|---|---|
| 1 digital revenue | $19,231,852 | $19,231,852.01 | correct |
| 2 Gran Turismo 7 | $899,999.98 (found "GT7" by itself) | $899,999.98 | correct |
| 3 Ghost of Yōtei | $198,000 (matched "Ghost of Yotei" by itself) | $198,000.00 | correct |
| 7 active customers | 96,773 (guessed 'A' = active) | 96,773 | correct |
| 8 active NA customers | 38,699 (guessed SIEA = NA) | 38,699 | correct |
| 9 hardware revenue NA | $70.24M | $70,243,201.72 | correct |
| 10 battle passes | $150,389.48 | $150,389.48 | correct |
| 12 platform keeps | **$230.5M**, with $211.4M as the "other reading" | $211,407,934.18 | **wrong this run** |
| 13 RPG games | 43 | 43 | correct |
| 14 first-person shooters | **13**, with 10 as an alternative | 10 | **wrong this run** |
| 16 currently exclusive | 53 | 53 | correct |
| 19 SKU CUSA86252-C1101 | MLB The Show 17, LOOT_BOX | same | correct |

**Conclusion:** 10 questions (1, 2, 3, 7, 8, 9, 10, 13, 16, 19) don't separate the agents. The data codes are self-explanatory enough for the baseline to work them out.
- Q12 and Q14 flip between runs. When they fail, the baseline is choosing between two readings, and the ontology picks the right one. Keep both.
- **Q9 reworded, verified:** "What was **console** revenue in North America?" The baseline answers **$64.17M** (consoles only). The governed `Hardware Revenue` metric (synonym `Console Revenue`) is $70,243,201.72.

### Age Rating
**Why it hasn't shown uplift so far:**
- `AGE_RATINGS` and `GAME_RATINGS` are **not in `GAMING_BASELINE_SV`**, so neither agent can query rating data. A data question can't distinguish them.
- The rating tables were **not made messy**. They appear in no challenge in `messy_data_design.md` and nothing in `sql/mess/`.
- `MIN_AGE` already normalizes ages across boards. "Mature" by the governed mapping gives 30 games, and `MIN_AGE >= 17` also gives 30. Even with the tables added to the view, a naive agent gets the count right without the ontology. A plain ESRB filter gives 29, which misses PEGI-only game 643.
- The governed equivalence text doesn't fully match the data. ESRB T pairs with PEGI 12 on 8 games and PEGI 16 on 13. E10+ always pairs with PEGI 7, but the definition doesn't mention it.

**It does show uplift as a definition question. Tested with the app's judge (same prompt and model):**
- Question: "Which PEGI and CERO ratings are equivalent to an ESRB M rating?"
- Baseline: "no age ratings in the data model", then from general knowledge "PEGI 18 ... CERO D".
- BON: "PEGI 18 and CERO Z", citing the governed `Age Rating System` definition.
- Judge (`claude-sonnet-4-5`, temperature 0): `baseline_correct=false, ontology_correct=true, differ=true`.
  > "The ontology agent is correct; the baseline agent answered from general industry knowledge instead of the governed mapping."

**Caveat:** the expected answer is the governed definition itself, like Q20. That is allowed under D17, because no expected *data value* is placed in the ontology.

### Constraints
- [app/backend/questions.py](app/backend/questions.py) parses the `## Questions` table rows `| # | Question | Challenge | Expected | Naive trap | Nodes |` and the reference-SQL table. The UI dropdown and the judge both read from it.
- [app/backend/test_questions.py](app/backend/test_questions.py) asserts the current question count and Q21 content, so it must be updated.
- [ontology_setup/build/build_ontology.py:486](ontology_setup/build/build_ontology.py) has the D17 `FORBIDDEN` leak list. Add any new expected numbers to it.
- No ontology description changes in this plan, apart from the optional Age Rating fix in step 4.

## Implementation steps
1. **Remove** Q1, Q2, Q3, Q7, Q8, Q10, Q13, Q16 and Q19 from `## Questions`, the results template and the reference SQL in [ontology_setup/ontology_eval_set.md](ontology_setup/ontology_eval_set.md). Move them to a short `## Retired questions (baseline solves unaided)` list with a one-line reason each, so the history isn't lost.
2. **Reword Q9** to "What was console revenue in North America?". Expected $70,243,201.72. Trap: counts only console products, giving $64,170,000 (approx). Fixed by `Hardware Revenue` (synonym Console Revenue) and `Sales Region Code`.
3. **Add new questions.** They target definitions and policies the data can't reveal:
   - **Age Rating equivalence:** "Which PEGI and CERO ratings are equivalent to an ESRB M rating?" Expected **PEGI 18, CERO Z**. Trap: answers from general knowledge (CERO D). Fixed by `Age Rating System`. Already verified.
   - **Store commission:** "How much of our digital sales does the store keep as its cut?" Expected **$112,507.02** (gross minus publisher share). Trap: applies a typical 30% rate (about $5.77M), or reports net as the store's share. Fixed by `Platform Commission Revenue` (synonym Store Cut) and `Net Publisher Revenue`.
   - **Cannibalization policy:** "What makes two of our games cannibalization candidates?" Expected: **same Publisher and Weighted Overlap >= 0.3**. Trap: invents a rule (same genre, release window); the similarity table isn't in the view. Fixed by `Weighted Overlap`.
   - Renumber the set 1..N in the current order. Keep the challenge labels, and add the reference SQL for the store commission question.
4. **Optional:** tighten the `Age Rating System` definition, with an edit card plus approval, so it matches the data: add E10+ = PEGI 7 and note that ESRB T can be PEGI 12 or 16. This affects only the T and E10+ questions, not the M question above, so it isn't required.
5. Add the new expected values (112,507.02, 70,243,201.72, 64.17M) to `FORBIDDEN` in `build_ontology.py`. Run the build's leak check.
6. Update `test_questions.py` for the new count and spot-check the new questions. Run the tests.
7. **Re-run in the React UI:** run every remaining question and record the judge verdicts in the `RESULTS OF RUNNING IN REACT UI` section. Run Q12 and Q14 at least twice and note that they are unstable on the baseline.

## Verification
- `python3 test_compare.py` and `test_questions` pass, and the dropdown lists the new set with no duplicate numbers.
- The `build_ontology.py` leak check passes.
- In the React UI, each new question gets `ontology_correct=true, baseline_correct=false` from the judge. Report any that don't, with the baseline's answer, and suggest dropping or rewording them.

## Critical Files
- [ontology_setup/ontology_eval_set.md](ontology_setup/ontology_eval_set.md) - question table, reference SQL, results
- [app/backend/test_questions.py](app/backend/test_questions.py) - question count/content assertions
- [ontology_setup/build/build_ontology.py](ontology_setup/build/build_ontology.py) - D17 FORBIDDEN list (and optional Age Rating System text)
- [app/backend/questions.py](app/backend/questions.py) - parser contract the edits must keep
