// Shared building blocks: markdown answers, score badges, the agent trace and tables touched.
import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Answer, Step, TOOL_LABEL, VerdictLabel } from "../api";

export function Markdown({ text }: { text: string }) {
  if (!text) return <div className="muted italic">No text response</div>;
  return (
    <div className="prose">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{text}</ReactMarkdown>
    </div>
  );
}

export function verdictLabel(v: VerdictLabel | undefined): string {
  return v === "correct" ? "CORRECT" : v === "partial" ? "PARTIAL" : v === "wrong" ? "WRONG" : "NOT SCORED";
}

export function ScoreBadge({ score, verdict }: { score?: number | null; verdict?: VerdictLabel }) {
  if (verdict == null) return null;
  return (
    <span className={`pill pill-${verdict}`}>
      {verdictLabel(verdict)} {score != null ? score.toFixed(2) : ""}
    </span>
  );
}

export function toolLabel(t: string | null): string {
  return (t && TOOL_LABEL[t]) || t || "tool";
}

/** "3 tool calls (Cortex Analyst, Ontology search, SQL x2)" */
export function toolSummary(a: Answer): string {
  const parts = Object.entries(a.tool_counts).map(([t, n]) => `${toolLabel(t)}${n > 1 ? ` x${n}` : ""}`);
  return `${a.tool_calls} tool call${a.tool_calls === 1 ? "" : "s"}${parts.length ? ` (${parts.join(", ")})` : ""}`;
}

/** Logical (__titles) and physical (ONTOLOGY_DEMO.GAME_SALES.TITLES) tables named in the SQL. */
export function tablesTouched(a: Answer): string[] {
  const found = new Set<string>();
  for (const sql of a.sql) {
    for (const m of sql.matchAll(/\b__([a-z0-9_]+)/gi)) found.add(m[1].toUpperCase());
    for (const m of sql.matchAll(/ONTOLOGY_DEMO\.(GAME_CATALOG|GAME_SALES)\.(\w+)/gi)) found.add(m[2].toUpperCase());
  }
  return [...found].sort();
}

function StepRow({ step, index }: { step: Step; index: number }) {
  const [open, setOpen] = useState(false);
  const body = step.sql ?? step.input ?? "";
  const failed = step.status && !/success|ok/i.test(step.status);
  return (
    <li className="step">
      <button className="step-head" onClick={() => setOpen(!open)}>
        <span className="muted">{index + 1}.</span>
        <span className="chip">{toolLabel(step.tool)}</span>
        <span className="mono step-summary">{body.replace(/\s+/g, " ").slice(0, 110)}</span>
        {failed && <span className="err">{step.status}</span>}
        {step.rows != null && <span className="muted">{step.rows} rows</span>}
        <span className="muted">{open ? "-" : "+"}</span>
      </button>
      {open && body && <pre className="code">{body}</pre>}
    </li>
  );
}

/** How the agent answered: tool calls, SQL, tokens, and the judge's reason. */
export function AgentTrace({ answer, openReason = false }: { answer: Answer; openReason?: boolean }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="trace">
      {answer.judge_reason && (
        <details className={`reason reason-${answer.verdict ?? "none"}`} open={openReason}>
          <summary>Why this score (judge)</summary>
          <p>{answer.judge_reason}</p>
        </details>
      )}
      <button className="link" onClick={() => setOpen(!open)}>
        {open ? "v" : ">"} How it answered: {toolSummary(answer)}
      </button>
      <div className="muted small">
        {answer.elapsed}s &middot; {(answer.tokens.input ?? 0).toLocaleString()} input /{" "}
        {(answer.tokens.output ?? 0).toLocaleString()} output tokens
      </div>
      {open && (
        <ol className="steps">
          {answer.steps.map((s, i) => <StepRow key={i} step={s} index={i} />)}
        </ol>
      )}
    </div>
  );
}
