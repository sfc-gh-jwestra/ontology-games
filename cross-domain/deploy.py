"""Deploy the cross-domain composable semantic views to ONTOLOGY_DEMO.CROSS_DOMAIN.

Order matters because composed views resolve imports by name:
  schema -> VW_TITLE_GAME_MAP -> SV_GAME_CATALOG -> SV_GENRE_TAXONOMY -> SV_GAME_COMMERCE
         -> SV_GAMING_CROSS_DOMAIN -> SV_GAMING_CROSS_DOMAIN_RESOLVED -> grants
Existing semantic views are dropped in reverse order first.

Usage (from the repo root):  python3 cross-domain/deploy.py [--connection JWESTRA_AWS1] [--dry-run]
Run build_yamls.py first if the baseline YAML changed.
"""
import argparse
import subprocess
from pathlib import Path

HERE = Path(__file__).parent
SCHEMA = "ONTOLOGY_DEMO.CROSS_DOMAIN"
VIEWS = [  # create order
    ("SV_GAME_CATALOG", "sv_game_catalog.yaml"),
    ("SV_GENRE_TAXONOMY", "sv_genre_taxonomy.yaml"),
    ("SV_GAME_COMMERCE", "sv_game_commerce.yaml"),
    ("SV_GAMING_CROSS_DOMAIN", "sv_gaming_cross_domain.yaml"),
    ("SV_GAMING_CROSS_DOMAIN_RESOLVED", "sv_gaming_cross_domain_resolved.yaml"),
]


def lit(s):
    return "'" + s.replace("\\", "\\\\").replace("'", "''") + "'"


def build_sql():
    stmts = [
        "USE ROLE ACCOUNTADMIN;",
        f"CREATE SCHEMA IF NOT EXISTS {SCHEMA} "
        "COMMENT = 'Composable semantic views split by Business Ontology domain (cross-domain/ subproject)';",
    ]
    stmts += [f"DROP SEMANTIC VIEW IF EXISTS {SCHEMA}.{name};" for name, _ in reversed(VIEWS)]
    stmts.append((HERE / "sql" / "vw_title_game_map.sql").read_text().strip())
    for _, fname in VIEWS:
        stmts.append(f"CALL SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML({lit(SCHEMA)}, {lit((HERE / 'yamls' / fname).read_text())});")
    stmts.append((HERE / "sql" / "grants.sql").read_text().strip())
    stmts.append(f"SHOW SEMANTIC VIEWS IN SCHEMA {SCHEMA};")
    return "\n\n".join(stmts) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--connection", default="JWESTRA_AWS1")
    ap.add_argument("--dry-run", action="store_true", help="print the SQL instead of running it")
    args = ap.parse_args()
    sql = build_sql()
    if args.dry_run:
        print(sql)
        return
    out = HERE / ".deploy.sql"
    out.write_text(sql)
    try:
        subprocess.run(["snow", "sql", "-c", args.connection, "-f", str(out)], check=True)
    finally:
        out.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
