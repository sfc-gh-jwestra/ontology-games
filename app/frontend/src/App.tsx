import { useEffect, useState } from "react";
import { getJSON, Question, RecordedRun, SetupInfo } from "./api";
import AnalysisView from "./components/AnalysisView";
import CompareView from "./components/CompareView";
import SetupView from "./components/SetupView";

type Tab = "setup" | "compare" | "analysis";
const TABS: { id: Tab; label: string }[] = [
  { id: "setup", label: "Setup" },
  { id: "compare", label: "Compare" },
  { id: "analysis", label: "Analysis" },
];

export default function App() {
  const [tab, setTab] = useState<Tab>("compare");
  const [questions, setQuestions] = useState<Question[]>([]);
  const [recorded, setRecorded] = useState<RecordedRun | null>(null);
  const [recordedError, setRecordedError] = useState<string | null>(null);
  const [challenges, setChallenges] = useState<Record<string, string>>({});

  useEffect(() => {
    getJSON<Question[]>("/api/questions").then(setQuestions).catch(() => setQuestions([]));
    getJSON<RecordedRun>("/api/recorded").then(setRecorded).catch((e) => setRecordedError(String(e)));
    getJSON<SetupInfo>("/api/setup")
      .then((s) => setChallenges(Object.fromEntries(s.challenges.map((c) => [c.id, c.title]))))
      .catch(() => setChallenges({}));
  }, []);

  return (
    <>
      <header className="header">
        <div className="container">
          <h1>Gaming Analytics: two agents, with and without Business Ontology</h1>
          <p className="muted">
            The same semantic view, the same {questions.length || 13} questions. One agent also searches the Business
            Ontology for governed definitions, synonyms, code mappings and identity rules. Questions are grouped by the
            seven data challenges (C1-C7).
          </p>
        </div>
      </header>
      <main className="container">
        <nav className="tabs">
          {TABS.map((t) => (
            <button key={t.id} className={tab === t.id ? "active" : ""} onClick={() => setTab(t.id)}>
              {t.label}
            </button>
          ))}
        </nav>
        {tab === "setup" && <SetupView />}
        {tab === "compare" && <CompareView questions={questions} recorded={recorded} recordedError={recordedError} />}
        {tab === "analysis" && <AnalysisView recorded={recorded} recordedError={recordedError} challenges={challenges} />}
      </main>
    </>
  );
}
