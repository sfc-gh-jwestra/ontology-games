// Types and API helpers shared by the UI.

export type Side = "baseline" | "ontology";

export interface Question {
  id: number;
  question: string;
  challenge: string;
  expected: string;
  naive_trap: string;
  fixing_nodes: string;
  reference_sql: string;
}

export interface Me {
  user: string;
  role: string;
  secondary_roles: string;
  warehouse: string | null;
}

export interface Final {
  text: string;
  sql: string[];
  tools: string[];
  tables: unknown[];
  ontology_hits: string[];
  status: string | null;
}

export interface Verdict {
  baseline_correct?: boolean;
  ontology_correct?: boolean;
  differ?: boolean;
  headline?: string;
  summary?: string;
  evidence?: string[];
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
  final?: Final;
  verdict?: Verdict;
  error?: string;
  compare_id?: string;
}

export interface Roles {
  roles: string[];
  default: string;
}

/** Thrown on HTTP 401: the user isn't signed in (or the session expired). */
export class Unauthorized extends Error {}

export function signInUrl(role: string) {
  return `/oauth/login?role=${encodeURIComponent(role)}`;
}

export async function getJSON<T>(url: string): Promise<T> {
  const r = await fetch(url);
  if (r.status === 401) throw new Unauthorized(await r.text());
  if (!r.ok) throw new Error(`${url}: HTTP ${r.status}`);
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
  if (r.status === 401) throw new Unauthorized(await r.text());
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
