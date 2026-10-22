import { useEffect, useMemo, useRef, useState } from "react";
import { Final, getJSON, Me, Question, Roles, Side, signInUrl, streamCompare, StreamEvent, Unauthorized, Verdict } from "./api";

type PaneStatus = "idle" | "streaming" | "done" | "error" | "cancelled";

interface PaneState {
  status: PaneStatus;
  question: string;
  text: string;
  thinking: string;
  steps: { label: string; done: boolean }[];
  final: Final | null;
  error: string | null;
  ms: number;
}

const emptyPane = (question = ""): PaneState => ({
  status: question ? "streaming" : "idle",
  question,
  text: "",
  thinking: "",
  steps: [],
  final: null,
  error: null,
  ms: 0,
});

const AGENT_INFO: Record<Side, { title: string; name: string; desc: string }> = {
  baseline: { title: "BASELINE", name: "GAMING_BASELINE_AGENT", desc: "semantic view only" },
  ontology: { title: "WITH ONTOLOGY", name: "GAMING_BON_AGENT", desc: "semantic view + Business Ontology search" },
};

const STEP_LABELS: Record<string, string> = {
  business_ontology: "Searching ontology",
  query_data: "Generating SQL",
  system_execute_sql: "Running SQL",
};

function stepFor(e: StreamEvent): string | null {
  if (e.type === "tool_use" && e.name) return STEP_LABELS[e.name] ?? `Tool: ${e.name}`;
  if (e.type === "status" && e.status === "planning") return "Planning";
  if (e.type === "status" && e.status === "proceeding_to_answer") return "Forming answer";
  return null;
}

