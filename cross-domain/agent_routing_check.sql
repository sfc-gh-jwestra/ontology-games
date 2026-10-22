-- Routing check for GAMING_ROUTER_AGENT. Run after `python3 cross-domain/deploy_agents.py`.
-- DATA_AGENT_RUN needs a constant request, so each question is its own statement.
-- ROUTED_TO shows the router's agent_router call(s): subagent_name, and direct_route = false
-- when it split the question across several specialists. Each run takes 30-120 s.
USE ROLE ONTOLOGY_APP_ROLE;   -- the role the React app signs in with
USE SECONDARY ROLES NONE;
USE WAREHOUSE COMPUTE_WH;

-- 1. Expect: Catalog agent
WITH r AS (SELECT PARSE_JSON(SNOWFLAKE.CORTEX.DATA_AGENT_RUN('ONTOLOGY_DEMO.CROSS_DOMAIN.GAMING_ROUTER_AGENT',
  '{"stream":false,"messages":[{"role":"user","content":[{"type":"text","text":"How many games has Santa Monica Studio developed?"}]}]}')) j)
SELECT 'catalog' expected,
       LISTAGG(IFF(c.value:type::STRING = 'tool_use', c.value:tool_use:input:subagent_name::STRING, NULL), ', ') routed_to,
       LISTAGG(IFF(c.value:type::STRING = 'text', c.value:text::STRING, NULL), ' ') answer
FROM r, LATERAL FLATTEN(r.j:content) c;

-- 2. Expect: Genre agent
WITH r AS (SELECT PARSE_JSON(SNOWFLAKE.CORTEX.DATA_AGENT_RUN('ONTOLOGY_DEMO.CROSS_DOMAIN.GAMING_ROUTER_AGENT',
  '{"stream":false,"messages":[{"role":"user","content":[{"type":"text","text":"How many RPG games are there?"}]}]}')) j)
SELECT 'genre' expected,
       LISTAGG(IFF(c.value:type::STRING = 'tool_use', c.value:tool_use:input:subagent_name::STRING, NULL), ', ') routed_to,
       LISTAGG(IFF(c.value:type::STRING = 'text', c.value:text::STRING, NULL), ' ') answer
FROM r, LATERAL FLATTEN(r.j:content) c;

-- 3. Expect: Sales agent
WITH r AS (SELECT PARSE_JSON(SNOWFLAKE.CORTEX.DATA_AGENT_RUN('ONTOLOGY_DEMO.CROSS_DOMAIN.GAMING_ROUTER_AGENT',
  '{"stream":false,"messages":[{"role":"user","content":[{"type":"text","text":"What was hardware revenue in North America?"}]}]}')) j)
SELECT 'sales' expected,
       LISTAGG(IFF(c.value:type::STRING = 'tool_use', c.value:tool_use:input:subagent_name::STRING, NULL), ', ') routed_to,
       LISTAGG(IFF(c.value:type::STRING = 'text', c.value:text::STRING, NULL), ' ') answer
FROM r, LATERAL FLATTEN(r.j:content) c;

-- 4. Expect: Cross-domain agent
WITH r AS (SELECT PARSE_JSON(SNOWFLAKE.CORTEX.DATA_AGENT_RUN('ONTOLOGY_DEMO.CROSS_DOMAIN.GAMING_ROUTER_AGENT',
  '{"stream":false,"messages":[{"role":"user","content":[{"type":"text","text":"Which developer earned the most revenue?"}]}]}')) j)
SELECT 'crossdomain' expected,
       LISTAGG(IFF(c.value:type::STRING = 'tool_use', c.value:tool_use:input:subagent_name::STRING, NULL), ', ') routed_to,
       LISTAGG(IFF(c.value:type::STRING = 'text', c.value:text::STRING, NULL), ' ') answer
FROM r, LATERAL FLATTEN(r.j:content) c;

-- 5. Expect: Genre agent + Sales agent in parallel (direct_route = false)
WITH r AS (SELECT PARSE_JSON(SNOWFLAKE.CORTEX.DATA_AGENT_RUN('ONTOLOGY_DEMO.CROSS_DOMAIN.GAMING_ROUTER_AGENT',
  '{"stream":false,"messages":[{"role":"user","content":[{"type":"text","text":"How many Horror games are there, and what was total subscription revenue?"}]}]}')) j)
SELECT 'genre + sales' expected,
       LISTAGG(IFF(c.value:type::STRING = 'tool_use', c.value:tool_use:input:subagent_name::STRING, NULL), ', ') routed_to,
       LISTAGG(IFF(c.value:type::STRING = 'text', c.value:text::STRING, NULL), ' ') answer
FROM r, LATERAL FLATTEN(r.j:content) c;

-- 6. Domain isolation: the Catalog agent must decline a sales question without calling query_data.
WITH r AS (SELECT PARSE_JSON(SNOWFLAKE.CORTEX.DATA_AGENT_RUN('ONTOLOGY_DEMO.CROSS_DOMAIN.GAMING_CATALOG_AGENT',
  '{"stream":false,"messages":[{"role":"user","content":[{"type":"text","text":"What was hardware revenue in North America?"}]}]}')) j)
SELECT 'catalog declines' expected,
       COALESCE(LISTAGG(IFF(c.value:type::STRING = 'tool_use', c.value:tool_use:name::STRING, NULL), ','), '') tools_used,
       LISTAGG(IFF(c.value:type::STRING = 'text', c.value:text::STRING, NULL), ' ') answer
FROM r, LATERAL FLATTEN(r.j:content) c;
