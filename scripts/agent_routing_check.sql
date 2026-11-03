-- Routing check for the CoWork profile SNOWFLAKE_INTELLIGENCE.PROFILES.GAMING_PROFILE.
-- Run after `./install.sh --only 03` and `--only 05`.
-- Uses the profile API: a profile is an agent, so DATA_AGENT_RUN calls it by FQN (it doesn't need to
-- be attached to CoWork). Each routing appears as a tool_use item of type agent_router, and
-- input.subagent_name is the agent that received the question. DATA_AGENT_RUN needs a constant
-- request, so each question is its own statement. Each run takes 30-120 s.
USE ROLE GAMING_PROFILE_USER;   -- USAGE on the profile at all three levels + ONTOLOGY_APP_ROLE data grants
USE SECONDARY ROLES NONE;
USE WAREHOUSE COMPUTE_WH;

-- 0. The profile's subagent list survived (a subagent missing a field silently drops the list).
--    Expect 4: catalog, genre, sales, baseline.
DESCRIBE AGENT SNOWFLAKE_INTELLIGENCE.PROFILES.GAMING_PROFILE;
SELECT ARRAY_SIZE(PARSE_JSON("agent_spec"):tool_resources:router:subagents) AS subagent_count
FROM TABLE(RESULT_SCAN(LAST_QUERY_ID()));

-- 1. Expect: GAMING_CATALOG_AGENT
WITH r AS (SELECT TRY_PARSE_JSON(SNOWFLAKE.CORTEX.DATA_AGENT_RUN('SNOWFLAKE_INTELLIGENCE.PROFILES.GAMING_PROFILE',
  '{"stream":false,"messages":[{"role":"user","content":[{"type":"text","text":"How many games has Santa Monica Studio developed?"}]}]}')) j)
SELECT 'catalog' expected,
       LISTAGG(IFF(c.value:tool_use:type::STRING = 'agent_router', c.value:tool_use:input:subagent_name::STRING, NULL), ', ') routed_to,
       LISTAGG(IFF(c.value:type::STRING = 'text', c.value:text::STRING, NULL), ' ') answer
FROM r, LATERAL FLATTEN(r.j:content) c;

-- 2. Expect: GAMING_GENRE_AGENT
WITH r AS (SELECT TRY_PARSE_JSON(SNOWFLAKE.CORTEX.DATA_AGENT_RUN('SNOWFLAKE_INTELLIGENCE.PROFILES.GAMING_PROFILE',
  '{"stream":false,"messages":[{"role":"user","content":[{"type":"text","text":"How many RPG games are there?"}]}]}')) j)
SELECT 'genre' expected,
       LISTAGG(IFF(c.value:tool_use:type::STRING = 'agent_router', c.value:tool_use:input:subagent_name::STRING, NULL), ', ') routed_to,
       LISTAGG(IFF(c.value:type::STRING = 'text', c.value:text::STRING, NULL), ' ') answer
FROM r, LATERAL FLATTEN(r.j:content) c;

-- 3. Expect: GAMING_SALES_AGENT
WITH r AS (SELECT TRY_PARSE_JSON(SNOWFLAKE.CORTEX.DATA_AGENT_RUN('SNOWFLAKE_INTELLIGENCE.PROFILES.GAMING_PROFILE',
  '{"stream":false,"messages":[{"role":"user","content":[{"type":"text","text":"What was hardware revenue in North America?"}]}]}')) j)
SELECT 'sales' expected,
       LISTAGG(IFF(c.value:tool_use:type::STRING = 'agent_router', c.value:tool_use:input:subagent_name::STRING, NULL), ', ') routed_to,
       LISTAGG(IFF(c.value:type::STRING = 'text', c.value:text::STRING, NULL), ' ') answer
FROM r, LATERAL FLATTEN(r.j:content) c;

-- 4. Expect: GAMING_BASELINE_AGENT (cross-domain)
WITH r AS (SELECT TRY_PARSE_JSON(SNOWFLAKE.CORTEX.DATA_AGENT_RUN('SNOWFLAKE_INTELLIGENCE.PROFILES.GAMING_PROFILE',
  '{"stream":false,"messages":[{"role":"user","content":[{"type":"text","text":"Which developer earned the most revenue?"}]}]}')) j)
SELECT 'baseline (cross-domain)' expected,
       LISTAGG(IFF(c.value:tool_use:type::STRING = 'agent_router', c.value:tool_use:input:subagent_name::STRING, NULL), ', ') routed_to,
       LISTAGG(IFF(c.value:type::STRING = 'text', c.value:text::STRING, NULL), ' ') answer
FROM r, LATERAL FLATTEN(r.j:content) c;

-- 5. Expect: GAMING_GENRE_AGENT + GAMING_SALES_AGENT in parallel
WITH r AS (SELECT TRY_PARSE_JSON(SNOWFLAKE.CORTEX.DATA_AGENT_RUN('SNOWFLAKE_INTELLIGENCE.PROFILES.GAMING_PROFILE',
  '{"stream":false,"messages":[{"role":"user","content":[{"type":"text","text":"How many Horror games are there, and what was total subscription revenue?"}]}]}')) j)
SELECT 'genre + sales' expected,
       LISTAGG(IFF(c.value:tool_use:type::STRING = 'agent_router', c.value:tool_use:input:subagent_name::STRING, NULL), ', ') routed_to,
       LISTAGG(IFF(c.value:type::STRING = 'text', c.value:text::STRING, NULL), ' ') answer
FROM r, LATERAL FLATTEN(r.j:content) c;

-- 6. Domain isolation: the Catalog agent must decline a sales question without calling query_data.
WITH r AS (SELECT TRY_PARSE_JSON(SNOWFLAKE.CORTEX.DATA_AGENT_RUN('ONTOLOGY_DEMO.AGENTS.GAMING_CATALOG_AGENT',
  '{"stream":false,"messages":[{"role":"user","content":[{"type":"text","text":"What was hardware revenue in North America?"}]}]}')) j)
SELECT 'catalog declines' expected,
       COALESCE(LISTAGG(IFF(c.value:type::STRING = 'tool_use', c.value:tool_use:name::STRING, NULL), ','), '') tools_used,
       LISTAGG(IFF(c.value:type::STRING = 'text', c.value:text::STRING, NULL), ' ') answer
FROM r, LATERAL FLATTEN(r.j:content) c;
