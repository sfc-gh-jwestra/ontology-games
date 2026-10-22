from pathlib import Path

from questions import parse

EVAL = Path(__file__).resolve().parents[2] / "ontology_setup" / "ontology_eval_set.md"


def test_parses_all_questions():
    qs = parse(EVAL.read_text())
    assert len(qs) == 23
    assert [q["id"] for q in qs] == list(range(1, 24))


def test_q21_expected_and_sql():
    q21 = {q["id"]: q for q in parse(EVAL.read_text())}[21]
    assert q21["question"] == "Which genre has the most revenue?"
    assert "14,642,492.04" in q21["expected"]
    assert "VW_GAME_GENRE_ROLLUP" in q21["reference_sql"]


def test_shared_reference_sql_and_pipes():
    qs = {q["id"]: q for q in parse(EVAL.read_text())}
    assert qs[2]["reference_sql"] == qs[3]["reference_sql"] != ""
    assert "||" in qs[19]["reference_sql"]
