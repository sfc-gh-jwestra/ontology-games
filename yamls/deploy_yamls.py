"""Deploy the semantic view and agents in yamls/ to Snowflake.

  gaming_baseline_sv.yaml     -> ONTOLOGY_DEMO.ONTOLOGY_AGENTS.GAMING_BASELINE_SV   (SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML)
  gaming_baseline_agent.yaml  -> ONTOLOGY_DEMO.ONTOLOGY_AGENTS.GAMING_BASELINE_AGENT (CREATE AGENT ... FROM SPECIFICATION)
  gaming_bon_agent.yaml       -> ONTOLOGY_DEMO.ONTOLOGY_AGENTS.GAMING_BON_AGENT      (CREATE AGENT ... FROM SPECIFICATION)

Usage (from the repo root):  python3 yamls/deploy_yamls.py [--connection JWESTRA_AWS1] [--dry-run]
"""
import argparse
import subprocess
from pathlib import Path

HERE = Path(__file__).parent
SCHEMA = "ONTOLOGY_DEMO.ONTOLOGY_AGENTS"
AGENTS = [
    ("GAMING_BASELINE_AGENT", "gaming_baseline_agent.yaml",
     "Baseline: text-to-SQL over GAMING_BASELINE_SV only (no Business Ontology)", "Gaming Baseline Assistant"),
    ("GAMING_BON_AGENT", "gaming_bon_agent.yaml",
     "BON agent: native Business Ontology search + text-to-SQL over GAMING_BASELINE_SV", "Gaming BON Assistant"),
]


def lit(s):
    return "'" + s.replace("\\", "\\\\").replace("'", "''") + "'"


def build_sql():
    sv_yaml = (HERE / "gaming_baseline_sv.yaml").read_text()
    stmts = [
        f"CREATE SCHEMA IF NOT EXISTS {SCHEMA} "
        "COMMENT = 'Semantic view and agents used to test ONTOLOGY_DEMO with and without Business Ontology';",
        f"DROP SEMANTIC VIEW IF EXISTS {SCHEMA}.GAMING_BASELINE_SV;",
        f"CALL SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML({lit(SCHEMA)}, {lit(sv_yaml)});",
    ]
    for name, fname, comment, display in AGENTS:
        spec = (HERE / fname).read_text()
        assert "$$" not in spec, f"{fname} must not contain $$"
        profile = lit('{"display_name": "%s"}' % display)
        stmts.append(
            f"CREATE OR REPLACE AGENT {SCHEMA}.{name}\n"
            f"  COMMENT = {lit(comment)}\n"
            f"  PROFILE = {profile}\n"
            f"  FROM SPECIFICATION\n$$\n{spec}$$;"
        )
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
