"""Offline Live-mode preview: fake agents and judge, no Snowflake needed.

Run: bash app/dev.sh --mock   (or: cd app/backend && python3 dev_mock.py, plus `npm run dev` in frontend/)
Then open http://localhost:5173. Recorded mode, Setup and Analysis work the same as the real backend.
"""
import asyncio
import os
from pathlib import Path

HERE = Path(__file__).parent
os.environ.setdefault("STATIC_DIR", str(HERE.parent / "frontend" / "dist"))

import uvicorn  # noqa: E402

import main  # noqa: E402

ANSWERS = {
    "baseline": ("Action is the top genre, with about $13.2M in gross digital revenue, more than double Horror ($6.1M).",
                 ["query_data"], "SELECT ... JOIN titles ti ON r.title_id = ti.title_id -- catalog_game_id only"),
    "ontology": ("Action has the most revenue: $14,642,492.04 across 66 games. RPG is next at $13,436,693.28.",
                 ["query_data", "business_ontology"], "SELECT ... COALESCE(ti.catalog_game_id, xr.gid, nm.gid) ..."),
}


MOCK_ONTOLOGY = ("Found 3 object(s):\n\n1. Game Catalog.Game Identity Match Rule (TERM)\n   Name: Game Identity Match Rule\n"
                 "   Domain: Game Catalog\n   Definition: Match sales titles to games by catalog id, then crosswalk, then name.\n\n"
                 "2. Genre Taxonomy.Genre Roll-up Rule (TERM)\n   Name: Genre Roll-up Rule\n   Domain: Genre Taxonomy\n"
                 "   Definition: Roll sub-genres up to their parent genre.\n\n"
                 "3. Genre Taxonomy.Genre Revenue (METRIC)\n   Name: Genre Revenue\n   Domain: Genre Taxonomy\n"
                 "   Definition: Revenue by parent genre.\n   Formula: SUM(REVENUE_USD) GROUP BY parent genre\n")


async def fake_stream(side, question):
    text, tools, sql = ANSWERS[side]
    pace = 0.05 if side == "baseline" else 0.07
    yield "metadata", {"metadata": {"run_id": f"mock-{side}"}}
    yield "response.status", {"status": "planning", "message": "Planning the next steps"}
    await asyncio.sleep(1)
    yield "response.thinking.delta", {"text": f"The user asks: {question}. I should check the data model first."}
    for t in tools:
        yield "response.tool_use", {"name": t, "input": {}}
        await asyncio.sleep(1.5)
        yield "response.tool_result", {"name": t, "status": "success"}
    yield "response.tool_use", {"name": "system_execute_sql", "input": {"sql": sql}}
    await asyncio.sleep(1)
    for word in text.split(" "):
        await asyncio.sleep(pace)
        yield "response.text.delta", {"text": word + " "}
    content = [{"type": "tool_use", "tool_use": {"name": n, "type": "mock", "tool_use_id": n, "input": {}}} for n in tools]
    content += [{"type": "tool_result", "tool_result": {"name": n, "tool_use_id": n, "status": "success", "content":
                 [{"type": "json", "json": {"message": MOCK_ONTOLOGY}}] if n == "business_ontology" else []}}
                for n in tools]
    content += [{"type": "tool_use", "tool_use": {"name": "system_execute_sql", "type": "system_execute_sql",
                                                  "tool_use_id": "sql", "input": {"sql": sql}}},
                {"type": "tool_result", "tool_result": {"name": "system_execute_sql", "tool_use_id": "sql",
                                                        "status": "success", "content": []}},
                {"type": "text", "text": text}]
    yield "response", {"content": content, "status": "completed"}


def fake_judge(question, b, o):
    return {"baseline_score": 0.0, "baseline_verdict": "wrong", "ontology_score": 1.0, "ontology_verdict": "correct",
            "baseline_reason": "Mock: the baseline matched sales titles to games only by CATALOG_GAME_ID (8.4% low).",
            "ontology_reason": "Mock: the ontology agent applied the Game Identity Match Rule and the Genre Roll-up Rule.",
            "headline": "Mock verdict: the ontology agent is correct; the baseline was naive.",
            "ontology_contributions": [
                {"node": "Game Identity Match Rule", "how": "Mock: COALESCE over catalog id, crosswalk and name matched every title."},
                {"node": "Genre Roll-up Rule", "how": "Mock: rolled sub-genres up to Action before summing."}]}


main.agents.stream_agent = fake_stream
main.judge.judge = fake_judge

if __name__ == "__main__":
    uvicorn.run(main.app, host="127.0.0.1", port=8080)
