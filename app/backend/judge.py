"""Graded judge shared by Live mode (main.py) and the batch eval (scripts/batch_eval.py).

One AI_COMPLETE call scores both answers against the eval set's expected answer on the same
0 / 0.33 / 0.67 / 1 scale: amounts within 1% score 1.0,
within 3% score 0.67, more than 3% off score 0. correct >= 0.67, partial > 0, wrong = 0.
"""
import json

MODEL = "claude-sonnet-4-5"
PASS = 0.67
MAX_CHARS = 6000

PROMPT = """You grade two analytics agents that answered the same business question over the same data.
BASELINE only sees a semantic view. ONTOLOGY also searches a Business Ontology of governed definitions.
Score EACH answer independently against the EXPECTED ANSWER. First find the agent's MAIN answer (the headline
figure, count, name or list it gives as its answer, not alternatives or caveats). Compare every amount to the
expected amount as a percentage difference: |actual - expected| / expected.
Use exactly one of these scores:
- 1.0  correct: every headline amount is within 1% of expected, counts are exact, names and list members match.
       Extra context is fine if it does not contradict the answer.
- 0.67 mostly correct: headline amounts are within 3% of expected (but not all within 1%), OR the headline
       answer is fully correct but a secondary detail (ranking order, breakdown, game count) is wrong or missing.
- 0.33 partially correct: the expected answer appears only as an alternative or caveat, not as the main answer;
       or the right items appear inside a wrong list; or some required parts are right and others are wrong.
- 0.0  wrong: any headline amount is more than 3% from expected, a count or name is wrong, the main answer
       contradicts the expected answer, or the agent declined to answer.
A correct name or category with a headline amount more than 3% off is WRONG (0.0), not mostly correct.
If there is no expected answer, score both 0.0 and explain how the answers differ instead.
State the percentage difference of each headline amount in your reason.
Use the SQL to explain what each agent did (joins, filters, codes) and cite the NAIVE TRAP when it applies.
Respond in JSON.

QUESTION: {question}
EXPECTED ANSWER: {expected}
NAIVE TRAP: {trap}
ONTOLOGY NODES THAT FIX IT: {nodes}

BASELINE ANSWER:
{b_text}

BASELINE SQL:
{b_sql}

ONTOLOGY ANSWER:
{o_text}

ONTOLOGY SQL:
{o_sql}
"""

RESPONSE_FORMAT = """{'type': 'json', 'schema': {'type': 'object', 'properties': {
    'baseline_score': {'type': 'number'}, 'baseline_reason': {'type': 'string'},
    'ontology_score': {'type': 'number'}, 'ontology_reason': {'type': 'string'},
    'headline': {'type': 'string'}},
    'required': ['baseline_score', 'baseline_reason', 'ontology_score', 'ontology_reason', 'headline']}}"""

JUDGE_SQL = f"""SELECT AI_COMPLETE(
  model => %(model)s,
  prompt => %(prompt)s,
  model_parameters => {{'temperature': 0, 'max_tokens': 1500}},
  response_format => {RESPONSE_FORMAT}
) AS VERDICT"""


def _cut(s: str) -> str:
    return s if len(s) <= MAX_CHARS else s[:MAX_CHARS] + " ...[truncated]"


def build_prompt(question: dict, baseline: dict, ontology: dict) -> str:
    return PROMPT.format(
        question=question.get("question", ""),
        expected=question.get("expected") or "(none - free-text question)",
        trap=question.get("naive_trap") or "(none)",
        nodes=question.get("fixing_nodes") or "(none)",
        b_text=_cut(baseline.get("text", "")),
        b_sql=_cut("\n---\n".join(baseline.get("sql", [])) or "(none)"),
        o_text=_cut(ontology.get("text", "")),
        o_sql=_cut("\n---\n".join(ontology.get("sql", [])) or "(none)"),
    )


def parse_verdict(raw) -> dict:
    v = json.loads(raw) if isinstance(raw, str) else raw
    if isinstance(v, dict) and "structured_output" in v:
        v = v["structured_output"][0]["raw_message"]
    return v


def verdict(score):
    if score is None:
        return None
    return "correct" if score >= PASS else ("partial" if score > 0 else "wrong")


def judge(question: dict, baseline: dict, ontology: dict) -> dict:
    """Live mode: score both answers over the shared Live connection."""
    import sf
    cur = sf.get_connection().cursor()
    row = cur.execute(JUDGE_SQL, {"model": MODEL, "prompt": build_prompt(question, baseline, ontology)}).fetchone()
    v = parse_verdict(row[0])
    for side in ("baseline", "ontology"):
        v[f"{side}_verdict"] = verdict(v.get(f"{side}_score"))
    return v
