// Analysis tab: the recorded batch run, grouped by challenge C1-C7. Static; no Snowflake connection.
import { AGENT_INFO, byChallenge, challengeNum, RecordedResult, RecordedRun, Side, SIDES } from "../api";
import { AgentTrace, Markdown, ScoreBadge, tablesTouched, toolLabel } from "./common";

export default function AnalysisView(props: {
  recorded: RecordedRun | null;
  recordedError: string | null;
  challenges: Record<string, string>;
}) {
  const { recorded, recordedError, challenges } = props;
  if (!recorded) return <div className="muted">No recorded run ({recordedError ?? "loading"}). Run python3 scripts/batch_eval.py.</div>;
  const rows = [...recorded.results].sort(byChallenge);
  const n = rows.length;
  const stats = (side: Side) => ({
    correct: rows.filter((r) => r.answers[side].verdict === "correct").length,
    partial: rows.filter((r) => r.answers[side].verdict === "partial").length,
    mean: rows.reduce((t, r) => t + (r.answers[side].score ?? 0), 0) / Math.max(n, 1),
    calls: rows.reduce((t, r) => t + r.answers[side].tool_calls, 0) / Math.max(n, 1),
  });
  const ontologyOnly = rows.filter((r) => r.answers.ontology.verdict === "correct" && r.answers.baseline.verdict !== "correct");
  const groups = new Map<number, RecordedResult[]>();
  for (const r of rows) groups.set(challengeNum(r.challenge), [...(groups.get(challengeNum(r.challenge)) ?? []), r]);

  return (
    <div className="stack">
      <p className="muted">
        Batch run <b>{recorded.run_id}</b>: {n} questions, both agents run once with DATA_AGENT_RUN
        {recorded.role ? ` as ${recorded.role}` : ""}. Each answer is graded by {recorded.judge_model} (AI_COMPLETE): 1.0
        within 1% of the expected amount, 0.67 within 3%, 0.33 when the right answer is only an alternative, 0 otherwise.
        Correct means {recorded.pass_threshold} or higher.
      </p>

      <section className="grid grid-4">
        {SIDES.map((side) => {
          const s = stats(side);
          return (
            <div key={side} className="card stat">
              <div className="stat-value" style={{ color: AGENT_INFO[side].color }}>{s.correct}/{n}</div>
              <div className="muted small">{AGENT_INFO[side].label} correct</div>
              <div className="tiny">
                {s.partial} partial &middot; mean score {s.mean.toFixed(2)} &middot; {s.calls.toFixed(1)} tool calls per answer
              </div>
            </div>
          );
        })}
        <div className="card stat">
          <div className="stat-value" style={{ color: "var(--sense)" }}>{ontologyOnly.length}</div>
          <div className="muted small">Questions only the ontology agent got right</div>
        </div>
        <div className="card stat">
          <div className="stat-value">{groups.size}</div>
          <div className="muted small">Challenges covered</div>
        </div>
      </section>

      {[...groups.entries()].map(([num, rs]) => (
        <section key={num} className="stack-sm">
          <h3>
            <span className="pill pill-challenge">C{num}</span> {challenges[`C${num}`] ?? ""}{" "}
            <span className="muted small">({rs.length} question{rs.length === 1 ? "" : "s"})</span>
          </h3>
          {rs.map((r) => <QuestionCard key={r.id} result={r} />)}
        </section>
      ))}
    </div>
  );
}

function QuestionCard({ result }: { result: RecordedResult }) {
  return (
    <div className="card qcard">
      <div className="qcard-head">
        <span className="pill">Q{result.id}</span>
        <span className="muted small">{result.challenge}</span>
        <span className="question-text">{result.question}</span>
      </div>
      <table className="behavior">
        <thead>
          <tr><th>Agent</th><th>Score</th><th>Tool calls</th><th>Tools used</th><th>Tables touched</th><th>Tokens</th><th>Time</th></tr>
        </thead>
        <tbody>
          {SIDES.map((side) => {
            const a = result.answers[side];
            return (
              <tr key={side}>
                <td style={{ color: AGENT_INFO[side].color }}><b>{AGENT_INFO[side].label}</b></td>
                <td><ScoreBadge score={a.score} verdict={a.verdict} /></td>
                <td>{a.tool_calls}</td>
                <td className="small">{Object.entries(a.tool_counts).map(([t, c]) => `${toolLabel(t)}${c > 1 ? ` x${c}` : ""}`).join(", ") || "none"}</td>
                <td className="mono tiny">{tablesTouched(a).join(", ") || "-"}</td>
                <td className="small">{((a.tokens.input ?? 0) + (a.tokens.output ?? 0)).toLocaleString()}</td>
                <td className="small">{a.elapsed}s</td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <div className="grid grid-2 answers">
        {SIDES.map((side) => {
          const a = result.answers[side];
          return (
            <div key={side} className="answer-block" style={{ borderLeftColor: AGENT_INFO[side].color }}>
              <div className="answer-head">
                <b style={{ color: AGENT_INFO[side].color }}>{AGENT_INFO[side].label}</b>
                <ScoreBadge score={a.score} verdict={a.verdict} />
              </div>
              <div className="answer-text"><Markdown text={a.text} /></div>
              <AgentTrace answer={a} openReason={a.verdict !== "correct"} />
            </div>
          );
        })}
      </div>
      <div className="qcard-foot small">
        {result.headline && <div><b>Judge:</b> {result.headline}</div>}
        <div><b>Expected:</b> {result.expected}</div>
        {result.naive_trap && <div><b>Naive trap:</b> {result.naive_trap}</div>}
      </div>
    </div>
  );
}
