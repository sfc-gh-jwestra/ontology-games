"""Deploy the cross-domain agents to ONTOLOGY_DEMO.CROSS_DOMAIN.

  agents/catalog_agent.yaml      -> GAMING_CATALOG_AGENT      (SV_GAME_CATALOG)
  agents/genre_agent.yaml        -> GAMING_GENRE_AGENT        (SV_GENRE_TAXONOMY)
  agents/sales_agent.yaml        -> GAMING_SALES_AGENT        (SV_GAME_COMMERCE)
  agents/crossdomain_agent.yaml  -> GAMING_CROSSDOMAIN_AGENT  (SV_GAMING_CROSS_DOMAIN)
  agents/router_agent.yaml       -> GAMING_ROUTER_AGENT       (agent_router over the four above)

The domain agents are created before the router, then USAGE is granted to ONTOLOGY_APP_ROLE.
Deploy the semantic views first (deploy.py).

Usage (from the repo root):  python3 cross-domain/deploy_agents.py [--connection JWESTRA_AWS1] [--dry-run]
"""
import argparse
import subprocess
from pathlib import Path

HERE = Path(__file__).parent
SCHEMA = "ONTOLOGY_DEMO.CROSS_DOMAIN"
APP_ROLE = "ONTOLOGY_APP_ROLE"
AGENTS = [  # create order: router last
    ("GAMING_CATALOG_AGENT", "catalog_agent.yaml", "Game Catalog domain agent over SV_GAME_CATALOG", "Gaming Catalog Agent"),
    ("GAMING_GENRE_AGENT", "genre_agent.yaml", "Genre Taxonomy domain agent over SV_GENRE_TAXONOMY", "Gaming Genre Agent"),
    ("GAMING_SALES_AGENT", "sales_agent.yaml", "Game Commerce domain agent over SV_GAME_COMMERCE", "Gaming Sales Agent"),
    ("GAMING_CROSSDOMAIN_AGENT", "crossdomain_agent.yaml", "Cross-domain agent over SV_GAMING_CROSS_DOMAIN", "Gaming Cross-domain Agent"),
    ("GAMING_ROUTER_AGENT", "router_agent.yaml", "Router: delegates to the catalog, genre, sales and cross-domain agents (agent_router)", "Gaming Router Agent"),
]


def lit(s):
    return "'" + s.replace("\\", "\\\\").replace("'", "''") + "'"


def build_sql():
    stmts = ["USE ROLE ACCOUNTADMIN;"]
    for name, fname, comment, display in AGENTS:
        spec = (HERE / "agents" / fname).read_text()
        assert "$$" not in spec, f"{fname} must not contain $$"
        profile = lit('{"display_name": "%s"}' % display)
        stmts.append(
            f"CREATE OR REPLACE AGENT {SCHEMA}.{name}\n"
            f"  COMMENT = {lit(comment)}\n"
            f"  PROFILE = {profile}\n"
            f"  FROM SPECIFICATION\n$$\n{spec}$$;"
        )
    stmts += [f"GRANT USAGE ON AGENT {SCHEMA}.{name} TO ROLE {APP_ROLE};" for name, *_ in AGENTS]
    stmts.append(f"SHOW AGENTS IN SCHEMA {SCHEMA};")
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
    out = HERE / ".deploy_agents.sql"
    out.write_text(sql)
    try:
        subprocess.run(["snow", "sql", "-c", args.connection, "-f", str(out)], check=True)
    finally:
        out.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
