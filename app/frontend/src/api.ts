// Types and API helpers shared by the UI. There is no login: every endpoint is local to the backend.

export type Side = "baseline" | "ontology";
export const SIDES: Side[] = ["baseline", "ontology"];

export interface Question {
  id: number;
  question: string;
  challenge: string;
  expected: string;
  naive_trap: string;
  fixing_nodes: string;
  reference_sql: string;
}

/** One tool call in an answer (same shape for Recorded and Live; see agents.parse_response). */
export interface Step {
  tool: string | null;
  type: string | null;
  sql: string | null;
  input: string | null;
  status: string | null;
  rows: number | null;
}

export type VerdictLabel = "correct" | "partial" | "wrong" | null;

/** An agent's answer plus its trace and (once judged) its score. */
export interface Answer {
  text: string;
  elapsed: number;
  tokens: { input?: number; output?: number };
  steps: Step[];
  tool_calls: number;
  tool_counts: Record<string, number>;
  sql: string[];
  ontology_hits?: string[];
  score?: number | null;
  verdict?: VerdictLabel;
  judge_reason?: string | null;
}

export interface RecordedResult {
  id: number;
  challenge: string;
  question: string;
  expected: string;
  naive_trap: string;
  headline: string | null;
  answers: Record<Side, Answer>;
}

export interface RecordedRun {
  run_id: string;
  judge_model: string;
  pass_threshold: number;
  role?: string;
  results: RecordedResult[];
}

/** Graded verdict from the shared judge (app/backend/judge.py). */
export interface Verdict {
  baseline_score?: number;
  ontology_score?: number;
  baseline_verdict?: VerdictLabel;
  ontology_verdict?: VerdictLabel;
  baseline_reason?: string;
  ontology_reason?: string;
  headline?: string;
}

export interface StreamEvent {
  type: string;
  side?: Side;
  text?: string;
  status?: string;
  message?: string;
  name?: string;
  sql?: string;
  ms?: number;
  final?: Answer;
  verdict?: Verdict;
  error?: string;
  compare_id?: string;
}

export interface SetupInfo {
  semantic_views: {
    fqn: string;
    name: string;
    file: string;
    description: string;
    tables: { name: string; base: string; description: string }[];
    imports: string[];
    relationships: number;
  }[];
  agents: { name: string; fqn: string; group: string; file: string; tools: string[]; semantic_views: string[]; yaml: string }[];
  challenges: { id: string; title: string }[];
  ontology: {
    terms: number;
    relationships: number;
    domains: { name: string; description: string; terms: number; kinds: Record<string, number> }[];
  };
  questions: { id: number; question: string; challenge: string; expected: string }[];
}

export interface LiveStatus {
  connected: boolean;
  connection: string;
  role: string;
  warehouse: string;
}

export const AGENT_INFO: Record<Side, { label: string; sublabel: string; color: string }> = {
  baseline: {
    label: "Without ontology",
    sublabel: "GAMING_BASELINE_AGENT: text-to-SQL over SV_GAMING_CROSS_DOMAIN",
    color: "var(--baseline)",
  },
  ontology: {
    label: "With Business Ontology",
    sublabel: "GAMING_BON_AGENT: ontology search + the same semantic view",
    color: "var(--sense)",
  },
};

export const TOOL_LABEL: Record<string, string> = {
  business_ontology: "Ontology search",
  query_data: "Cortex Analyst",
  system_execute_sql: "SQL",
  data_to_chart: "Chart",
};

/** "C3 imperfect keys" -> 3; anything without a C<n> code sorts last. */
export function challengeNum(tag: string): number {
  const m = tag.match(/\bC(\d)\b/);
  return m ? Number(m[1]) : 9;
}

/** Sort key: challenge number, then controls after the trap questions, then id. */
export function byChallenge<T extends { challenge: string; id: number }>(a: T, b: T): number {
  return (
    challengeNum(a.challenge) - challengeNum(b.challenge) ||
    Number(a.challenge.startsWith("control")) - Number(b.challenge.startsWith("control")) ||
    a.id - b.id
  );
}

export async function getJSON<T>(url: string): Promise<T> {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`${url}: HTTP ${r.status} ${await r.text()}`);
  return r.json();
}

/** POST and read the server-sent event stream (EventSource can't POST). */
export async function streamCompare(
  body: { question_id?: number; text?: string },
  onEvent: (e: StreamEvent) => void,
  signal: AbortSignal,
): Promise<void> {
  const r = await fetch("/api/compare", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });
  if (!r.ok || !r.body) throw new Error(`compare failed: HTTP ${r.status} ${await r.text()}`);
  const reader = r.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    let idx;
    while ((idx = buf.indexOf("\n\n")) >= 0) {
      const chunk = buf.slice(0, idx);
      buf = buf.slice(idx + 2);
      const data = chunk
        .split("\n")
        .filter((l) => l.startsWith("data:"))
        .map((l) => l.slice(5).trimStart())
        .join("\n");
      if (data) onEvent(JSON.parse(data));
    }
  }
}
