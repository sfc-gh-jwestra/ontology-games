"""Verdict on the two agent answers, grounded in the eval set's expected answer.

Runs one AI_COMPLETE call (structured JSON output, temperature 0) as the signed-in user.
"""
import json

from sf import Credential, sql_connection

MODEL = "claude-sonnet-4-5"
MAX_CHARS = 4000

JUDGE_SQL = """
SELECT AI_COMPLETE(
  model => %(model)s,
  prompt => %(prompt)s,
  model_parameters => {'temperature': 0, 'max_tokens': 1200},
  response_format => {
    'type': 'json',
    'schema': {
      'type': 'object',
      'properties': {
        'baseline_correct': {'type': 'boolean'},
        'ontology_correct': {'type': 'boolean'},
        'differ': {'type': 'boolean'},
        'headline': {'type': 'string'},
        'summary': {'type': 'string'},
        'evidence': {'type': 'array', 'items': {'type': 'string'}}
      },
      'required': ['baseline_correct', 'ontology_correct', 'differ', 'headline', 'summary', 'evidence']
    }
  }
) AS VERDICT
"""

PROMPT = """You are grading two analytics agents that answered the same business question over the same data.
The BASELINE agent only sees a semantic view. The ONTOLOGY agent also searches a Business Ontology of governed
definitions, synonyms, code mappings and identity rules. Respond in JSON.

Rules:
- If an EXPECTED ANSWER is given, an agent is correct only if its headline numbers or list match it
  (currency within $0.01, counts exact, lists same members). Approximate wording like "about $13.2M" is wrong
  when the expected value differs.
- Never say the ontology agent is correct unless its answer matches the expected answer. If both are wrong, say so.
- differ = true when the two agents reach different answers.
- headline: one sentence verdict, e.g. "The ontology agent is correct; the baseline was naive."
- summary: 2-4 sentences explaining WHY they differ, citing the specific trap (from NAIVE TRAP) and the concrete
  thing each agent did in its SQL (joins, filters, codes). Name the ontology nodes that fixed it when relevant.
- evidence: 2-4 short bullets quoting SQL fragments or numbers from the answers.
- If there is no expected answer, compare the two answers and explain the difference without declaring correctness
  beyond what the SQL shows (set both *_correct to false and say "no expected answer").

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


def _cut(s: str) -> str:
    return s if len(s) <= MAX_CHARS else s[:MAX_CHARS] + " ...[truncated]"


def build_prompt(question: dict, baseline: dict, ontology: dict) -> str:
    return PROMPT.format(
        question=question.get("question", ""),
        expected=question.get("expected") or "(none - free-text question)",
        trap=question.get("naive_trap") or "(none)",
        nodes=question.get("fixing_nodes") or "(none)",
        b_text=_cut(baseline.get("text", "")),
        b_sql=_cut("\n---\n".join(baseline.get("sql", []))),
        o_text=_cut(ontology.get("text", "")),
        o_sql=_cut("\n---\n".join(ontology.get("sql", []))),
    )


def judge(question: dict, baseline: dict, ontology: dict, cred: Credential) -> dict:
    prompt = build_prompt(question, baseline, ontology)
    with sql_connection(cred) as conn:
        row = conn.cursor().execute(JUDGE_SQL, {"model": MODEL, "prompt": prompt}).fetchone()
    raw = row[0]
    verdict = json.loads(raw) if isinstance(raw, str) else raw
    if isinstance(verdict, dict) and "structured_output" in verdict:
        verdict = verdict["structured_output"][0]["raw_message"]
    return verdict
