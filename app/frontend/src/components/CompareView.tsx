// Compare tab: pick a question, then show Recorded answers instantly or run both agents Live.
import { useEffect, useMemo, useRef, useState } from "react";
import {
  AGENT_INFO, Answer, byChallenge, challengeNum, getJSON, LiveStatus, Question, RecordedRun, Side, SIDES,
  streamCompare, StreamEvent, Verdict,
} from "../api";
import { AgentTrace, Markdown, ScoreBadge, toolLabel } from "./common";

type Mode = "recorded" | "live";

interface Pane {
  status: "idle" | "running" | "done" | "error" | "cancelled";
  text: string;
  steps: string[];
  answer: Answer | null;
  error: string | null;
  ms: number;
}

const emptyPane = (status: Pane["status"] = "idle"): Pane => ({ status, text: "", steps: [], answer: null, error: null, ms: 0 });

interface Shown {
  question: string;
  challenge: string;
  id: number | null;
  expected: string;
  trap: string;
  headline: string | null;
  source: Mode;
}

export default function CompareView(props: { questions: Question[]; recorded: RecordedRun | null; recordedError: string | null }) {
  const { questions, recorded, recordedError } = props;
  const [mode, setMode] = useState<Mode>("recorded");
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [customQ, setCustomQ] = useState("");
  const [shown, setShown] = useState<Shown | null>(null);
  const [panes, setPanes] = useState<Record<Side, Pane>>({ baseline: emptyPane(), ontology: emptyPane() });
  const [judging, setJudging] = useState(false);
  const [judgeError, setJudgeError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [live, setLive] = useState<LiveStatus | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const compareIdRef = useRef<string | null>(null);

  useEffect(() => {
    getJSON<LiveStatus>("/api/live-status").then(setLive).catch(() => setLive(null));
  }, [running]);

  const grouped = useMemo(() => {
    const groups = new Map<number, Question[]>();
    for (const q of [...questions].sort(byChallenge)) {
      const n = challengeNum(q.challenge);
      groups.set(n, [...(groups.get(n) ?? []), q]);
    }
    return [...groups.entries()];
  }, [questions]);
  const selected = questions.find((q) => q.id === selectedId) ?? null;

  function showRecorded(q: Question) {
    const r = recorded?.results.find((x) => x.id === q.id);
    if (!r) return;
    setShown({ question: r.question, challenge: r.challenge, id: r.id, expected: r.expected, trap: r.naive_trap,
               headline: r.headline, source: "recorded" });
    setPanes({
      baseline: { ...emptyPane("done"), answer: r.answers.baseline, text: r.answers.baseline.text, ms: r.answers.baseline.elapsed * 1000 },
      ontology: { ...emptyPane("done"), answer: r.answers.ontology, text: r.answers.ontology.text, ms: r.answers.ontology.elapsed * 1000 },
    });
    setJudgeError(null);
  }

  function onEvent(e: StreamEvent) {
    if (e.type === "start") {
      compareIdRef.current = e.compare_id ?? null;
      return;
    }
    if (e.type === "verdict_pending") return setJudging(true);
    if (e.type === "verdict") {
      setJudging(false);
      if (e.error || !e.verdict) return setJudgeError(e.error ?? "no verdict");
      return applyVerdict(e.verdict);
    }
    if (e.type === "done" || !e.side) return;
    const side = e.side;
    setPanes((prev) => {
      const p = { ...prev[side] };
      if (e.ms !== undefined) p.ms = e.ms;
      if (e.type === "tool_use" && e.name) p.steps = [...p.steps, toolLabel(e.name)];
      if (e.type === "text") p.text += e.text ?? "";
      if (e.type === "error") {
        p.error = e.message ?? "error";
        p.status = "error";
      }
      if (e.type === "final" && e.final) {
        p.answer = e.final;
        p.text = e.final.text || p.text;
        p.status = p.status === "error" ? "error" : "done";
      }
      return { ...prev, [side]: p };
    });
  }

  function applyVerdict(v: Verdict) {
    setShown((s) => (s ? { ...s, headline: v.headline ?? null } : s));
    setPanes((prev) => {
      const next = { ...prev };
      for (const side of SIDES) {
        const a = next[side].answer;
        if (a) {
          next[side] = { ...next[side], answer: { ...a, score: v[`${side}_score`], verdict: v[`${side}_verdict`], judge_reason: v[`${side}_reason`] } };
        }
      }
      return next;
    });
  }

  async function runLive(body: { question_id?: number; text?: string }, q: Question | null, text: string) {
    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    setShown({ question: text, challenge: q?.challenge ?? "custom", id: q?.id ?? null, expected: q?.expected ?? "",
               trap: q?.naive_trap ?? "", headline: null, source: "live" });
    setPanes({ baseline: emptyPane("running"), ontology: emptyPane("running") });
    setJudgeError(null);
    setJudging(false);
    setRunning(true);
    try {
      await streamCompare(body, onEvent, ctrl.signal);
    } catch (err) {
      if (!ctrl.signal.aborted) {
        setPanes((prev) => {
          const next = { ...prev };
          for (const s of SIDES) if (next[s].status === "running") next[s] = { ...next[s], status: "error", error: String(err) };
          return next;
        });
      }
    } finally {
      setRunning(false);
    }
  }

  function stop() {
    const id = compareIdRef.current;
    abortRef.current?.abort();
    if (id) fetch(`/api/compare/${id}/cancel`, { method: "POST" }).catch(() => undefined);
    setPanes((prev) => {
      const next = { ...prev };
      for (const s of SIDES) if (next[s].status === "running") next[s] = { ...next[s], status: "cancelled" };
      return next;
    });
    setRunning(false);
    setJudging(false);
  }

  function ask() {
    if (!selected) return;
    if (mode === "recorded") showRecorded(selected);
    else runLive({ question_id: selected.id }, selected, selected.question);
  }

  return (
    <div className="stack">
      <section className="card picker">
        <div className="picker-row">
          <label className="grow">
            <div className="label">Select a question</div>
            <select
              value={selectedId ?? ""}
              disabled={running}
              onChange={(e) => {
                const id = e.target.value ? Number(e.target.value) : null;
                setSelectedId(id);
                const q = questions.find((x) => x.id === id);
                if (q && mode === "recorded") showRecorded(q);
              }}
            >
              <option value="">Pick one of {questions.length} eval questions...</option>
              {grouped.map(([n, qs]) => (
                <optgroup key={n} label={n < 9 ? `C${n}` : "Other"}>
                  {qs.map((q) => (
                    <option key={q.id} value={q.id}>Q{q.id} [{q.challenge}]: {q.question}</option>
                  ))}
                </optgroup>
              ))}
            </select>
          </label>
          <div className="toggle">
            {(["recorded", "live"] as Mode[]).map((m) => (
              <button key={m} className={mode === m ? "on" : ""} disabled={running} onClick={() => setMode(m)}>
                {m === "recorded" ? "Recorded" : "Live"}
              </button>
            ))}
          </div>
          <button className="primary" disabled={running || !selected || (mode === "recorded" && !recorded)} onClick={ask}>
            {running ? "Running..." : mode === "recorded" ? "Show both agents" : "Ask both agents"}
          </button>
        </div>
        <div className="muted small">
          {mode === "recorded"
            ? recorded
              ? `Recorded replays the scored answers, tool calls and judge reasons from batch run ${recorded.run_id} instantly. No Snowflake connection.`
              : `No recorded run (${recordedError ?? "loading"}). Run python3 scripts/batch_eval.py.`
            : `Live runs both agents now with DATA_AGENT_RUN (about 30-120 s) and judges the answers.${
                live && !live.connected ? ` The first Live run opens a Snowflake browser login (connection ${live.connection}, role ${live.role}).` : ""
              }`}
        </div>
        <form
          className="custom"
          onSubmit={(e) => {
            e.preventDefault();
            if (customQ.trim()) runLive({ text: customQ.trim() }, null, customQ.trim());
          }}
        >
          <div className="label">Or type a custom question (always live, not scored against an expected answer)</div>
          <div className="picker-row">
            <input className="grow" placeholder="Ask any gaming business question..." value={customQ}
                   onChange={(e) => setCustomQ(e.target.value)} disabled={running} />
            <button type="submit" disabled={running || !customQ.trim()}>Ask</button>
          </div>
        </form>
      </section>

      {shown && (
        <section className="question-head">
          <span className="pill pill-challenge">{shown.challenge}</span>
          {shown.id != null && <span className="muted">Q{shown.id}</span>}
          <span className="muted small">{shown.source === "recorded" ? "recorded" : "live"}</span>
          <div className="question-text">{shown.question}</div>
        </section>
      )}

      {shown && (
        <section className="grid grid-2">
          {SIDES.map((side) => <AgentPanel key={side} side={side} pane={panes[side]} onStop={stop} />)}
        </section>
      )}

      {shown && (
        <section className="grid grid-2">
          <div className="card expected">
            <div className="label">Expected answer</div>
            <div>{shown.expected || "No expected answer (custom question)."}</div>
            {shown.trap && (
              <>
                <div className="label">Naive trap</div>
                <div className="small">{shown.trap}</div>
              </>
            )}
          </div>
          <div className="card">
            <div className="label">Judge verdict</div>
            {judging && <div className="muted">Judging both answers...</div>}
            {judgeError && <div className="err">Judge failed: {judgeError}</div>}
            {shown.headline && <div className="headline">{shown.headline}</div>}
            {SIDES.map((side) => {
              const a = panes[side].answer;
              if (!a || a.verdict == null) return null;
              return (
                <div key={side} className="verdict-line">
                  <b style={{ color: AGENT_INFO[side].color }}>{AGENT_INFO[side].label}:</b> <ScoreBadge score={a.score} verdict={a.verdict} />
                </div>
              );
            })}
          </div>
        </section>
      )}

      {recorded && <Scorecard recorded={recorded} />}
    </div>
  );
}

function AgentPanel({ side, pane, onStop }: { side: Side; pane: Pane; onStop: () => void }) {
  const info = AGENT_INFO[side];
  return (
    <div className="card panel" style={{ borderLeftColor: info.color }}>
      <div className="panel-head">
        <div>
          <div className="panel-title">{info.label}</div>
          <div className="muted tiny mono">{info.sublabel}</div>
        </div>
        <div className="panel-pills">
          <ScoreBadge score={pane.answer?.score} verdict={pane.answer?.verdict} />
          {pane.status !== "idle" && <span className="pill">{(pane.ms / 1000).toFixed(1)}s</span>}
        </div>
      </div>
      <div className="panel-body">
        {pane.status === "running" && (
          <div className="running">
            <span className="spinner" /> Running{pane.steps.length ? `: ${pane.steps.join(" > ")}` : "..."}
            <button className="link" onClick={onStop}>Stop</button>
          </div>
        )}
        {pane.status === "cancelled" && <div className="muted">Cancelled.</div>}
        {pane.error && <div className="err">{pane.error}</div>}
        {pane.answer ? <Markdown text={pane.answer.text} /> : pane.text && <Markdown text={pane.text} />}
        {pane.answer && <AgentTrace answer={pane.answer} openReason />}
      </div>
    </div>
  );
}

function Scorecard({ recorded }: { recorded: RecordedRun }) {
  const byNum = new Map<number, RecordedRun["results"]>();
  for (const r of [...recorded.results].sort(byChallenge)) {
    const n = challengeNum(r.challenge);
    byNum.set(n, [...(byNum.get(n) ?? []), r]);
  }
  return (
    <section className="card">
      <div className="label">Scorecard (recorded run {recorded.run_id}, correct at {recorded.pass_threshold} or higher)</div>
      <div className="grid grid-7">
        {[...byNum.entries()].map(([n, rs]) => (
          <div key={n} className="score-box">
            <b>C{n}</b>
            {SIDES.map((side) => (
              <div key={side} className="small" style={{ color: AGENT_INFO[side].color }}>
                {side === "baseline" ? "Baseline" : "Ontology"}: {rs.filter((r) => r.answers[side].verdict === "correct").length}/{rs.length}
              </div>
            ))}
          </div>
        ))}
      </div>
    </section>
  );
}