function fmtMs(ms: number) {
  const s = Math.floor(ms / 1000);
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

export default function App() {
  const [me, setMe] = useState<Me | null>(null);
  const [meError, setMeError] = useState<string | null>(null);
  const [signedOut, setSignedOut] = useState(false);
  const [roles, setRoles] = useState<Roles | null>(null);
  const [questions, setQuestions] = useState<Question[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [freeText, setFreeText] = useState("");
  const [current, setCurrent] = useState<Question | null>(null);
  const [panes, setPanes] = useState<Record<Side, PaneState>>({ baseline: emptyPane(), ontology: emptyPane() });
  const [verdict, setVerdict] = useState<Verdict | null>(null);
  const [verdictState, setVerdictState] = useState<"none" | "waiting" | "judging" | "done" | "error">("none");
  const [verdictError, setVerdictError] = useState<string | null>(null);
  const [score, setScore] = useState({ runs: 0, baseline: 0, ontology: 0 });
  const [running, setRunning] = useState(false);
  const [now, setNow] = useState(Date.now());
  const abortRef = useRef<AbortController | null>(null);
  const compareIdRef = useRef<string | null>(null);
  const startRef = useRef(0);

  useEffect(() => {
    getJSON<Roles>("/api/roles").then(setRoles).catch(() => setRoles(null));
    getJSON<Me>("/api/me")
      .then(setMe)
      .catch((e) => (e instanceof Unauthorized ? setSignedOut(true) : setMeError(String(e))));
    getJSON<Question[]>("/api/questions").then(setQuestions).catch(() => setQuestions([]));
  }, []);

  useEffect(() => {
    if (!running) return;
    const t = setInterval(() => setNow(Date.now()), 500);
    return () => clearInterval(t);
  }, [running]);

  const grouped = useMemo(() => {
    const groups = new Map<string, Question[]>();
    for (const q of questions) {
      const list = groups.get(q.challenge) ?? [];
      list.push(q);
      groups.set(q.challenge, list);
    }
    return [...groups.entries()];
  }, [questions]);
  const selected = questions.find((q) => q.id === selectedId) ?? null;

  function onEvent(e: StreamEvent) {
    if (e.type === "start") {
      compareIdRef.current = e.compare_id ?? null;
      return;
    }
    if (e.type === "verdict_pending") return setVerdictState("judging");
    if (e.type === "verdict") {
      if (e.error) {
        setVerdictError(e.error);
        setVerdictState("error");
        return;
      }
      setVerdict(e.verdict ?? null);
      setVerdictState("done");
      setScore((s) => ({
        runs: s.runs + 1,
        baseline: s.baseline + (e.verdict?.baseline_correct ? 1 : 0),
        ontology: s.ontology + (e.verdict?.ontology_correct ? 1 : 0),
      }));
      return;
    }
    if (e.type === "done") return;
    const side = e.side;
    if (!side) return;
    setPanes((prev) => {
      const p = { ...prev[side] };
      if (e.ms !== undefined) p.ms = e.ms;
      const step = stepFor(e);
      if (step) {
        p.steps = [...p.steps.map((s) => ({ ...s, done: true })), { label: step, done: false }];
      }
      if (e.type === "text") p.text += e.text ?? "";
      if (e.type === "thinking") p.thinking += e.text ?? "";
      if (e.type === "tool_result") p.steps = p.steps.map((s) => ({ ...s, done: true }));
      if (e.type === "error") {
        p.error = e.message ?? "error";
        p.status = "error";
      }
      if (e.type === "final" && e.final) {
        p.final = e.final;
        if (e.final.text) p.text = e.final.text;
        p.steps = p.steps.map((s) => ({ ...s, done: true }));
        p.status = p.status === "error" ? "error" : "done";
      }
      return { ...prev, [side]: p };
    });
  }

  async function run(body: { question_id?: number; text?: string }, q: Question | null, text: string) {
    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    setCurrent(q);
    setPanes({ baseline: emptyPane(text), ontology: emptyPane(text) });
    setVerdict(null);
    setVerdictError(null);
    setVerdictState("waiting");
    setRunning(true);
    startRef.current = Date.now();
    try {
      await streamCompare(body, onEvent, ctrl.signal);
    } catch (err) {
      if (err instanceof Unauthorized) {
        setSignedOut(true);
        return;
      }
      if (!ctrl.signal.aborted) {
        setPanes((prev) => {
          const next = { ...prev };
          for (const s of ["baseline", "ontology"] as Side[]) {
            if (next[s].status === "streaming") next[s] = { ...next[s], status: "error", error: String(err) };
          }
          return next;
        });
        setVerdictState("none");
      }
    } finally {
      setRunning(false);
    }
  }

  async function stop() {
    const id = compareIdRef.current;
    abortRef.current?.abort();
    if (id) fetch(`/api/compare/${id}/cancel`, { method: "POST" }).catch(() => undefined);
    setPanes((prev) => {
      const next = { ...prev };
      for (const s of ["baseline", "ontology"] as Side[]) {
        if (next[s].status === "streaming") next[s] = { ...next[s], status: "cancelled" };
      }
      return next;
    });
    setVerdictState("none");
    setRunning(false);
  }

  const liveMs = running ? now - startRef.current : 0;

  if (signedOut) return <SignIn roles={roles} />;

  return (
    <div className="app">
      <header className="header">
        <h1>Ontology vs Baseline - Gaming agents</h1>
        <div className="identity">
          {me ? (
            <>
              <span>User: <b>{me.user}</b></span>
              <span>Role: <b>{me.role}</b></span>
              <span>Secondary: <b>{me.secondary_roles || "none"}</b></span>
              <span>WH: <b>{me.warehouse ?? "none"}</b></span>
              {roles && roles.roles.length > 1 && (
                <select
                  value=""
                  disabled={running}
                  onChange={(e) => e.target.value && (window.location.href = signInUrl(e.target.value))}
                >
                  <option value="">Switch role...</option>
                  {roles.roles.filter((r) => r !== me.role).map((r) => <option key={r} value={r}>{r}</option>)}
                </select>
              )}
              <form method="post" action="/oauth/logout" className="inline">
                <button type="submit" disabled={running}>Sign out</button>
              </form>
            </>
          ) : (
            <span className="muted">{meError ? `Session unavailable: ${meError}` : "Loading session..."}</span>
          )}
        </div>
      </header>

      <section className="picker">
        <div className="picker-top">
          <select
            className="question-select"
            value={selectedId ?? ""}
            disabled={running}
            onChange={(e) => setSelectedId(e.target.value ? Number(e.target.value) : null)}
          >
            <option value="">Pick an eval question ({questions.length})...</option>
            {grouped.map(([challenge, qs]) => (
              <optgroup key={challenge} label={challenge}>
                {qs.map((q) => (
                  <option key={q.id} value={q.id}>{q.id}. {q.question}</option>
                ))}
              </optgroup>
            ))}
          </select>
          <button
            disabled={running || !selected}
            onClick={() => selected && run({ question_id: selected.id }, selected, selected.question)}
          >
            Run
          </button>
        </div>
        <form
          className="free-text"
          onSubmit={(e) => {
            e.preventDefault();
            if (freeText.trim()) run({ text: freeText.trim() }, null, freeText.trim());
          }}
        >
          <span>Or type your own:</span>
          <input value={freeText} onChange={(e) => setFreeText(e.target.value)} disabled={running} />
          <button type="submit" disabled={running || !freeText.trim()}>Ask</button>
        </form>
      </section>

      <section className="panes">
        {(["baseline", "ontology"] as Side[]).map((side) => (
          <AgentPane
            key={side}
            side={side}
            pane={panes[side]}
            liveMs={liveMs}
            expected={current?.expected ?? ""}
            correct={side === "baseline" ? verdict?.baseline_correct : verdict?.ontology_correct}
            judged={verdictState === "done" && !!current}
            onStop={stop}
          />
        ))}
      </section>

      <VerdictPanel state={verdictState} verdict={verdict} error={verdictError} expected={current?.expected ?? ""} />

      <footer className="score">
        Session score: Baseline {score.baseline}/{score.runs} &nbsp; Ontology {score.ontology}/{score.runs}
      </footer>
    </div>
  );
}

function SignIn({ roles }: { roles: Roles | null }) {
  const [role, setRole] = useState("");
  const chosen = role || roles?.default || "";
  return (
    <div className="app signin">
      <h1>Ontology vs Baseline - Gaming agents</h1>
      <div className="signin-card">
        <p>Sign in with your Snowflake account. The agents run as you, using the role you pick.</p>
        {roles ? (
          <>
            <label>
              Role{" "}
              <select value={chosen} onChange={(e) => setRole(e.target.value)}>
                {roles.roles.map((r) => <option key={r} value={r}>{r}</option>)}
              </select>
            </label>
            <a className="button" href={signInUrl(chosen)}>Sign in with Snowflake</a>
          </>
        ) : (
          <div className="error">Could not load roles from /api/roles. Is the backend running with APP_ROLES set?</div>
        )}
      </div>
    </div>
  );
}

function AgentPane(props: {
  side: Side;
  pane: PaneState;
  liveMs: number;
  expected: string;
  correct: boolean | undefined;
  judged: boolean;
  onStop: () => void;
}) {
  const { side, pane, liveMs, expected, correct, judged, onStop } = props;
  const info = AGENT_INFO[side];
  const [showSql, setShowSql] = useState(false);
  const [showThinking, setShowThinking] = useState(false);
  const streaming = pane.status === "streaming";
  const badge = !judged ? (pane.final ? "pending" : null) : correct ? "CORRECT" : "WRONG";

  return (
    <div className={`pane pane-${side}`}>
      <div className="pane-head">
        <div>
          <b>{info.title}</b> <span className="mono">{info.name}</span>
          <div className="muted small">{info.desc}</div>
        </div>
        <div className="pane-status">
          {streaming ? `running ${fmtMs(Math.max(liveMs, pane.ms))}` : pane.status === "idle" ? "" : `${pane.status} ${fmtMs(pane.ms)}`}
        </div>
      </div>

      <div className="chat">
        {pane.status === "idle" ? (
          <div className="muted">Pick a question to run both agents.</div>
        ) : (
          <>
            <div className="msg user">You: {pane.question}</div>
            {pane.steps.length > 0 && (
              <div className="steps">
                {pane.steps.map((s, i) => (
                  <span key={i} className={`chip ${s.done ? "done" : "active"}`}>
                    {s.done ? "[v]" : "[>]"} {s.label}
                  </span>
                ))}
              </div>
            )}
            {pane.thinking && (
              <div className="thinking">
                <button className="link" onClick={() => setShowThinking(!showThinking)}>
                  {showThinking ? "v" : ">"} Thinking
                </button>
                {showThinking && <pre>{pane.thinking}</pre>}
              </div>
            )}
            {(pane.text || streaming) && (
              <div className="msg agent">
                Agent: {pane.text}
                {streaming && <span className="cursor">|</span>}
              </div>
            )}
            {pane.error && <div className="error">{pane.error}</div>}
            {streaming && (
              <div className="stop-row">
                <button onClick={onStop}>Stop</button>
              </div>
            )}
          </>
        )}
      </div>

      {pane.final && (
        <div className="result">
          <div className="result-head">
            <b>RESULT</b>
            {badge && <span className={`badge badge-${badge.toLowerCase()}`}>{badge}</span>}
          </div>
          {expected && <div><span className="muted">Expected:</span> {expected}</div>}
          <div><span className="muted">Tools:</span> {pane.final.tools.filter(Boolean).join(", ") || "-"}</div>
          {side === "ontology" && (
            <div><span className="muted">Ontology nodes:</span> {pane.final.ontology_hits.join(", ") || "-"}</div>
          )}
          <button className="link" onClick={() => setShowSql(!showSql)}>
            {showSql ? "Hide" : "Show"} SQL ({pane.final.sql.length})
          </button>
          {showSql && pane.final.sql.map((s, i) => <pre key={i} className="sql">{s}</pre>)}
        </div>
      )}
    </div>
  );
}

function VerdictPanel(props: { state: string; verdict: Verdict | null; error: string | null; expected: string }) {
  const { state, verdict, error, expected } = props;
  if (state === "none") return null;
  if (state === "waiting") return <section className="verdict muted">Verdict: waiting for both agents...</section>;
  if (state === "judging") return <section className="verdict muted">Verdict: comparing answers...</section>;
  if (state === "error") return <section className="verdict error">Verdict failed: {error}</section>;
  if (!verdict) return null;

  const bothRight = verdict.baseline_correct && verdict.ontology_correct;
  const cls = bothRight ? "agree" : verdict.differ ? "differ" : "neither";
  return (
    <section className={`verdict ${cls}`}>
      <div className="verdict-head">
        <b>{bothRight ? "BOTH AGENTS AGREE" : verdict.differ ? "WHY THE ANSWERS DIFFER" : "NEITHER AGENT MATCHED"}</b>
        {expected && <span className="muted">Expected: {expected}</span>}
      </div>
      <div className="headline">{verdict.headline}</div>
      {!bothRight && <p>{verdict.summary}</p>}
      {!bothRight && verdict.evidence && verdict.evidence.length > 0 && (
        <ul>{verdict.evidence.map((e, i) => <li key={i}>{e}</li>)}</ul>
      )}
    </section>
  );
}
