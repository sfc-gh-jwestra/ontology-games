"""How the Business Ontology contributed to one ontology-agent answer.

Shared by Live mode (main.py) and the batch eval. Combines three things:
- applied: nodes the judge says the agent used (validated against what the search returned), with kind/formula
- expected: the eval set's fixing nodes, each marked applied, applied via another node (its logic is in the
  answer or SQL but another node carried it), retrieved only, or missed (logic absent)
- relationships: ontology edges (scripts/build_ontology.py REL) between the nodes in play
"""
import importlib.util
import re
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MAX_EDGES = 12


@lru_cache(maxsize=1)
def _ontology():
    spec = importlib.util.spec_from_file_location("build_ontology", ROOT / "scripts" / "build_ontology.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def kind_label(name: str, kind: str) -> str:
    if kind == "ENTITY":
        return "Class"
    if kind == "METRIC":
        return "Metric"
    return "Rule" if name.endswith("Rule") else "Term"


def _known() -> dict:
    """lower(name) -> {name, kind, domain, definition, formula} for every ontology node."""
    out = {}
    for t in _ontology().TERMS:
        out[t[0].lower()] = {"name": t[0], "domain": t[1], "kind": t[2], "synonyms": list(t[3]),
                             "definition": t[4][:500], "formula": t[5] if len(t) > 5 else ""}
    return out


def expected_names(fixing_nodes: str) -> list[str]:
    """'Game Revenue (route split); Title Code; RPG term' -> ontology node names (unknown text kept as-is)."""
    known = _known()
    out = []
    for part in (fixing_nodes or "").split(";"):
        name = part.split("(")[0].strip().strip("`")
        if not name:
            continue
        if name.lower() not in known and name.lower().endswith(" term"):
            name = name[:-5].strip()
        out.append(known.get(name.lower(), {"name": name})["name"])
    return list(dict.fromkeys(out))


def contribution(question: dict, answer: dict, verdict: dict) -> dict:
    known = _known()
    retrieved = {n["name"]: n for n in answer.get("ontology_retrieved") or []}
    applied = []
    for c in verdict.get("ontology_contributions") or []:
        base = known.get(c["node"].lower(), {})
        n = {**base, **{k: v for k, v in (retrieved.get(c["node"]) or {}).items() if v}} or {"name": c["node"]}
        applied.append({"name": n["name"], "kind": n.get("kind", "TERM"), "label": kind_label(n["name"], n.get("kind", "")),
                        "how": c.get("how", ""), "formula": n.get("formula", ""), "definition": n.get("definition", ""),
                        "domain": n.get("domain", "")})
    applied_names = {a["name"] for a in applied}

    logic = {}
    for item in verdict.get("expected_logic") or []:
        key = re.sub(r"\s*\(.*$", "", str(item.get("node", ""))).strip().lower()
        logic[key] = item

    expected = []
    for name in expected_names(question.get("fixing_nodes", "")):
        item = logic.get(name.lower()) or {}
        via, evidence = "", item.get("evidence", "")
        if name in applied_names:
            status = "applied"
        elif item.get("present"):
            # The logic is in the answer/SQL, carried by another node (e.g. Game Revenue's resolved-game formula).
            status, via = "via", item.get("via") or "SQL"
            if via == name:
                status, via = "applied", ""
        elif name in retrieved:
            status = "retrieved"
        else:
            status = "missed"
        expected.append({"name": name, "status": status, "via": via, "evidence": evidence,
                         "in_ontology": name.lower() in known})

    focus = applied_names | {e["name"] for e in expected if e["status"] != "missed"}
    in_play = focus | set(retrieved)
    edges = [{"source": s, "type": typ, "target": t} for s, t, typ in _ontology().REL
             if (s in focus and t in in_play) or (t in focus and s in in_play)]
    edges.sort(key=lambda e: (e["source"] not in applied_names and e["target"] not in applied_names))

    count = {s: sum(e["status"] == s for e in expected) for s in ("applied", "via", "retrieved", "missed")}
    return {"applied": applied, "expected": expected, "relationships": edges[:MAX_EDGES],
            "retrieved": [{"name": n["name"], "label": kind_label(n["name"], n.get("kind", ""))} for n in retrieved.values()],
            # applied counts logic carried by another node too; "direct" is the node itself.
            "coverage": {"applied": count["applied"] + count["via"], "direct": count["applied"], "via": count["via"],
                         "retrieved": count["retrieved"], "missed": count["missed"], "expected": len(expected)}}
