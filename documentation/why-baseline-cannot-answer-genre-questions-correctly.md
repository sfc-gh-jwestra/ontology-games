# Why the baseline agent can't answer genre questions correctly

The genre data is all there. What the tables don't say is how a genre question should be read: which rows count, how genres roll up, and how a sale links to a game. The baseline semantic view gives the agent column names and join paths, not those rules, so it writes SQL that runs cleanly and returns a believable wrong number. This affects eval questions 4 and 7-9 in [ontology_eval_set.md](ontology_eval_set.md).

## 1. Every genre question first has to resolve each sale to a catalog game

Genre lives only in the catalog, so each Sales title has to be matched to a catalog game. The only title-to-game join in `SV_GAMING_CROSS_DOMAIN` is the catalog ID on the Sales title (`TITLES.CATALOG_GAME_ID`). Titles that match only through the store-code crosswalk (`TITLE_CODE_XREF`), or only by name and release year (Ghost of Yōtei), are dropped. Even when the genre logic is right, revenue comes out low:

| Question | Expected | Catalog-ID join only |
|---|---|---|
| Q7 Action | $14,642,492.04 | $13,217,013.28 |
| Q8 RPG | $13,436,693.28 | $12,278,693.28 |

The rule that fixes this is the **Game Identity Match Rule**, and only the ontology has it.

## 2. The genre tree has only one parent per genre, and the business meaning differs from it

This is deliberate (decision D9).

- In `GENRE_RULES`, ActionRPG's parent is Action, Soulslike's is ActionRPG, and Roguelike's is RPG.
- In `VW_GAME_GENRE_ROLLUP`, `ROLLUP_GENRE = 'RPG'` returns **0 games**, so a baseline that follows the tree reports $0 for Q8.
- The business counts ActionRPG and Soulslike games as RPGs too. That family has **43 games**.
- Nothing in the tables says that. Only the ontology's **RPG** term and **Genre Roll-up Rule** do.

## 3. Genre names and match quality need interpreting

- **Synonyms (Q4):** "first-person shooter" is not a value in the data; it's stored as `FPS`. The baseline may sum all shooters instead, or find nothing. The ontology's **FPS** term carries the synonym.
- **Match quality:** `GAME_GENRE_CLASSIFICATION` has `FULL`, `PARTIAL`, `NONE` and `UNEVALUABLE` rows. Only `FULL` means the game is in that genre. Without that rule the agent may count partial matches, or every game that was evaluated.

## 4. Genre totals are not additive (Q7, Q9)

A game counts in every genre it belongs to. The baseline tends to either:

- group by the genre the game was classified into directly (Q7 then reports ActionRPG instead of Action), or
- add the subgenres together and report about $30.6M for Action, more than total revenue ($19,231,852.01).

The ontology's **Genre Revenue** metric says these totals aren't additive.

## Summary

Having all the data isn't enough. Deciding which rows count, which hierarchy to follow and which join is valid is business meaning, and in this demo it lives only in the ontology. Adding `GENRE_ROLLUP` to the semantic view lets the baseline show parent genres, but it still gets RPG and the identity matching wrong.
