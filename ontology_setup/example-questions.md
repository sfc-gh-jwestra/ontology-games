I'll pull the ontology summary to see available domains.

Now the graph for node names, relationships, and representations.

The ontology is enabled and fully published: 3 domains, 70 ACTIVE nodes, 93 relationships and 92 representations, with no pending drafts. Every representation points into the `ONTOLOGY_DEMO` database: <catalog_object db="ONTOLOGY_DEMO" schema="GAME_SALES" name="" type="schema" /> and <catalog_object db="ONTOLOGY_DEMO" schema="GAME_CATALOG" name="" type="schema" />. Domain names didn't come back on the per-node graph rows, so the node lists below are grouped by kind across all domains.

**Domains**
| Domain | Nodes (Entity / Metric / Term) | Relationships | Representations |
|---|---|---|---|
| Game Catalog | 19 (8 / 4 / 7) | 20 | 34 |
| Game Commerce | 26 (8 / 9 / 9) | 23 | 31 |
| Genre Taxonomy | 25 (6 / 2 / 17) | 22 | 27 |

**What's in it**
- **Entities:** Game, Franchise, Publisher, Developer, Platform, Customer, Subscription Plan, Subscription Charge, Digital Product, Digital Transaction, Hardware Sale, Genre, Mechanic, Engine and others.
- **Metrics:** Subscription Revenue, Total Platform Revenue, Net Publisher Revenue, Platform Commission Revenue, Digital Gross Revenue, Hardware Revenue, Battle Pass Sales Revenue, Active Customer Count, Genre Match Score, Weighted Overlap and others.
- **Terms:** genre values (RPG, Soulslike, FPS, TPS and so on), code systems (SKU Code, SIE Region Code, Platform Code, POV Code) and rules (Game Identity Match Rule, Genre Rule).
- **Relationship types I saw:** RELATED_TO, CLASSIFIES, HAS_VARIANT, MEASURES, DERIVES.

**Subscription Revenue (the node you're viewing)**
- **Definition:** gross PlayStation Plus billing, `SUM(GROSS_REVENUE)` from <catalog_object db="ONTOLOGY_DEMO" schema="GAME_SALES" name="SUBSCRIPTION_CHARGES" type="table" />. No commission is deducted.
- **Relationship:** it DERIVES Total Platform Revenue.
- **Representation:** the `GROSS_REVENUE` column.
- **Synonym:** "PlayStation Plus Revenue".

## Questions to test it

**Definitions**
1. "What is Subscription Revenue, and is it gross or net of commission?" It should say gross, with no commission.
2. "What's our PlayStation Plus revenue?" This checks that the synonym resolves to Subscription Revenue.
3. "How does Net Publisher Revenue differ from Platform Commission Revenue?"
4. "What does Soulslike mean? Is it a kind of ActionRPG or RPG?"
5. "What is the Game Identity Match Rule, and when do Catalog Game ID and Sales Title ID match?"
6. "Is Active Customer Count based on Account Status? Which statuses count as active?"

**Relationships**

7. "Which metrics add up to Total Platform Revenue?" Expect Subscription, Digital, Hardware and Commission Revenue.
8. "Which entities does Genre Match Score measure?"
9. "How is Franchise related to Game and Publisher? What does Franchise Relationship Type classify?"
10. "What does Genre Rule classify, and which genres have variants (HAS_VARIANT)?"
11. "Show Subscription Revenue by region." This tests the join from `SUBSCRIBER_ID` to `CUSTOMER_ACCOUNTS.REGION` (SIE Region Code).
12. "Which Game Commerce nodes are linked to Game Catalog nodes?" This checks whether links cross between domains.

**Snowflake representations**

13. "Which table and column implement Hardware Revenue?"
14. "Is Total Platform Revenue a whole table or a column?" One representation appears to link a revenue metric to the entire `HARDWARE_SALES_TRANSACTIONS` table, which is worth checking.
15. "Is `STUDIO_ACQUISITIONS.STUDIO_NAME` represented by the right node?" The node it links to has the same ID as the Genre Taxonomy domain, so this may be a mislink.
16. "Which column holds Weighted Overlap, and what's its data type?" It should be `GAME_SIMILARITY_SCORES.WEIGHTED_OVERLAP`, FLOAT.
17. "Which metrics have a formula but no representation?" This finds coverage gaps.
18. "Is every Platform Code representation still valid?" All 6 representations I sampled are marked VALID.

Questions 14 and 15 are the most likely to turn up real problems. I can check both directly, or run a full gap audit (questions 17 and 18) if you'd like.