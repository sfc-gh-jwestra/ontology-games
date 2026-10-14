The goal is to make this nicely defined 3 schema database into a mess that will look more like two separate business systems: Sales and GameCatalog. Today, the database is cleanly divided into GAME_SALES and GAME_CATALOG and common tables that each use are in GAMES_CORE.

Instead, two systems should have duplicate tables and data in systems and have challenges outlined in the HOW_TO_MESS_YOUR_DATA_UP section below.

Implement counterintuitive database changes that will help to show how business ontology solves the 5 challenges posed in the ontology_setup/README_ontology_challenges.md. 

Ignore VIDEOWL schema.

## How to mess up the data
Think deeply about how to make the data table and view and dynamic view structural changes and data changes.

Find patterns to use when messing up the database and the data by analysing ontology_setup/README_ontology_challenges.md. It uses Healthcare references. You should apply to the gaming industry.

Follow each Challenge documented in the README_ontology_challenges.md and summarize in a markdown how you are accomplishing the messing up of the database and data.


Examples you could apply to muddy the data with are:
====================================================
MONETIZATION TYPES AND REVENUE CATAGORIES:
concretely, the REVENUE_CATEGORIES table has rows like DLC, BATTLE_PASS, SEASON_PASS, LOOT_BOX — these mirror the names already in MONETIZATION_TYPES (that's intentional, same vocabulary), but REVENUE_CATEGORIES is attached to a priced product and real transactions, while MONETIZATION_TYPES is just a tag on the game with nothing priced attached. One-line summary: MONETIZATION_TYPES says what kind of business model a game has; the REVENUE_CATEGORIES say what was actually sold — you can create some naming clashes there that need to be resolved by ontology later.


### Challenge 1 — Overloaded tables (one table → many ontology classes)

| Table | Entity types crammed into one row |

| GAME_CATALOG.GAME | Game + Publisher + Developer Studio + Franchise
| GAME_CATALOG.GAME | Game + Publisher + Developer Studio
| GAME_CORE.GAME_FRANCHISES | Franchise + Sequel information | 


Run merge-sequels-into-franchises plan to combine 


### Challenge 2 — Same entity, different names across systems
1. Add slightly different names for games.

See challenge2_same_entity_different_names.md


| Ontology Class | Sales | Catalog |
| -------- | -------- | -------- |
| Developer | Studio | Developer |
| Publisher | Publisher | ? |
| Player | Customer | Player |

# Create plan to alter database tables by domain.
The messy data should be applied cross-domain with how Business Ontology can help to solve the problems. For example, don't apply the same messy change to both Sales and GameCatalog.


Don't suggest how to fix the messy data patterns with things like views and UDFs and stored procedures.

The goal is to show value of Business Ontology to get the correct answers, not wrap all the bad data in views and things that abstract away the issues using SQL objects.

You can suggest multiple sub-plans and implement them separately if the work is too complex or interdependent.

Keep the changes to just enough examples per challenge that they are realistic, so that they can be applied to an ontology easily.

Think of the features supported by Snowflake Business Ontology when creating the issues in the data. Features of Business Ontology can be found in the bundled skill.