"""FastAPI backend: serves the React build and streams both agents side by side.

POST /api/compare  -> text/event-stream of {side, type, ...} events, then a verdict and done.
"""
import asyncio
import json
import os
import time
import uuid
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import agents
import judge
import oauth
import questions as eval_questions
from sf import sql_connection

HERE = Path(__file__).parent
# Read the eval set straight from the repo, so edits show up after a backend reload.
EVAL_MD = Path(os.getenv("EVAL_MD", HERE.parents[1] / "ontology_setup" / "ontology_eval_set.md"))
QUESTIONS = eval_questions.parse(EVAL_MD.read_text())
BY_ID = {q["id"]: q for q in QUESTIONS}
STATIC = Path(os.getenv("STATIC_DIR", HERE / "static"))
HEARTBEAT_SECS = 15

app = FastAPI(title="Ontology vs Baseline")
app.include_router(oauth.router)
oauth.default_role()  # fail fast if APP_ROLES / APP_DEFAULT_ROLE are misconfigured
client = httpx.AsyncClient(http2=False)
RUNS: dict[str, dict] = {}  # compare_id -> {side: run_id, "cred": Credential}


class CompareRequest(BaseModel):
    question_id: int | None = None
    text: str | None = None


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.get("/api/me")
def me(request: Request):
    try:
        cred = oauth.credential(request)
    except PermissionError as exc:
        raise HTTPException(401, str(exc))
    with sql_connection(cred) as conn:
        user, role, secondary, wh = conn.cursor().execute(
            "SELECT CURRENT_USER(), CURRENT_ROLE(), CURRENT_SECONDARY_ROLES(), CURRENT_WAREHOUSE()"
        ).fetchone()
    secondary = json.loads(secondary).get("roles", "") if secondary else ""
    return {"user": user, "role": role, "secondary_roles": secondary, "warehouse": wh}


@app.get("/api/questions")
def questions():
    return QUESTIONS


def _sse(payload: dict) -> bytes:
    return f"event: {payload['type']}\ndata: {json.dumps(payload, default=str)}\n\n".encode()


async def _pump(side: str, question: str, cred, compare_id: str, out: asyncio.Queue):
    start = time.monotonic()
    final = None
    try:
        async for event, data in agents.stream_agent(client, side, question, cred):
            elapsed = int((time.monotonic() - start) * 1000)
            if event == "metadata" and data.get("metadata", {}).get("run_id"):
                RUNS.get(compare_id, {})[side] = data["metadata"]["run_id"]
            if event == "response.text.delta":
                await out.put({"side": side, "type": "text", "text": data.get("text", ""), "ms": elapsed})
            elif event == "response.thinking.delta":
                await out.put({"side": side, "type": "thinking", "text": data.get("text", ""), "ms": elapsed})
            elif event == "response.status":
                await out.put({"side": side, "type": "status", "status": data.get("status"),
                               "message": data.get("message"), "ms": elapsed})
            elif event == "response.tool_use":
                await out.put({"side": side, "type": "tool_use", "name": data.get("name"),
                               "sql": (data.get("input") or {}).get("sql"), "ms": elapsed})
            elif event == "response.tool_result":
                await out.put({"side": side, "type": "tool_result", "name": data.get("name"),
                               "status": data.get("status"), "ms": elapsed})
            elif event == "response.table":
                await out.put({"side": side, "type": "table", "table": data, "ms": elapsed})
            elif event == "error":
                await out.put({"side": side, "type": "error", "message": data.get("message"), "ms": elapsed})
            elif event == "response":
                final = agents.summarize_final(data)
                await out.put({"side": side, "type": "final", "final": final, "ms": elapsed})
    except Exception as exc:  # network errors, cancellations from the server side
        await out.put({"side": side, "type": "error", "message": str(exc)})
    finally:
        await out.put({"side": side, "type": "_side_done", "final": final})


async def _compare_stream(question: dict, cred, compare_id: str, request: Request):
    out: asyncio.Queue = asyncio.Queue()
    yield _sse({"type": "start", "compare_id": compare_id, "question": question})
    tasks = [asyncio.create_task(_pump(side, question["question"], cred, compare_id, out))
             for side in ("baseline", "ontology")]
    finals, done = {}, 0
    try:
        while done < 2:
            try:
                item = await asyncio.wait_for(out.get(), timeout=HEARTBEAT_SECS)
            except asyncio.TimeoutError:
                yield b": keepalive\n\n"
                continue
            if item["type"] == "_side_done":
                done += 1
                finals[item["side"]] = item["final"]
                continue
            yield _sse(item)

        b, o = finals.get("baseline"), finals.get("ontology")
        if b and o:
            yield _sse({"type": "verdict_pending"})
            try:
                # Agent runs can outlast the access token; get a fresh one for the judge.
                judge_cred = await asyncio.to_thread(oauth.credential, request)
                verdict = await asyncio.to_thread(judge.judge, question, b, o, judge_cred)
                yield _sse({"type": "verdict", "verdict": verdict})
            except Exception as exc:
                yield _sse({"type": "verdict", "error": str(exc)})
        yield _sse({"type": "done"})
    finally:
        for t in tasks:
            t.cancel()
        RUNS.pop(compare_id, None)


@app.post("/api/compare")
async def compare(req: CompareRequest, request: Request):
    if req.question_id is not None:
        question = BY_ID.get(req.question_id)
        if not question:
            raise HTTPException(404, "unknown question")
    elif req.text and req.text.strip():
        question = {"id": None, "question": req.text.strip(), "expected": "", "naive_trap": "", "fixing_nodes": ""}
    else:
        raise HTTPException(400, "question_id or text required")
    try:
        cred = await asyncio.to_thread(oauth.credential, request)
    except PermissionError as exc:
        raise HTTPException(401, str(exc))
    compare_id = uuid.uuid4().hex
    RUNS[compare_id] = {"cred": cred}
    return StreamingResponse(_compare_stream(question, cred, compare_id, request), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.post("/api/compare/{compare_id}/cancel")
async def cancel(compare_id: str):
    entry = RUNS.get(compare_id)
    if not entry:
        return {"cancelled": []}
    cancelled = []
    for side in ("baseline", "ontology"):
        if entry.get(side):
            try:
                await agents.cancel_run(client, entry[side], entry["cred"])
                cancelled.append(side)
            except Exception:
                pass
    return {"cancelled": cancelled}


if STATIC.exists():
    app.mount("/assets", StaticFiles(directory=STATIC / "assets"), name="assets")

    @app.get("/{path:path}")
    def spa(path: str):
        return FileResponse(STATIC / "index.html")
