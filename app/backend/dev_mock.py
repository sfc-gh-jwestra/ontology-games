"""Offline UI preview: fake streaming agents, fake sign-in, /api/me and judge. No Snowflake needed.

Run: bash app/dev.sh --mock   (or: cd app/backend && python3 dev_mock.py, plus `npm run dev` in frontend/)
Then open http://localhost:5173
"""
import asyncio
import os
from pathlib import Path

HERE = Path(__file__).parent
os.environ.setdefault("SNOWFLAKE_ACCOUNT_URL", "https://mock.invalid")
os.environ.setdefault("APP_ROLES", "ONTOLOGY_APP_ROLE")
os.environ.setdefault("APP_DEFAULT_ROLE", "ONTOLOGY_APP_ROLE")
os.environ.setdefault("STATIC_DIR", str(HERE.parent / "frontend" / "dist"))

import uvicorn  # noqa: E402

import main  # noqa: E402
from sf import Credential  # noqa: E402

ANSWERS = {
    "baseline": ("Action is the top genre, with about $13.2M in gross digital revenue, more than double Horror ($6.1M).",
                 ["query_data"], "SELECT ... JOIN titles ti ON r.title_id = ti.title_id -- catalog_game_id only"),
    "ontology": ("Action has the most revenue: $14,642,492.04 across 66 games. RPG is next at $13,436,693.28 "
                 "(RPG + Roguelike + ActionRPG + Soulslike).",
                 ["business_ontology", "query_data"], "SELECT ... COALESCE(ti.catalog_game_id, xr.gid, nm.gid) ..."),
}


async def fake_stream(client, side, question, cred):
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
    hits = "1. Genre Taxonomy.Genre Revenue (METRIC) 2. Genre Taxonomy.Genre Roll-up Rule (TERM)" if side == "ontology" else ""
    content = [{"type": "tool_use", "tool_use": {"name": n, "input": {}}} for n in tools]
    if hits:
        content.append({"type": "tool_result", "tool_result": {"name": "business_ontology",
                                                               "content": [{"type": "text", "text": hits}]}})
    content += [{"type": "tool_use", "tool_use": {"name": "system_execute_sql", "input": {"sql": sql}}},
                {"type": "text", "text": text}]
    yield "response", {"content": content, "status": "completed"}


def fake_judge(question, b, o, cred=None):
    return {"baseline_correct": False, "ontology_correct": True, "differ": True,
            "headline": "The ontology agent is correct; the baseline was naive.",
            "summary": "The baseline matched sales titles to games only by CATALOG_GAME_ID, dropping titles that "
                       "resolve only via the title-code crosswalk or name + year. The ontology agent applied the "
                       "Game Identity Match Rule and the Genre Roll-up Rule.",
            "evidence": ["Baseline SQL: catalog_game_id only", "Ontology SQL: COALESCE(catalog_game_id, xref, name+year)"]}


main.agents.stream_agent = fake_stream
main.judge.judge = fake_judge
main.oauth.credential = lambda request: Credential("mock", "OAUTH", True)
main.app.router.routes = [r for r in main.app.router.routes if getattr(r, "path", "") != "/api/me"]


@main.app.get("/api/me")
def fake_me():
    return {"user": "JWESTRA", "role": "ONTOLOGY_APP_ROLE", "secondary_roles": "", "warehouse": "COMPUTE_WH"}


# Re-append the SPA catch-all so it stays last.
spa = [r for r in main.app.router.routes if getattr(r, "path", "") == "/{path:path}"]
main.app.router.routes = [r for r in main.app.router.routes if r not in spa] + spa

if __name__ == "__main__":
    uvicorn.run(main.app, host="127.0.0.1", port=8080)
