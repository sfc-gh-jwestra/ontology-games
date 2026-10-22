# Plan: Business Ontology grants for ONTOLOGY_APP_ROLE

## Context
- **Access model:** per the [access control doc](https://docs.snowflake.com/en/LIMITEDACCESS/snowflake-horizon/business-ontology-access-control), access is granted per **ontology domain**. It can't be granted per node.
  - `READ` covers approved and deprecated nodes, the relationships between visible nodes, and representations.
  - `MODIFY` covers authoring and approving changes.
  - The [agents doc](https://docs.snowflake.com/en/LIMITEDACCESS/snowflake-horizon/business-ontology-agents) says ontology search checks domain access when the query runs, and that `USAGE` on the agent does not grant domain access.
- **Why the BON agent can't see the ontology yet:** the session runs only as `ONTOLOGY_APP_ROLE` (`OAUTH_USE_SECONDARY_ROLES = NONE`), and that role has no domain grants. The `business_ontology` tool would return nothing, which looks the same as a missing definition.
- **Live domains,** from `SYSTEM$GET_GLOSSARY_SUMMARY()`: `Game Catalog`, `Game Commerce`, `Genre Taxonomy`.
- **What's already covered:** agent USAGE, SELECT on the semantic view and tables, warehouse, `CORTEX_USER` and `CORTEX_AGENT_USER` are all in [app/sql/01_local_oauth.sql](app/sql/01_local_oauth.sql). Cortex Analyst runs as the caller, so the table SELECT grants are still required.
- **Scope:** the app only consumes the ontology, so only `READ` is needed. `MODIFY` would let the role edit and approve nodes, which the app doesn't need. I'll include it as a commented-out line.
- **Preview limitation:** domain grants don't appear in `SHOW GRANTS TO ROLE`, so verification has to run as the role itself.

## Implementation steps
1. In [app/sql/01_local_oauth.sql](app/sql/01_local_oauth.sql), replace the "Business Ontology search" placeholder comment with:
   ```sql
   -- Business Ontology (account-level, per domain). READ = approved nodes, relationships, representations.
   -- Domain grants are not shown by SHOW GRANTS (preview); verify by querying as the role.
   GRANT READ ON ONTOLOGY DOMAIN "Game Catalog"   TO ROLE ONTOLOGY_APP_ROLE;
   GRANT READ ON ONTOLOGY DOMAIN "Game Commerce"  TO ROLE ONTOLOGY_APP_ROLE;
   GRANT READ ON ONTOLOGY DOMAIN "Genre Taxonomy" TO ROLE ONTOLOGY_APP_ROLE;
   -- Only if this role should also author/approve nodes:
   -- GRANT MODIFY ON ONTOLOGY DOMAIN "Game Catalog" TO ROLE ONTOLOGY_APP_ROLE;  (repeat per domain)
   ```
   Domain names contain spaces, so they're double-quoted. If the parser rejects that form, try the name as a single-quoted string; the docs only show an unquoted single-word name (`finance`).
2. Run these 3 GRANT statements as ACCOUNTADMIN (or the domain owner role). I'll ask for confirmation first, since this changes account access.
3. Add one line to [app/README.md](app/README.md) under Setup: if you add a role to `APP_ROLES`, also grant it READ on each ontology domain.

## Verification
- As the role, check that the published graph is visible:
  `USE ROLE ONTOLOGY_APP_ROLE; SELECT SYSTEM$GET_GLOSSARY_SUMMARY();` should list all 3 domains, 70+ nodes and 93 relationships. A domain the role can't read shows up as not found.
- Spot-check the node from the earlier miss: `SELECT SYSTEM$GET_GLOSSARY_TERM('Developer Revenue');` as the role should return its formula.
- In the app, sign in as `ONTOLOGY_APP_ROLE` and run eval Q5. The BON pane should show "Searching ontology" with ontology nodes listed. The search index can lag up to 6 hours, so an empty result right after approval may not be a grant problem.

## Critical Files
- [app/sql/01_local_oauth.sql](app/sql/01_local_oauth.sql) - add the domain READ grants
- [app/README.md](app/README.md) - note domain grants for extra roles
