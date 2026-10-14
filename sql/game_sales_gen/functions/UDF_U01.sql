CREATE OR REPLACE FUNCTION ONTOLOGY_DEMO.GAME_SALES_GEN.UDF_U01("SEED" NUMBER(38,0), "K" VARCHAR)
RETURNS FLOAT
LANGUAGE SQL
COMMENT='Deterministic pseudo-random number in [0,1) from a seed and a key; used instead of RANDOM() so generation is reproducible.'
AS 'CAST(MOD(ABS(HASH(SEED, K)), 1000000007) AS FLOAT) / 1000000007.0';
