# Plan: Remove answer leaks from ontology descriptions

## Context

[ontology_setup/build/build_ontology.py](ontology_setup/build/build_ontology.py) is the source for all 70 live nodes. Reviewing every TERMS and GENRES entry turned up three problems.

**1. Answer leaks.** Many descriptions contain the exact expected answer from [ontology_eval_set.md](ontology_setup/ontology_eval_set.md), or the trap value an agent would get by mistake. Either way, the ontology agent can copy the number instead of computing it, which makes the with/without-ontology comparison meaningless.

| Node | What leaks |
|---|---|
| Digital Gross Revenue | Correct $19,231,852.01; Wrong $17,312,180.80 |
| Net Publisher Revenue | $19,119,344.99 |
| Platform Commission Revenue | $112,507.02 |
| Hardware Revenue | $175,660,810.62; NA $70,243,201.72 |
| Subscription Revenue | $35,634,616.54 |
| Total Platform Revenue | $211,407,934.18; Wrong $230,527,279.17 |
| Active Customer Count | 96,773 of 289,225; SIEA 38,699 |
| Battle Pass Sales Revenue | $150,389.48 |
| Currently Exclusive Game Count | 53 |
| Game Revenue | route split $ amounts, correct/wrong totals, GT7 and Ghost of Yotei amounts |
| Developer Revenue | top-3 developer amounts, Santa Monica wrong value |
| Franchise Revenue | God of War and Spider-Man amounts |
| Active Catalog Game Count | 89 of 90 |
| Game (entity) | "90 catalog games; 87 have digital sales" |
| Game Identity Match Rule | "Resolves 75 / 13 / 2", "loses $1,612,478.74" |
| SKU Code | Example CUSA86252-C1101 = MLB The Show 17, LOOT_BOX. This is eval question verbatim. |
| Revenue Type Code | BASE_GAME_PHYSICAL $7,881,147.58 |
| Genre Match Score | 258 of 3,420 evaluations |
| Digital Product | 354 products, about 3.9 per game |
| All 14 genre terms | member counts: Action 68, RPG 43, FPS 10, Shooter 30, TPS 20, ActionRPG 43, Soulslike 0, and so on |

**2. Thin metric descriptions.** Several metrics don't state their grain, whether they are gross or net, or how time and region apply. Subscription Revenue is the worst: just "PlayStation Plus charges."

**3. No metric representations.** REP links entities and terms to tables and columns, but none of the 15 METRIC nodes has one. That is why `representedAs: []` showed on Subscription Revenue.

**What stays:**
- Schema and code facts the agent needs and can't easily guess: code value lists, key ranges (TITLE_ID 5001-5090), "TITLE_ID NULL for every 10th row", "CATALOG_GAME_ID NULL for some titles", the 8 renamed names. These describe structure, not answers.
- Formulas.
- Wrong-way warnings, stated as rules without numbers. For example: "do not filter TITLE_ID IS NOT NULL".

**Update path:** `SYSTEM$UPDATE_GLOSSARY_TERM(name, patch_json)` accepts `description` and `formula`. It edits ACTIVE nodes in place, so relationships and term IDs are kept. No rebuild needed.

## Leak rule (applied to every description)

Remove anything an eval question asks for, plus any trap value: totals, counts of games/customers/pairs, per-game, per-developer and per-franchise amounts, genre member counts, and route-split counts. Replace each with guidance:
- **grain**: what one row is
- **gross vs net**: whether platform commission is included
- **filters**: which status or region code applies
- **additivity**: whether the metric can be summed across groups
- **pitfall**: the wrong way, with no number

Indicative rewrites:
- **Subscription Revenue**: "Gross PlayStation Plus billing. Grain: one row per subscription charge (SUBSCRIPTION_CHARGES), keyed to a customer by SUBSCRIBER_ID and to a plan by PLAN_ID. Gross, no commission deducted. Time by billing period. No region column; for region join to CUSTOMER_ACCOUNTS (SIE Region Code). Additive. Part of Total Platform Revenue in full."
- **Total Platform Revenue**: "What the platform keeps. = Hardware Revenue + Platform Commission Revenue + Subscription Revenue. Digital contributes ONLY the commission, never the full digital gross. Pitfall: summing all GROSS_REVENUE columns overstates it."
- **Game Revenue**: keep the 3-step resolution and the COALESCE rule. Drop all amounts. Pitfall: joining on CATALOG_GAME_ID only drops titles.
- **SKU Code**: keep the format. Pick an example SKU that no eval question uses.
- **Genre terms**: drop member counts. Keep parent, rule meaning and variant axis. Keep "Soulslike: its rule needs attributes that do not exist in the data", which explains the zero without stating it.
- **Game**: drop "90 / 87". Keep the grain warning (count games, not products).

