"""Batch eval: run every question in documentation/ontology/ontology_eval_set.md through both agents and grade the answers.

For each question and agent it records the answer, every tool call in order (name, type, status), the SQL
executed, token usage and elapsed time. An AI_COMPLETE judge then scores each answer on the same 0 / 0.33 / 0.67 / 1
scale (correct >= 0.67, partial > 0, wrong = 0).

Writes evaluations/results/<run_id>.json (+ latest.json) and a Markdown summary grouped by challenge C1-C7.

Usage (repo root): python3 scripts/batch_eval.py [--connection NAME] [--role ROLE] [--only 1,5,7] [--workers 4]
                   python3 scripts/batch_eval.py --summarize evaluations/results/latest.json   (rebuild the .md only)
                   python3 scripts/batch_eval.py --rejudge evaluations/results/latest.json     (judge recorded answers again)
Connection defaults to SNOWFLAKE_CONNECTION_NAME, then ONTOLOGY_DEMO_CONN.
"""
import argparse
import concurrent.futures as cf
import datetime as dt
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVAL_MD = ROOT / "documentation" / "ontology" / "ontology_eval_set.md"
OUT = ROOT / "evaluations" / "results"
AGENTS = {"baseline": "ONTOLOGY_DEMO.AGENTS.GAMING_BASELINE_AGENT", "ontology": "ONTOLOGY_DEMO.AGENTS.GAMING_BON_AGENT"}
BACKEND = ROOT / "app" / "backend"
sys.path.insert(0, str(BACKEND))
import agents as live_agents  # noqa: E402  shared response parser (same fields as Live mode)
import judge as shared_judge  # noqa: E402  shared graded judge (same rubric as Live mode)
import ontology_trace  # noqa: E402  how the ontology contributed (same as Live mode)

JUDGE_MODEL = shared_judge.MODEL
PASS = shared_judge.PASS


def load_questions():
    import questions
    return questions.parse(EVAL_MD.read_text())


def lit(s):
    return "'" + s.replace("\\", "\\\\").replace("'", "''") + "'"


def snow(sql, args, retries=3):
    cmd = ["snow", "sql", "-c", args.connection, "--role", args.role, "--warehouse", args.warehouse,
           "--enable-templating", "NONE", "--format", "json", "-q", sql]
    for attempt in range(retries):
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
        if p.returncode == 0:
            return json.loads(p.stdout)
        if attempt == retries - 1:
            raise RuntimeError((p.stderr or p.stdout)[-600:])
        time.sleep(5 * (attempt + 1))  # parallel logins sometimes fail to connect; back off and retry


def run_agent(side, question, args):
    body = json.dumps({"messages": [{"role": "user", "content": [{"type": "text", "text": question}]}]},
                      ensure_ascii=False)
    start = time.monotonic()
    rows = snow(f"SELECT SNOWFLAKE.CORTEX.DATA_AGENT_RUN('{AGENTS[side]}', {lit(body)}) AS R", args)
    elapsed = round(time.monotonic() - start, 1)
    return dict(live_agents.parse_response(json.loads(rows[0]["R"])), elapsed=elapsed)


def judge(q, b, o, args):
    prompt = shared_judge.build_prompt(q, b, o)
    sql = shared_judge.JUDGE_SQL.replace("%(model)s", lit(JUDGE_MODEL)).replace("%(prompt)s", lit(prompt))
    return shared_judge.keep_retrieved(shared_judge.parse_verdict(snow(sql, args)[0]["VERDICT"]), o)


verdict = shared_judge.verdict


def challenge_key(tag):
    m = re.search(r"\bC(\d)\b", tag)
    return (int(m.group(1)) if m else 9, 1 if tag.startswith("control") else 0)


