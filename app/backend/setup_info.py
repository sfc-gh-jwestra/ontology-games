"""Setup tab content, built only from repo files (no Snowflake connection)."""
import importlib.util
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
CHALLENGES_MD = ROOT / "documentation" / "README_ontology_games_challenges.md"


def _load_ontology():
    spec = importlib.util.spec_from_file_location("build_ontology", ROOT / "scripts" / "build_ontology.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _semantic_views():
    out = []
    for f in sorted((ROOT / "semantic_views").glob("*.yaml")):
        text = f.read_text()
        m = re.match(r"# Semantic view (\S+)\n", text)
        d = yaml.safe_load(text)
        tables = [{"name": t["name"], "base": f"{t['base_table']['schema']}.{t['base_table']['table']}",
                   "description": t.get("description", "")} for t in d.get("tables", [])]
        out.append({"fqn": m.group(1) if m else d["name"], "name": d["name"], "file": f"semantic_views/{f.name}",
                    "description": d.get("description", ""), "tables": tables,
                    "imports": [f"{i['schema_name']}.{i['name']}" for i in d.get("imports", [])],
                    "relationships": len(d.get("relationships", []))})
    return out


def _agents():
    out = []
    for folder, group in (("agents", "demo"), ("agents/router", "router (optional)")):
        for f in sorted((ROOT / folder).glob("*.yaml")):
            text = f.read_text()
            spec = yaml.safe_load(text)
            tools = [t["tool_spec"]["name"] + " (" + t["tool_spec"]["type"] + ")" for t in spec.get("tools", [])]
            sv = [r["semantic_view"] for r in (spec.get("tool_resources") or {}).values()
                  if isinstance(r, dict) and r.get("semantic_view")]
            out.append({"name": f.stem, "fqn": f"ONTOLOGY_DEMO.AGENTS.{f.stem}", "group": group,
                        "file": f"{folder}/{f.name}", "tools": tools, "semantic_views": sv, "yaml": text})
    return out


def _challenges():
    return [{"id": f"C{m.group(1)}", "title": m.group(2).replace("*", "")}
            for m in re.finditer(r"^## Challenge (\d+): (.+)$", CHALLENGES_MD.read_text(), re.M)]


def _ontology():
    bo = _load_ontology()
    domains = []
    for name, desc in bo.DOMAINS:
        terms = [t for t in bo.TERMS if t[1] == name]
        kinds = {}
        for t in terms:
            kinds[t[2]] = kinds.get(t[2], 0) + 1
        domains.append({"name": name, "description": desc, "terms": len(terms), "kinds": kinds})
    return {"domains": domains, "terms": len(bo.TERMS), "relationships": len(bo.REL)}


def setup(questions: list[dict]) -> dict:
    return {"semantic_views": _semantic_views(), "agents": _agents(), "challenges": _challenges(),
            "ontology": _ontology(),
            "questions": [{k: q[k] for k in ("id", "question", "challenge", "expected")} for q in questions]}