## Implementation steps

1. **Rewrite descriptions** in [build_ontology.py](ontology_setup/build/build_ontology.py) for every node in the table above, following the leak rule. Enrich all 15 METRIC descriptions with grain, gross/net, filters, additivity and pitfall. Leave formulas unchanged except where the wording needs to be clearer.
2. **Add a leak guard** in the same script, asserted at generation time.
   - Collect the expected and trap values from the eval set into a `FORBIDDEN` list: dollar amounts, counts and the eval SKU.
   - Fail the build if any description contains one of them, in any formatting, with or without the `$` or commas.
   - Also fail on the words `Correct:` and `Wrong (`.
3. **Add metric representations to REP.** Each is a COLUMN on the measured column:
   - Digital Gross Revenue, Game, Developer and Franchise Revenue, Battle Pass Sales Revenue: DIGITAL_PRODUCT_TRANSACTIONS.GROSS_REVENUE
   - Net Publisher Revenue: NET_DEVELOPER_REVENUE
   - Platform Commission Revenue: PLATFORM_COMMISSION_PCT
   - Hardware Revenue: HARDWARE_SALES_TRANSACTIONS.GROSS_REVENUE
   - Subscription Revenue: SUBSCRIPTION_CHARGES.GROSS_REVENUE
   - Active Customer Count: CUSTOMER_ACCOUNTS.STATUS
   - Currently Exclusive Game Count: GAME_PLATFORMS.IS_EXCLUSIVE
   - Active Catalog Game Count: GAMES.STATUS
   - Genre Match Score: GAME_GENRE_CLASSIFICATION.MATCH_STATUS
   - Weighted Overlap: GAME_SIMILARITY_SCORES.WEIGHTED_OVERLAP
   - Total Platform Revenue: the 3 source tables

   That adds about 17 representations, for about 92 in total.
4. **Generate the update scripts.**
   - `04_update_descriptions.sql`: one `SYSTEM$UPDATE_GLOSSARY_TERM` per changed node, with the description and, for metrics, the formula as a patch. JSON is serialised once and escaped once with the existing `lit()`.
   - `05_metric_representations.sql`: the new associations.
   - Keep `01_domains_terms.sql` regenerating with the cleaned text, so a fresh rebuild is also clean.
5. **Apply to Snowflake** with `snow sql -c JWESTRA_AWS1 -f` for 04, then 05.
6. **Update the docs.**
   - [business_ontology_phases.md](ontology_setup/business_ontology_phases.md): add decision D17 ("no answers in ontology text; expected values live only in the eval set"), update the Phase 3 metric template, and update the representation count.
   - [ontology_eval_set.md](ontology_setup/ontology_eval_set.md): add a note that the ontology must not contain expected values. The eval file remains the only home of answers.

## Verification

- `python3 build_ontology.py` passes the new leak guard and the existing assertions (unique names and synonyms, valid edges).
- Read every node back: run `SYSTEM$GET_GLOSSARY_TERM` for all 70 names and scan the returned descriptions in SQL (regex on `\$[0-9]`, `Correct:`, and each FORBIDDEN value). Expected: 0 hits. Per invariant I6, `error:false` alone doesn't count as success.
- `SYSTEM$GET_GLOSSARY_SUMMARY()`: still 70 ACTIVE terms and 93 relationships; associations go from 75 to about 92.
- Spot check: `Subscription Revenue` shows the new description and a non-empty `representedAs`.
- Formulas are unchanged. I'll diff the formula field before and after for all 15 metrics.

## Critical Files

- [ontology_setup/build/build_ontology.py](ontology_setup/build/build_ontology.py): all description edits, the leak guard, the new REP rows and the update-script generation.
- [ontology_setup/ontology_eval_set.md](ontology_setup/ontology_eval_set.md): source of the FORBIDDEN values.
- [ontology_setup/business_ontology_phases.md](ontology_setup/business_ontology_phases.md): decision D17 and the updated counts.
- `ontology_setup/build/04_update_descriptions.sql`, `05_metric_representations.sql`: new generated scripts.