def evaluate(q, args, recorded=None):
    answers = {}
    for side in AGENTS:
        if recorded:
            answers[side] = recorded["answers"][side]
            continue
        try:
            answers[side] = run_agent(side, q["question"], args)
        except Exception as exc:
            answers[side] = {"text": f"ERROR: {exc}", "status": "error", "elapsed": 0, "tokens": {}, "steps": [],
                             "tool_calls": 0, "tool_counts": {}, "sql": []}
    try:
        v = judge(q, answers["baseline"], answers["ontology"], args)
    except Exception as exc:
        v = {"headline": f"judge failed: {exc}"}
    for side in AGENTS:
        s = v.get(f"{side}_score")
        answers[side].update(score=s, verdict=verdict(s), judge_reason=v.get(f"{side}_reason"))
    answers["ontology"]["ontology_trace"] = ontology_trace.contribution(q, answers["ontology"], v)
    print(f"  Q{q['id']:>2}  baseline {answers['baseline']['score']}  ontology {answers['ontology']['score']}", flush=True)
    return {"id": q["id"], "challenge": q["challenge"], "question": q["question"], "expected": q["expected"],
            "naive_trap": q["naive_trap"], "headline": v.get("headline"), "answers": answers}


def summary_md(run):
    lines = [f"# Batch eval {run['run_id']}", "",
             f"Judge: {run['judge_model']} (AI_COMPLETE), scores 0 / 0.33 / 0.67 / 1; correct >= {PASS}.", ""]
    tot = {s: {"correct": 0, "partial": 0, "wrong": 0, "score": 0.0} for s in AGENTS}
    lines += ["| Challenge | Q | Question | Baseline | Ontology | Baseline tools | Ontology tools |",
              "|---|---|---|---|---|---|---|"]
    for r in sorted(run["results"], key=lambda r: (challenge_key(r["challenge"]), r["id"])):
        cells = []
        for s in AGENTS:
            a = r["answers"][s]
            if a["verdict"]:
                tot[s][a["verdict"]] += 1
                tot[s]["score"] += a["score"]
            cells.append(f"{a['score']} {a['verdict'] or 'n/a'}")
        tools = [", ".join(f"{k} x{v}" for k, v in r["answers"][s]["tool_counts"].items()) or "none" for s in AGENTS]
        lines.append(f"| {r['challenge']} | {r['id']} | {r['question']} | {cells[0]} | {cells[1]} | {tools[0]} | {tools[1]} |")
    lines += ["", "| Agent | Correct | Partial | Wrong | Mean score |", "|---|---|---|---|---|"]
    n = len(run["results"])
    for s in AGENTS:
        t = tot[s]
        lines.append(f"| {s} | {t['correct']}/{n} | {t['partial']} | {t['wrong']} | {t['score'] / n:.2f} |")
    lines += ["", "## Why answers failed", "",
              "Every answer that was not correct, grouped by challenge, with the judge's reason and the SQL it ran.", ""]
    current = None
    for r in sorted(run["results"], key=lambda r: (challenge_key(r["challenge"]), r["id"])):
        misses = [(s, r["answers"][s]) for s in AGENTS if r["answers"][s]["verdict"] != "correct"]
        if not misses:
            continue
        group = f"C{challenge_key(r['challenge'])[0]}"
        if group != current:
            lines += [f"### {group}", ""]
            current = group
        lines += [f"#### Q{r['id']}. {r['question']}", "",
                  f"- **Challenge:** {r['challenge']}", f"- **Expected:** {r['expected']}",
                  f"- **Judge headline:** {r['headline']}", ""]
        for s, a in misses:
            tools = ", ".join(f"{k} x{v}" for k, v in a["tool_counts"].items()) or "none"
            lines += [f"**{s.capitalize()}: {a['score']} ({a['verdict']})**", "",
                      f"{a['judge_reason']}", "", f"Tools: {tools}", ""]
            for sql in a["sql"]:
                lines += ["```sql", sql.strip(), "```", ""]
    lines += ontology_md(run)
    return "\n".join(lines) + "\n"


STATUS_MD = {"applied": "applied", "via": "applied via", "retrieved": "retrieved only", "missed": "missed"}


