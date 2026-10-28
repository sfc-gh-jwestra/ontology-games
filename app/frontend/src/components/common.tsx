// Shared building blocks: markdown answers, score badges, the agent trace and tables touched.
import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Answer, OntologyTrace, Step, TOOL_LABEL, VerdictLabel } from "../api";

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

function StepRow({ step, index, applied }: { step: Step; index: number; applied: Set<string> }) {
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
      {step.nodes && step.nodes.length > 0 && (
        <div className="node-list">
          <span className="muted small">Returned {step.nodes.length} nodes:</span>{" "}
          {step.nodes.map((n) => (
            <span key={n} className={`node ${applied.has(n) ? "node-applied" : ""}`} title={applied.has(n) ? "Applied in the answer" : "Returned, not applied"}>
              {n}
            </span>
          ))}
        </div>
      )}
    </li>
  );
}

/** How the agent answered: tool calls, SQL, tokens, and the judge's reason. */
export function AgentTrace({ answer, openReason = false }: { answer: Answer; openReason?: boolean }) {
  const [open, setOpen] = useState(false);
  const searched = (answer.tool_counts.business_ontology ?? 0) > 0;
  return (
    <div className="trace">
      {(answer.ontology_trace || searched) && <OntologyContribution trace={answer.ontology_trace} usedSearch={searched} />}
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
          {answer.steps.map((s, i) => (
            <StepRow key={i} step={s} index={i} applied={new Set(answer.ontology_trace?.applied.map((a) => a.name) ?? [])} />
          ))}
        </ol>
      )}
    </div>
  );
}

const STATUS_MARK = { applied: "applied", via: "applied via", retrieved: "retrieved only", missed: "missed" };
const STATUS_HELP = {
  applied: "The agent retrieved this node and used it.",
  via: "The node itself wasn't retrieved, but its logic is in the answer or SQL, carried by another node.",
  retrieved: "Retrieved, but its logic isn't in the answer or SQL.",
  missed: "Neither retrieved nor present in the answer or SQL.",
};

/** How the Business Ontology contributed: applied nodes and how, expected coverage, relationships. */
export function OntologyContribution({ trace, usedSearch }: { trace?: OntologyTrace; usedSearch?: boolean }) {
  if (!trace) {
    return (
      <div className="onto-box muted small">
        Ontology contribution: not recorded in this run{usedSearch ? " (the agent did search the ontology)" : ""}. Re-run the
        batch eval (scripts/batch_eval.py) or use Live mode.
      </div>
    );
  }
  const c = trace.coverage;
  return (
    <div className="onto-box">
      <div className="onto-title">
        How the Business Ontology helped
        {c.expected > 0 && (
          <span className="muted small">
            {" "}
            &middot; expected logic covered {c.applied}/{c.expected}
            {c.via ? ` (${c.via} via another node)` : ""}
          </span>
        )}
      </div>
      {trace.applied.length === 0 && <div className="muted small">No ontology node was applied in this answer.</div>}
      <ul className="onto-applied">
        {trace.applied.map((n) => (
          <li key={n.name}>
            <span className={`kind kind-${n.label.toLowerCase()}`}>{n.label}</span> <b>{n.name}</b>: {n.how}
            {(n.formula || n.definition) && (
              <details>
                <summary className="muted small">Definition{n.formula ? " and formula" : ""}</summary>
                {n.definition && <p className="small">{n.definition}</p>}
                {n.formula && <pre className="code">{n.formula}</pre>}
              </details>
            )}
          </li>
        ))}
      </ul>
      {trace.expected.length > 0 && (
        <div className="small">
          <span className="muted">Expected nodes: </span>
          {trace.expected.map((e) => (
            <span
              key={e.name}
              className={`node node-${e.status}`}
              title={`${STATUS_HELP[e.status]}${e.evidence ? `\n${e.evidence}` : ""}`}
            >
              {e.name} ({STATUS_MARK[e.status]}
              {e.via ? ` ${e.via}` : ""})
            </span>
          ))}
          <div className="tiny muted">
            Expected nodes come from the eval set. "Applied via" means the logic was used through another node, so it
            still counts as covered. Hover a node for the evidence.
          </div>
        </div>
      )}
      {trace.relationships.length > 0 && (
        <div className="small onto-rels">
          <span className="muted">Relationships: </span>
          {trace.relationships.map((r, i) => (
            <span key={i} className="mono rel">
              {r.source} &rarr; {r.type} &rarr; {r.target}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
