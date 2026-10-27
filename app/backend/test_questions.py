from pathlib import Path

from questions import parse

EVAL = Path(__file__).resolve().parents[2] / "documentation" / "ontology_eval_set.md"


def test_parses_all_questions():
    qs = parse(EVAL.read_text())
    assert len(qs) == 13
    assert [q["id"] for q in qs] == list(range(1, 14))


def test_genre_question_expected_and_sql():
    q7 = {q["id"]: q for q in parse(EVAL.read_text())}[7]
    assert q7["question"] == "Which genre has the most revenue?"
    assert "14,642,492.04" in q7["expected"]
    assert "VW_GAME_GENRE_ROLLUP" in q7["reference_sql"]


def test_every_question_has_reference_sql():
    qs = parse(EVAL.read_text())
    assert all(q["reference_sql"] for q in qs)
    assert {q["id"]: q for q in qs}[10]["question"] == "What was console revenue in North America?"
