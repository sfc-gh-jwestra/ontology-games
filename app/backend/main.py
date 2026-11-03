"""FastAPI backend for the compare app. No app login.

Recorded mode, Setup and Analysis read repo files only. Live mode runs both agents with
DATA_AGENT_RUN over one named connection (sf.py), opened on the first Live call.

GET  /api/questions      eval set questions (documentation/ontology/ontology_eval_set.md)
GET  /api/recorded       latest batch eval (evaluations/results/latest.json, from scripts/batch_eval.py)
GET  /api/setup          agents, semantic views, ontology and challenges, from repo files
GET  /api/live-status    whether the Live connection is open yet
POST /api/compare        text/event-stream of {side, type, ...} events, then a graded verdict and done
"""
import asyncio
import json
import os
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import agents
import judge
import ontology_trace
import questions as eval_questions
import setup_info
import sf

HERE = Path(__file__).parent
# Read the eval set straight from the repo, so edits show up after a backend reload.
EVAL_MD = Path(os.getenv("EVAL_MD", HERE.parents[1] / "documentation" / "ontology" / "ontology_eval_set.md"))
QUESTIONS = eval_questions.parse(EVAL_MD.read_text())
BY_ID = {q["id"]: q for q in QUESTIONS}
STATIC = Path(os.getenv("STATIC_DIR", HERE / "static"))
# Batch eval results, shown in Recorded mode. Read on each request so a new run appears.
RECORDED_JSON = Path(os.getenv("RECORDED_JSON", HERE.parents[1] / "evaluations" / "results" / "latest.json"))
HEARTBEAT_SECS = 15

app = FastAPI(title="Ontology vs Baseline")
RUNS: dict[str, dict] = {}  # compare_id -> {side: query_id}


class CompareRequest(BaseModel):
    question_id: int | None = None
    text: str | None = None


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.get("/api/questions")
def questions():
    return QUESTIONS


@app.get("/api/recorded")
def recorded():
    if not RECORDED_JSON.exists():
        raise HTTPException(404, "no recorded run yet; run python3 scripts/batch_eval.py")
    return json.loads(RECORDED_JSON.read_text())


@app.get("/api/setup")
def setup():
    return setup_info.setup(QUESTIONS)


@app.get("/api/live-status")
def live_status():
    return sf.info()


def _sse(payload: dict) -> bytes:
    return f"event: {payload['type']}\ndata: {json.dumps(payload, default=str)}\n\n".encode()


async def _pump(side: str, question: str, compare_id: str, out: asyncio.Queue):
    start = time.monotonic()
    final = None
    try:
        async for event, data in agents.stream_agent(side, question):
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
            elif event == "error":
                await out.put({"side": side, "type": "error", "message": data.get("message"), "ms": elapsed})
            elif event == "response":
                final = dict(agents.parse_response(data), elapsed=round(elapsed / 1000, 1))
                await out.put({"side": side, "type": "final", "final": final, "ms": elapsed})
    except Exception as exc:  # network errors, cancellations from the server side
        await out.put({"side": side, "type": "error", "message": str(exc)})
    finally:
        await out.put({"side": side, "type": "_side_done", "final": final})


async def _compare_stream(question: dict, compare_id: str):
    out: asyncio.Queue = asyncio.Queue()
    yield _sse({"type": "start", "compare_id": compare_id, "question": question})
    tasks = [asyncio.create_task(_pump(side, question["question"], compare_id, out))
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
                verdict = await asyncio.to_thread(judge.judge, question, b, o)
                trace = ontology_trace.contribution(question, o, verdict)
                yield _sse({"type": "verdict", "verdict": verdict, "ontology_trace": trace})
            except Exception as exc:
                yield _sse({"type": "verdict", "error": str(exc)})
        yield _sse({"type": "done"})
    finally:
        for t in tasks:
            t.cancel()
        RUNS.pop(compare_id, None)


@app.post("/api/compare")
async def compare(req: CompareRequest):
    if req.question_id is not None:
        question = BY_ID.get(req.question_id)
        if not question:
            raise HTTPException(404, "unknown question")
    elif req.text and req.text.strip():
        if len(req.text) > 2000:
            raise HTTPException(400, "question too long (max 2000 characters)")
        question = {"id": None, "question": req.text.strip(), "expected": "", "naive_trap": "", "fixing_nodes": ""}
    else:
        raise HTTPException(400, "question_id or text required")
    compare_id = uuid.uuid4().hex
    RUNS[compare_id] = {}
    return StreamingResponse(_compare_stream(question, compare_id), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.post("/api/compare/{compare_id}/cancel")
async def cancel(compare_id: str):
    entry = RUNS.get(compare_id) or {}
    cancelled = []
    for side in ("baseline", "ontology"):
        if entry.get(side):
            try:
                await agents.cancel_run(entry[side])
                cancelled.append(side)
            except Exception:
                pass
    return {"cancelled": cancelled}


if STATIC.exists():
    app.mount("/assets", StaticFiles(directory=STATIC / "assets"), name="assets")

    @app.get("/{path:path}")
    def spa(path: str):
        return FileResponse(STATIC / "index.html")
