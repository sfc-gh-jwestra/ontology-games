"""Split yamls/gaming_baseline_sv.yaml into domain semantic views plus two composed views.

Table, dimension, fact, metric and relationship blocks are copied verbatim from the baseline,
so the strict composed view is the baseline rebuilt from parts.

  sv_game_catalog.yaml                 Game Catalog domain   (GAME_CATALOG minus genre)
  sv_genre_taxonomy.yaml               Genre Taxonomy domain (imports SV_GAME_CATALOG)
  sv_game_commerce.yaml                Game Commerce domain  (GAME_SALES)
  sv_gaming_cross_domain.yaml          imports all three + TITLE_GAME (strong key, = baseline)
  sv_gaming_cross_domain_resolved.yaml imports all three + local TITLE_GAME_MAP (identity rule)

Usage (from the repo root):  python3 cross-domain/build_yamls.py   (re-run after editing the baseline)
"""
from pathlib import Path

import yaml

HERE = Path(__file__).parent
BASELINE = HERE.parent / "yamls" / "gaming_baseline_sv.yaml"
OUT = HERE / "yamls"
DB, SCHEMA = "ONTOLOGY_DEMO", "CROSS_DOMAIN"

CATALOG_TABLES = ["GAMES", "GAME_FRANCHISES"]
GENRE_TABLES = ["GENRE_CLASSIFICATION", "GENRE_ROLLUP"]
COMMERCE_TABLES = ["CUSTOMERS", "DIGITAL_PRODUCTS", "DIGITAL_TRANSACTIONS", "HARDWARE_PRODUCTS",
                   "HARDWARE_SALES", "REVENUE_TYPES", "SALES_GAME_PLATFORMS", "SALES_PLATFORMS",
                   "SUBSCRIPTION_CHARGES", "SUBSCRIPTION_PLANS", "TITLES", "TITLE_CODE_XREF"]
CROSS_DOMAIN_RELS = ["TITLE_GAME"]  # the only baseline relationship between Sales and Catalog


def imp(name: str) -> dict:
    return {"database_name": DB, "schema_name": SCHEMA, "name": name}


def main():
    base = yaml.safe_load(BASELINE.read_text())
    tables = {t["name"]: t for t in base["tables"]}
    rels = {r["name"]: r for r in base["relationships"]}
    assert set(tables) == set(CATALOG_TABLES + GENRE_TABLES + COMMERCE_TABLES), "baseline tables changed"

    def rels_within(names, also=()):
        allowed = set(names) | set(also)
        return [r for r in base["relationships"]
                if r["name"] not in CROSS_DOMAIN_RELS
                and r["left_table"] in allowed and r["right_table"] in allowed
                and (r["left_table"] in names or r["right_table"] in names)]

    views = {
        "sv_game_catalog.yaml": {
            "name": "SV_GAME_CATALOG",
            "description": "Business Ontology domain: Game Catalog. Catalog games and franchises (GAME_CATALOG).",
            "tables": [tables[n] for n in CATALOG_TABLES],
            "relationships": rels_within(CATALOG_TABLES),
        },
        "sv_genre_taxonomy.yaml": {
            "name": "SV_GENRE_TAXONOMY",
            "description": "Business Ontology domain: Genre Taxonomy. Genre classification and roll-up; imports SV_GAME_CATALOG for GAMES.",
            "imports": [imp("SV_GAME_CATALOG")],
            "tables": [tables[n] for n in GENRE_TABLES],
            "relationships": rels_within(GENRE_TABLES, also=["GAMES"]),
        },
        "sv_game_commerce.yaml": {
            "name": "SV_GAME_COMMERCE",
            "description": "Business Ontology domain: Game Commerce. Sales titles, products, transactions, hardware, subscriptions (GAME_SALES). No link to the Catalog.",
            "tables": [tables[n] for n in COMMERCE_TABLES],
            "relationships": rels_within(COMMERCE_TABLES),
        },
        "sv_gaming_cross_domain.yaml": {
            "name": "SV_GAMING_CROSS_DOMAIN",
            "description": "Composed view: imports the three domain views and adds the strong-key TITLE_GAME join (Sales TITLES.CATALOG_GAME_ID -> Catalog GAMES). Same joins as GAMING_BASELINE_SV.",
            "imports": [imp("SV_GAME_CATALOG"), imp("SV_GENRE_TAXONOMY"), imp("SV_GAME_COMMERCE")],
            "relationships": [rels[n] for n in CROSS_DOMAIN_RELS],
        },
        "sv_gaming_cross_domain_resolved.yaml": {
            "name": "SV_GAMING_CROSS_DOMAIN_RESOLVED",
            "description": "Composed view: imports the three domain views and resolves every Sales title to a Catalog game through TITLE_GAME_MAP (Game Identity Match Rule: strong key, title-code crosswalk, then name + release year).",
            "imports": [imp("SV_GAME_CATALOG"), imp("SV_GENRE_TAXONOMY"), imp("SV_GAME_COMMERCE")],
            "tables": [{
                "name": "TITLE_GAME_MAP",
                "description": "One row per Sales title with its resolved Catalog game and the match route used.",
                "base_table": {"database": DB, "schema": SCHEMA, "table": "VW_TITLE_GAME_MAP"},
                "primary_key": {"columns": ["TITLE_ID"]},
                "dimensions": [
                    {"name": "MAP_TITLE_ID", "expr": "TITLE_ID", "data_type": "NUMBER(38,0)", "access_modifier": "public_access"},
                    {"name": "MAP_GAME_ID", "expr": "GAME_ID", "data_type": "NUMBER(38,0)", "access_modifier": "public_access"},
                    {"name": "MATCH_ROUTE", "expr": "MATCH_ROUTE", "data_type": "VARCHAR(16777216)",
                     "description": "STRONG = TITLES.CATALOG_GAME_ID, MEDIUM = TITLE_CODE_XREF, WEAK = name + release year.",
                     "access_modifier": "public_access"},
                ],
                "metrics": [
                    {"name": "MAPPED_TITLE_COUNT", "expr": "COUNT(title_game_map.TITLE_ID)", "access_modifier": "public_access"},
                ],
            }],
            # Imported side: logical dimension names (TITLES.TITLE_ID, GAMES.GAME_ID).
            # Local side: physical columns of VW_TITLE_GAME_MAP, as in the baseline YAML.
            "relationships": [
                {"name": "TITLE_TO_MAP", "left_table": "TITLES", "right_table": "TITLE_GAME_MAP",
                 "relationship_columns": [{"left_column": "TITLE_ID", "right_column": "TITLE_ID"}]},
                {"name": "MAP_TO_GAME", "left_table": "TITLE_GAME_MAP", "right_table": "GAMES",
                 "relationship_columns": [{"left_column": "GAME_ID", "right_column": "GAME_ID"}]},
            ],
        },
    }

    covered = [r["name"] for v in views.values() if v["name"] != "SV_GAMING_CROSS_DOMAIN_RESOLVED"
               for r in v.get("relationships", [])]
    assert sorted(covered) == sorted(rels), f"relationship coverage mismatch: {set(rels) ^ set(covered)}"

    OUT.mkdir(exist_ok=True)
    for fname, body in views.items():
        (OUT / fname).write_text(yaml.safe_dump(body, sort_keys=False, width=200))
        print(f"wrote {fname}: {len(body.get('tables', []))} tables, {len(body.get('relationships', []))} relationships")


if __name__ == "__main__":
    main()