def ontology_md(run):
    """'How the ontology helped': applied nodes, expected coverage and relationships, grouped by challenge."""
    rows = [r for r in run["results"] if r["answers"]["ontology"].get("ontology_trace")]
    if not rows:
        return []
    lines = ["", "## How the ontology helped", "",
             "For each question: the ontology nodes the judge says the agent applied and how, which expected nodes "
             "were applied, only retrieved, or missed, and the relationships between them.", ""]
    current = None
    for r in sorted(rows, key=lambda r: (challenge_key(r["challenge"]), r["id"])):
        t, a = r["answers"]["ontology"]["ontology_trace"], r["answers"]["ontology"]
        group = f"C{challenge_key(r['challenge'])[0]}"
        if group != current:
            lines += [f"### {group}", ""]
            current = group
        cov = t["coverage"]
        lines += [f"#### Q{r['id']}. {r['question']}", "",
                  f"Ontology score {a['score']} ({a['verdict']}). Expected nodes applied: {cov['applied']}/{cov['expected']}"
                  f" (directly {cov.get('direct', cov['applied'])}, via another node {cov.get('via', 0)}; retrieved but not applied: {cov['retrieved']}).", ""]
        for n in t["applied"]:
            formula = f" Formula: `{n['formula']}`." if n.get("formula") else ""
            lines.append(f"- **{n['name']}** ({n['label']}): {n['how']}{formula}")
        if not t["applied"]:
            lines.append("- No ontology node was applied.")
        lines.append("- Expected: " + ", ".join(f"{e['name']} ({STATUS_MD[e['status']]}{' ' + e['via'] if e.get('via') else ''})"
                                               for e in t["expected"]))
        if t["relationships"]:
            lines.append("- Relationships: " + "; ".join(f"{e['source']} -> {e['type']} -> {e['target']}"
                                                        for e in t["relationships"]))
        lines.append("")
    return lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--connection", default=os.getenv("SNOWFLAKE_CONNECTION_NAME", "ONTOLOGY_DEMO_CONN"))
    ap.add_argument("--role", default="ONTOLOGY_APP_ROLE")
    ap.add_argument("--warehouse", default="COMPUTE_WH")
    ap.add_argument("--only", help="comma-separated question ids")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--summarize", metavar="RUN_JSON", help="only rebuild the Markdown summary from a results file")
    ap.add_argument("--rejudge", metavar="RUN_JSON", help="judge the recorded answers again (no agent runs), as a new run")
    args = ap.parse_args()
    if args.summarize:
        run = json.loads(Path(args.summarize).read_text())
        (OUT / f"{run['run_id']}.md").write_text(summary_md(run))
        print(f"Wrote evaluations/results/{run['run_id']}.md")
        return
    qs = load_questions()
    if args.only:
        keep = {int(x) for x in args.only.split(",")}
        qs = [q for q in qs if q["id"] in keep]
    run_id = dt.datetime.now().strftime("%Y%m%d_%H%M")
    if args.rejudge:
        old = {r["id"]: r for r in json.loads(Path(args.rejudge).read_text())["results"]}
        qs = [q for q in qs if q["id"] in old]
        print(f"Re-judge {run_id}: {len(qs)} recorded questions")
        with cf.ThreadPoolExecutor(args.workers) as ex:
            results = list(ex.map(lambda q: evaluate(q, args, old[q["id"]]), qs))
    else:
        print(f"Batch eval {run_id}: {len(qs)} questions x {len(AGENTS)} agents")
        with cf.ThreadPoolExecutor(args.workers) as ex:
            results = list(ex.map(lambda q: evaluate(q, args), qs))
    run = {"run_id": run_id, "judge_model": JUDGE_MODEL, "pass_threshold": PASS, "agents": AGENTS, "role": args.role,
           "results": sorted(results, key=lambda r: r["id"])}
    OUT.mkdir(parents=True, exist_ok=True)
    for name in (f"{run_id}.json", "latest.json"):
        (OUT / name).write_text(json.dumps(run, indent=1, ensure_ascii=False))
    md = summary_md(run)
    (OUT / f"{run_id}.md").write_text(md)
    print("\n" + md)


if __name__ == "__main__":
    main()
