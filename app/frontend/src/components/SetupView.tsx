// Setup tab: what each agent can reach, the semantic views, the ontology and the challenges.
// Everything comes from repo files through /api/setup; no Snowflake connection.
import { useEffect, useState } from "react";
import { AGENT_INFO, getJSON, SetupInfo } from "../api";

export default function SetupView() {
  const [info, setInfo] = useState<SetupInfo | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    getJSON<SetupInfo>("/api/setup").then(setInfo).catch((e) => setError(String(e)));
  }, []);
  if (error) return <div className="err">Could not load setup: {error}</div>;
  if (!info) return <div className="muted">Loading setup...</div>;

  const cross = info.semantic_views.find((v) => v.name === "SV_GAMING_CROSS_DOMAIN");
  const domainViews = info.semantic_views.filter((v) => v.tables.length > 0);
  const tableCount = new Set(domainViews.flatMap((v) => v.tables.map((t) => t.base))).size;
  const demoAgents = info.agents.filter((a) => a.group === "demo");
  const routerAgents = info.agents.filter((a) => a.group !== "demo");

  return (
    <div className="stack">
      <section className="card">
        <h2>How the comparison works</h2>
        <p className="muted">
          Two Cortex Agents answer the same {info.questions.length} questions over the same semantic view. The only
          difference is that one agent also searches the Business Ontology for governed definitions, synonyms, code
          mappings and identity rules.
        </p>
        <div className="arch">
          <div className="arch-col">
            <div className="arch-box" style={{ borderColor: AGENT_INFO.baseline.color }}>
              <b style={{ color: AGENT_INFO.baseline.color }}>{AGENT_INFO.baseline.label}</b>
              <div className="mono small">GAMING_BASELINE_AGENT</div>
              <div className="small">Cortex Analyst (text-to-SQL)</div>
            </div>
            <div className="arch-box" style={{ borderColor: AGENT_INFO.ontology.color }}>
              <b style={{ color: AGENT_INFO.ontology.color }}>{AGENT_INFO.ontology.label}</b>
              <div className="mono small">GAMING_BON_AGENT</div>
              <div className="small">Ontology search, then Cortex Analyst</div>
            </div>
          </div>
          <div className="arch-arrow">&rarr;</div>
          <div className="arch-col">
            <div className="arch-box">
              <b>{cross?.fqn ?? "SV_GAMING_CROSS_DOMAIN"}</b>
              <div className="small">Imports {cross?.imports.join(", ")}: {tableCount} tables and views</div>
              <div className="small muted">Only cross-system join: TITLES.CATALOG_GAME_ID to GAMES</div>
            </div>
            <div className="arch-box" style={{ borderColor: AGENT_INFO.ontology.color }}>
              <b>Business Ontology</b>
              <div className="small">
                {info.ontology.domains.length} domains, {info.ontology.terms} terms, {info.ontology.relationships} relationships
              </div>
              <div className="small muted">Used only by the ontology agent</div>
            </div>
          </div>
          <div className="arch-arrow">&rarr;</div>
          <div className="arch-col">
            <div className="arch-box">
              <b>ONTOLOGY_DEMO.GAME_CATALOG</b>
              <div className="small">Master game catalog</div>
            </div>
            <div className="arch-box">
              <b>ONTOLOGY_DEMO.GAME_SALES</b>
              <div className="small">Store, hardware and subscription sales</div>
            </div>
          </div>
        </div>
      </section>

      <section>
        <h2>Semantic views</h2>
        <div className="grid grid-2">
          {info.semantic_views.map((v) => (
            <details key={v.fqn} className="card">
              <summary>
                <b>{v.fqn}</b>{" "}
                <span className="muted small">
                  {v.tables.length ? `${v.tables.length} tables and views` : "composed view"}
                  {v.imports.length ? `, imports ${v.imports.length}` : ""}, {v.relationships} relationships
                </span>
              </summary>
              <p className="small">{v.description}</p>
              {v.imports.length > 0 && <div className="small">Imports: <span className="mono">{v.imports.join(", ")}</span></div>}
              {v.tables.length > 0 && (
                <ul className="mono small columns">
                  {v.tables.map((t) => <li key={t.name} title={t.description}>{t.base}</li>)}
                </ul>
              )}
              <div className="muted small">Source: {v.file}</div>
            </details>
          ))}
        </div>
      </section>

      <section>
        <h2>Business Ontology domains</h2>
        <div className="grid grid-3">
          {info.ontology.domains.map((d) => (
            <div key={d.name} className="card">
              <b style={{ color: "var(--sense)" }}>{d.name}</b>
              <div className="small">
                {d.terms} terms ({Object.entries(d.kinds).map(([k, n]) => `${n} ${k.toLowerCase()}`).join(", ")})
              </div>
              <p className="muted small">{d.description}</p>
            </div>
          ))}
        </div>
      </section>

      <section>
        <h2>The seven data challenges</h2>
        <div className="card">
          {info.challenges.map((c) => {
            const qs = info.questions.filter((q) => q.challenge.match(/\bC(\d)\b/)?.[0] === c.id);
            return (
              <div key={c.id} className="challenge-row">
                <span className="pill pill-challenge">{c.id}</span>
                <div>
                  <b>{c.title}</b>
                  <ul className="small">
                    {qs.map((q) => (
                      <li key={q.id}>
                        Q{q.id}. {q.question} <span className="muted">({q.challenge})</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            );
          })}
          <div className="muted small">Details: documentation/README_ontology_games_challenges.md</div>
        </div>
      </section>

      <section>
        <h2>Deployed agent definitions</h2>
        <div className="stack-sm">
          {demoAgents.map((a) => <AgentSpec key={a.name} agent={a} />)}
        </div>
        <h3 className="muted">Optional router demo</h3>
        <div className="stack-sm">
          {routerAgents.map((a) => <AgentSpec key={a.name} agent={a} />)}
        </div>
      </section>
    </div>
  );
}

function AgentSpec({ agent }: { agent: SetupInfo["agents"][number] }) {
  return (
    <details className="card">
      <summary>
        <b>{agent.fqn}</b> <span className="muted small">{agent.tools.join(", ")}</span>
      </summary>
      {agent.semantic_views.length > 0 && (
        <div className="small">Semantic view: <span className="mono">{agent.semantic_views.join(", ")}</span></div>
      )}
      <pre className="code">{agent.yaml}</pre>
      <div className="muted small">Source: {agent.file}</div>
    </details>
  );
}
