"""Parse documentation/ontology_eval_set.md into question records.

The eval file has two markdown tables:
  - Questions: | # | Question | Challenge | Expected answer | Naive trap | Ontology nodes that fix it |
  - Reference SQL: | # | Final SELECT |   (# may be "2, 3"; SQL may contain "||")

Usage: python3 questions.py <eval_set.md> <out.json>
"""
import json
import re
import sys
from pathlib import Path

ROW = re.compile(r"^\|\s*([\d, ]+?)\s*\|")


def _clean(cell: str) -> str:
    return cell.strip().replace("**", "").strip()


def parse(md: str) -> list[dict]:
    questions: dict[int, dict] = {}
    ref_sql: dict[int, str] = {}
    section = None
    for line in md.splitlines():
        if line.startswith("## "):
            section = line[3:].strip().lower()
            continue
        m = ROW.match(line)
        if not m:
            continue
        cells = line.strip().strip("|").split("|")
        if section == "questions" and len(cells) >= 6:
            qid = int(m.group(1))
            questions[qid] = {
                "id": qid,
                "question": _clean(cells[1]),
                "challenge": _clean(cells[2]),
                "expected": _clean(cells[3]),
                "naive_trap": _clean(cells[4]),
                "fixing_nodes": _clean("|".join(cells[5:])),
            }
        elif section and section.startswith("reference sql"):
            sql = "|".join(cells[1:]).strip().strip("`").strip()
            for part in m.group(1).split(","):
                if part.strip():
                    ref_sql[int(part)] = sql
    return [{**q, "reference_sql": ref_sql.get(qid, "")} for qid, q in sorted(questions.items())]


def main():
    src, out = Path(sys.argv[1]), Path(sys.argv[2])
    qs = parse(src.read_text())
    out.write_text(json.dumps(qs, indent=2, ensure_ascii=False))
    print(f"wrote {len(qs)} questions to {out}")


if __name__ == "__main__":
    main()
