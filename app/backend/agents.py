"""Run a Cortex Agent with SNOWFLAKE.CORTEX.DATA_AGENT_RUN over the shared Live connection (sf.py).

DATA_AGENT_RUN returns the whole response at once, so there is no token-by-token streaming: this
module emits a "planning" status, then replays the finished response as (event_name, data) pairs,
ending with `response`. parse_response() is shared with scripts/batch_eval.py, so Live and Recorded
answers carry the same fields (steps, tool counts, SQL, tokens).
"""
import asyncio
import json
import re
from typing import AsyncIterator

import sf

DB, SCHEMA = "ONTOLOGY_DEMO", "AGENTS"
AGENTS = {"baseline": "GAMING_BASELINE_AGENT", "ontology": "GAMING_BON_AGENT"}
POLL_SECS = 1.0
RUN_SQL = "SELECT SNOWFLAKE.CORTEX.DATA_AGENT_RUN(%s, %s)"


async def stream_agent(side: str, question: str) -> AsyncIterator[tuple[str, dict]]:
    yield "response.status", {"status": "planning", "message": "Running agent"}
    body = json.dumps({"messages": [{"role": "user", "content": [{"type": "text", "text": question}]}],
                       "stream": False})
    conn, qid = None, None
    try:
        conn = await asyncio.to_thread(sf.get_connection)
        cur = conn.cursor()
        await asyncio.to_thread(cur.execute_async, RUN_SQL, (f"{DB}.{SCHEMA}.{AGENTS[side]}", body))
        qid = cur.sfqid
        yield "metadata", {"metadata": {"run_id": qid}}
        while conn.is_still_running(await asyncio.to_thread(conn.get_query_status_throw_if_error, qid)):
            await asyncio.sleep(POLL_SECS)
        await asyncio.to_thread(cur.get_results_from_sfqid, qid)
        raw = (await asyncio.to_thread(cur.fetchone))[0]
        qid = None  # finished; nothing to cancel
    except asyncio.CancelledError:
        if conn is not None and qid:
            await asyncio.to_thread(_cancel_on, conn, qid)
        raise
    except Exception as exc:
        if "expired" in str(exc).lower():
            sf.reset()  # the next Live run reconnects
        yield "error", {"message": str(exc)}
        return

    response = json.loads(raw) if isinstance(raw, str) else raw
    if not response.get("content") and (response.get("message") or response.get("code")):
        yield "error", {"message": f"{response.get('code', '')} {response.get('message', '')}".strip()}
        return
    for event in _replay(response):
        yield event


def _replay(response: dict):
    """Turn the finished response into the step/text events the UI renders while it waits."""
    for item in response.get("content", []):
        kind = item.get("type")
        if kind == "thinking":
            yield "response.thinking.delta", {"text": (item.get("thinking") or {}).get("text", "")}
        elif kind == "tool_use":
            tu = item.get("tool_use", {})
            yield "response.tool_use", {"name": tu.get("name"), "input": tu.get("input") or {}}
        elif kind == "tool_result":
            tr = item.get("tool_result", {})
            yield "response.tool_result", {"name": tr.get("name"), "status": tr.get("status")}
        elif kind == "text":
            yield "response.text.delta", {"text": item.get("text", "")}
    yield "response", response


def _cancel_on(conn, qid: str) -> None:
    try:
        conn.cursor().execute("SELECT SYSTEM$CANCEL_QUERY(%s)", (qid,))
    except Exception:
        pass


async def cancel_run(run_id: str) -> None:
    """Cancel a running DATA_AGENT_RUN query by its query id (only if Live is connected)."""
    if sf.is_connected():
        await asyncio.to_thread(_cancel_on, sf.get_connection(), run_id)


def parse_response(r: dict) -> dict:
    """Answer text, every tool call in order (name, type, status, SQL or input, rows), SQL list and tokens."""
    steps, by_id, text, hits = [], {}, [], []
    for c in r.get("content", []):
        t = c.get("type")
        if t == "text":
            text.append(c.get("text", ""))
        elif t == "tool_use":
            u = c.get("tool_use", {})
            inp = u.get("input") or {}
            step = {"tool": u.get("name"), "type": u.get("type"), "sql": inp.get("sql"),
                    "input": None if inp.get("sql") else json.dumps(inp, ensure_ascii=False)[:600],
                    "status": None, "rows": None}
            steps.append(step)
            by_id[u.get("tool_use_id")] = step
        elif t == "tool_result":
            tr = c.get("tool_result", {})
            if tr.get("name") == "business_ontology":
                hits += _ontology_names(json.dumps(tr.get("content", [])))
            step = by_id.get(tr.get("tool_use_id"))
            if step is None:
                continue
            step["status"] = tr.get("status")
            for item in tr.get("content", []):
                j = item.get("json") or {}
                if j.get("sql") and not step["sql"]:
                    step["sql"] = j["sql"]
                rs = j.get("result_set") or {}
                if rs.get("resultSetMetaData"):
                    step["rows"] = rs["resultSetMetaData"].get("numRows")
    tokens = {"input": 0, "output": 0}
    for u in ((r.get("metadata") or {}).get("usage") or {}).get("tokens_consumed", []):
        tokens["input"] += (u.get("input_tokens") or {}).get("total", 0)
        tokens["output"] += (u.get("output_tokens") or {}).get("total", 0)
    tools = [s["tool"] for s in steps]
    return {"text": "\n".join(x for x in text if x).strip(), "status": r.get("status"), "tokens": tokens,
            "steps": steps, "tool_calls": len(steps),
            "tool_counts": {t: tools.count(t) for t in dict.fromkeys(tools)},
            "sql": [s["sql"] for s in steps if s["sql"]],
            "ontology_hits": list(dict.fromkeys(hits))[:15]}


def _ontology_names(blob: str) -> list[str]:
    # Search results render as "N. Domain.Name (KIND)"; keep the names.
    return [m.group(2) for m in re.finditer(r"\d+\.\s+([A-Za-z ]+)\.([A-Za-z0-9 \-]+?) \((?:METRIC|ENTITY|TERM)\)", blob)]
