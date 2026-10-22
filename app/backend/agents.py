"""Run a Cortex Agent through SQL (SNOWFLAKE.CORTEX.DATA_AGENT_RUN) as the signed-in user.

The REST :run endpoint rejected the app's OAuth token inside the BON agent's tool calls
(390303 Invalid OAuth access token), so both agents run over an OAuth SQL session instead.
DATA_AGENT_RUN returns the whole response at once, so there is no token-by-token streaming:
this module emits a "planning" status, then replays the finished response as the same
(event_name, data_dict) pairs the REST stream used, ending with `response`.
"""
import asyncio
import json
from typing import AsyncIterator

from sf import Credential, sql_connection

DB, SCHEMA = "ONTOLOGY_DEMO", "ONTOLOGY_AGENTS"
AGENTS = {"baseline": "GAMING_BASELINE_AGENT", "ontology": "GAMING_BON_AGENT"}
POLL_SECS = 1.0
RUN_SQL = "SELECT SNOWFLAKE.CORTEX.DATA_AGENT_RUN(%s, %s)"


async def stream_agent(client, side: str, question: str, cred: Credential) -> AsyncIterator[tuple[str, dict]]:
    """`client` is unused (kept so callers and test fakes keep one signature)."""
    yield "response.status", {"status": "planning", "message": "Running agent"}
    body = json.dumps({"messages": [{"role": "user", "content": [{"type": "text", "text": question}]}],
                       "stream": False})
    conn, qid = None, None
    try:
        conn = await asyncio.to_thread(sql_connection, cred)
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
        yield "error", {"message": str(exc)}
        return
    finally:
        if conn is not None:
            await asyncio.to_thread(conn.close)

    response = json.loads(raw) if isinstance(raw, str) else raw
    if not response.get("content") and (response.get("message") or response.get("code")):
        yield "error", {"message": f"{response.get('code', '')} {response.get('message', '')}".strip()}
        return
    for event in _replay(response):
        yield event


def _replay(response: dict):
    """Turn the finished response into the step/text events the UI already renders."""
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


async def cancel_run(client, run_id: str, cred: Credential) -> None:
    """Cancel a running DATA_AGENT_RUN query by its query id."""
    def _cancel():
        with sql_connection(cred) as conn:
            _cancel_on(conn, run_id)
    await asyncio.to_thread(_cancel)


def summarize_final(response: dict) -> dict:
    """Pull the pieces the UI and judge need from the final `response` event."""
    text, sql, tools, tables, ontology_hits = [], [], [], [], []
    for item in response.get("content", []):
        kind = item.get("type")
        if kind == "text":
            text.append(item.get("text", ""))
        elif kind == "tool_use":
            tu = item.get("tool_use", {})
            tools.append(tu.get("name"))
            if tu.get("input", {}).get("sql"):
                sql.append(tu["input"]["sql"])
        elif kind == "tool_result":
            tr = item.get("tool_result", {})
            if tr.get("name") == "business_ontology":
                for c in tr.get("content", []):
                    blob = json.dumps(c)
                    ontology_hits += _ontology_names(blob)
        elif kind == "table":
            tables.append(item.get("table", {}))
    return {
        "text": "\n".join(t for t in text if t).strip(),
        "sql": sql,
        "tools": tools,
        "tables": tables,
        "ontology_hits": list(dict.fromkeys(ontology_hits))[:15],
        "status": response.get("status"),
    }


def _ontology_names(blob: str) -> list[str]:
    # Search results render as "N. Domain.Name (KIND)"; keep the names.
    import re
    return [m.group(2) for m in re.finditer(r"\d+\.\s+([A-Za-z ]+)\.([A-Za-z0-9 \-]+?) \((?:METRIC|ENTITY|TERM)\)", blob)]
