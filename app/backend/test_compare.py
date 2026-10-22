"""Offline test of the merged compare stream: fake agent streams, fake judge, no Snowflake."""
import asyncio
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
os.environ.setdefault("SNOWFLAKE_ACCOUNT_URL", "https://example.invalid")
os.environ.setdefault("APP_ROLES", "ONTOLOGY_APP_ROLE")

import agents  # noqa: E402
import judge  # noqa: E402
import main  # noqa: E402

REAL_STREAM_AGENT = agents.stream_agent  # test_merged_stream swaps in a fake


async def fake_stream(client, side, question, cred):
    delay = 0.01 if side == "baseline" else 0.02
    yield "metadata", {"metadata": {"run_id": f"{side}-1"}}
    yield "response.status", {"status": "planning", "message": "Planning"}
    for word in ("Action ", "is ", "top."):
        await asyncio.sleep(delay)
        yield "response.text.delta", {"text": word}
    yield "response.tool_use", {"name": "query_data", "input": {"sql": f"SELECT 1 -- {side}"}}
    yield "response", {"content": [{"type": "text", "text": f"{side} answer"},
                                   {"type": "tool_use", "tool_use": {"name": "system_execute_sql",
                                                                    "input": {"sql": f"SELECT 1 -- {side}"}}}],
                       "status": "completed"}


def test_merged_stream():
    agents.stream_agent = fake_stream
    main.agents.stream_agent = fake_stream
    judge.judge = lambda q, b, o, cred: {"differ": True, "headline": "ok", "b": b["text"], "o": o["text"]}
    main.judge.judge = judge.judge
    main.oauth.credential = lambda request: None

    async def run():
        chunks = [c async for c in main._compare_stream(main.BY_ID[21], None, "cid", None)]
        events = [json.loads(c.decode().split("data: ", 1)[1]) for c in chunks if c.startswith(b"event:")]
        return events

    events = asyncio.run(run())
    types = [(e.get("side"), e["type"]) for e in events]
    assert types[0] == (None, "start") and types[-1] == (None, "done")
    for side in ("baseline", "ontology"):
        assert (side, "final") in types and (side, "text") in types
    text = {s: "".join(e["text"] for e in events if e.get("side") == s and e["type"] == "text") for s in ("baseline", "ontology")}
    assert text == {"baseline": "Action is top.", "ontology": "Action is top."}
    verdict = next(e for e in events if e["type"] == "verdict")["verdict"]
    assert verdict["b"] == "baseline answer" and verdict["o"] == "ontology answer"
    # Both sides interleave (ran concurrently), not one after the other.
    sides = [e["side"] for e in events if e["type"] == "text"]
    assert sides != sorted(sides, key=lambda s: s != "baseline")


def test_sql_agent_run():
    """stream_agent over a fake SQL connection: async query, polling, replayed events, final."""
    import sf
    response = {"content": [
        {"type": "thinking", "thinking": {"text": "plan"}},
        {"type": "tool_use", "tool_use": {"name": "system_execute_sql", "input": {"sql": "SELECT 3"}}},
        {"type": "tool_result", "tool_result": {"name": "system_execute_sql", "status": "success"}},
        {"type": "text", "text": "Total is $3."}], "status": "completed"}
    seen = {}

    class Cur:
        sfqid = "q1"
        def execute_async(self, sql, args): seen["sql"], seen["args"] = sql, args
        def get_results_from_sfqid(self, qid): seen["qid"] = qid
        def fetchone(self): return [json.dumps(response)]
        def execute(self, *a): seen["cancel"] = a

    class Conn:
        polls = iter([True, False])
        def cursor(self): return Cur()
        def get_query_status_throw_if_error(self, qid): return next(self.polls)
        def is_still_running(self, status): return status
        def close(self): seen["closed"] = True

    real_conn = agents.sql_connection
    agents.sql_connection = lambda cred: Conn()
    agents.POLL_SECS = 0
    try:
        async def run():
            return [e async for e in REAL_STREAM_AGENT(None, "ontology", "q?", sf.Credential("t", "OAUTH", True))]
        events = asyncio.run(run())
    finally:
        agents.sql_connection = real_conn
    names = [e for e, _ in events]
    assert names == ["response.status", "metadata", "response.thinking.delta", "response.tool_use",
                     "response.tool_result", "response.text.delta", "response"]
    assert seen["args"][0] == "ONTOLOGY_DEMO.ONTOLOGY_AGENTS.GAMING_BON_AGENT" and seen["closed"]
    assert json.loads(seen["args"][1])["stream"] is False
    final = agents.summarize_final(events[-1][1])
    assert final["text"] == "Total is $3." and final["sql"] == ["SELECT 3"]


def test_summarize_final():
    s = agents.summarize_final({"content": [
        {"type": "text", "text": "A"},
        {"type": "tool_use", "tool_use": {"name": "business_ontology", "input": {"query": "q"}}},
        {"type": "tool_result", "tool_result": {"name": "business_ontology", "content": [
            {"type": "text", "text": "1. Genre Taxonomy.Genre Revenue (METRIC)\n2. Game Catalog.Game Identity Match Rule (TERM)"}]}},
        {"type": "tool_use", "tool_use": {"name": "system_execute_sql", "input": {"sql": "SELECT 2"}}},
    ], "status": "completed"})
    assert s["text"] == "A" and s["sql"] == ["SELECT 2"]
    assert s["ontology_hits"] == ["Genre Revenue", "Game Identity Match Rule"]


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("PASS", name)
