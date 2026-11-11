"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, useEffect } from "react";
import {
  LayoutDashboard,
  NotebookPen,
  Camera,
  ChartNoAxesCombined,
  History,
  FileText,
  Wind,
  Settings,
  FlaskConical,
  ArrowUpRight,
  ArrowRight,
  ChevronLeft,
  Menu,
  X,
  Check,
  Download,
  Printer,
  Trash2,
  LockKeyhole,
  Leaf,
  Play,
  Pause,
  RotateCcw,
} from "lucide-react";
import dynamic from "next/dynamic";
import { motion, useReducedMotion } from "motion/react";
import { Logo } from "./navigation";
import { useStill } from "./state";
import { gad, scoreGad, report, download, api, Session } from "@/lib/session";
import { Observations } from "./observations";
const CameraSession = dynamic(() => import("./camera"), {
  ssr: false,
  loading: () => (
    <div className="skeleton" role="status">
      Preparing camera controls…
    </div>
  ),
});
const Trend = dynamic(() => import("./trend"), { ssr: false });
const nav = [
  ["", "Your overview", LayoutDashboard],
  ["assessment", "Questionnaire", NotebookPen],
  ["camera", "Camera session", Camera],
  ["results", "Your results", ChartNoAxesCombined],
  ["history", "Session history", History],
  ["reports", "Reports", FileText],
  ["tools", "Wellbeing tools", Wind],
  ["settings", "Settings & privacy", Settings],
] as const;
export function WorkspaceShell({ children }: { children: React.ReactNode }) {
  const path = usePathname();
  const [open, setOpen] = useState(false);
  useEffect(() => setOpen(false), [path]);
  return (
    <div className="workspace">
      <aside className="sidebar">
        <Logo />
        <div className="sidebar-label eyebrow">YOUR QUIET CORNER</div>
        <nav aria-label="Workspace">
          {nav.map(([slug, name, Icon]) => (
            <Link
              key={slug}
              aria-current={
                path === "/workspace" + (slug ? "/" + slug : "")
                  ? "page"
                  : undefined
              }
              href={"/workspace" + (slug ? "/" + slug : "")}
            >
              <Icon size={18} />
              {name}
            </Link>
          ))}
        </nav>
        <Link className="research-link" href="/research">
          <FlaskConical size={17} /> Research & limitations{" "}
          <ArrowUpRight size={14} />
        </Link>
        <div className="sidebar-bottom">
          <LockKeyhole size={17} />
          <p>
            Private by default.
            <br />
            Saved only by choice.
          </p>
        </div>
      </aside>
      <div className="workspace-body">
        <header className="workspace-header">
          <Link className="back-home" href="/">
            <ChevronLeft size={15} /> Back to Still
          </Link>
          <span className="pill">
            <span className="status-dot" /> Local-first workspace
          </span>
          <button
            className="icon-button mobile-menu"
            onClick={() => setOpen(!open)}
            aria-label="Open workspace navigation"
            aria-expanded={open}
          >
            {open ? <X /> : <Menu />}
          </button>
        </header>
        {open && (
          <nav className="mobile-workspace" aria-label="Mobile workspace">
            {nav.map(([s, n]) => (
              <Link key={s} href={"/workspace" + (s ? "/" + s : "")}>
                {n}
              </Link>
            ))}
          </nav>
        )}
        <main id="main" className="workspace-main">
          {children}
        </main>
        <footer className="workspace-footer">
          <span>Still · Anxiety Screening & Wellbeing</span>
          <Link href="/privacy">Your data choices</Link>
        </footer>
      </div>
    </div>
  );
}
function Heading({
  label,
  title,
  sub,
}: {
  label: string;
  title: string;
  sub?: string;
}) {
  return (
    <div className="page-heading">
      <p className="eyebrow">{label}</p>
      <h1>{title}</h1>
      {sub && <p>{sub}</p>}
    </div>
  );
}
function Empty({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="card empty">
      <Leaf size={28} />
      <h3>{title}</h3>
      {children}
    </div>
  );
}
function Dashboard() {
  const { current, history, answers, newSession } = useStill();
  const done = answers.filter((x) => x !== null).length;
  return (
    <>
      <Heading
        label="WELCOME TO YOUR SPACE"
        title="A softer place to start."
        sub="Make time for yourself. Everything here is yours to explore, or to leave for another day."
      />
      {(current.screening || current.camera) && (
        <button
          className="text-link"
          onClick={() => {
            if (
              window.confirm(
                "Start a fresh temporary session? Unsaved answers and observations will be cleared.",
              )
            )
              newSession();
          }}
        >
          <RotateCcw size={14} /> Start a fresh session
        </button>
      )}
      <div className="dashboard-grid">
        <section className="dashboard-primary card">
          <span className="pill">YOUR NEXT SMALL STEP</span>
          <h2>
            A moment of
            <br />
            <em>honest reflection.</em>
          </h2>
          <p>
            Seven questions. The last two weeks.
            <br />
            No need to have it all figured out.
          </p>
          <Link className="button" href="/workspace/assessment">
            {done && done < 7
              ? `Resume check-in · ${done}/7 answered`
              : "Begin your check-in"}{" "}
            <ArrowUpRight size={18} />
          </Link>
          <span className="micro">
            <LockKeyhole size={13} /> Answers stay in this browser session.
          </span>
        </section>
        <Link href="/workspace/tools" className="card dashboard-breathe">
          <div className="breath-art" aria-hidden="true">
            <div />
            <div />
            <Wind size={28} />
          </div>
          <p className="eyebrow">ROOM TO RESET</p>
          <h3>A breath of space.</h3>
          <p>
            A simple paced-breathing timer.
            <br />
            Nothing to achieve.
          </p>
          <span className="text-link">
            Take a pause <ArrowUpRight size={16} />
          </span>
        </Link>
        <section className="card dashboard-summary">
          <div className="row between">
            <p className="eyebrow">YOUR CURRENT CHECK-IN</p>
            <NotebookPen size={21} />
          </div>
          {current.screening ? (
            <>
              <h3>
                {current.screening.score} <span className="muted">/ 21</span>
              </h3>
              <p>
                {current.screening.category} symptoms · Questionnaire-derived
              </p>
              <Link href="/workspace/results" className="text-link">
                View your result <ArrowRight size={15} />
              </Link>
            </>
          ) : (
            <>
              <h3>
                A blank page is
                <br />a good beginning.
              </h3>
              <p>
                Your result will appear after you complete the questionnaire.
              </p>
            </>
          )}
        </section>
        <Link href="/workspace/camera" className="card dashboard-camera">
          <Camera size={24} />
          <p className="eyebrow">A SEPARATE PERSPECTIVE</p>
          <h3>Observe, if you like.</h3>
          <p>
            Optional camera observations. Always distinct from your screening
            result.
          </p>
          <span className="text-link">
            Explore camera session <ArrowUpRight size={16} />
          </span>
        </Link>
      </div>
      <div className="row between section-title">
        <h2>Recent moments</h2>
        <Link className="text-link" href="/workspace/history">
          View history <ArrowUpRight size={15} />
        </Link>
      </div>
      {history.length === 0 ? (
        <Empty title="Nothing saved. And that’s okay.">
          <p>
            Sessions are temporary by default. You can choose to save a
            completed check-in when it feels right.
          </p>
        </Empty>
      ) : (
        <div className="card">
          {history.slice(0, 3).map((s) => (
            <SavedRow key={s.id} session={s} />
          ))}
        </div>
      )}
      <p className="micro">
        GAD-7 covers two weeks. Repeating it throughout a day does not measure
        momentary changes.
      </p>
    </>
  );
}
function Assessment() {
  const { answers, setAnswers, current, setCurrent } = useStill();
  const [step, setStep] = useState(0);
  const [difficulty, setDifficulty] = useState("");
  const [error, setError] = useState("");
  const routerPath = "/workspace/results";
  const complete = answers.every((x) => x !== null);
  function finish() {
    try {
      setCurrent({
        ...current,
        date: new Date().toISOString(),
        screening: scoreGad(answers),
        difficulty,
      });
    } catch {
      setError("Complete every question before calculating a result.");
      return false;
    }
    return true;
  }
  return (
    <>
      <Heading
        label="GAD-7 / QUESTIONNAIRE-DERIVED SCREENING"
        title="Make room for how you feel."
        sub="Take your time. Your answers stay in browser memory unless you choose to save the result."
      />
      <section className="assessment card">
        <div className="row between">
          <span className="eyebrow">
            {step < 7 ? `QUESTION ${step + 1} OF 7` : "REVIEW YOUR RESPONSES"}
          </span>
          <span className="muted">
            {answers.filter((x) => x !== null).length}/7 answered
          </span>
        </div>
        <div
          className="step-progress"
          aria-label={`${answers.filter((x) => x !== null).length} of 7 answered`}
        >
          {gad.questions.map((_, i) => (
            <span className={answers[i] !== null ? "filled" : ""} key={i} />
          ))}
        </div>
        <p className="timeframe">{gad.timeframe}</p>
        {step < 7 ? (
          <fieldset>
            <legend>{gad.questions[step]}</legend>
            <div className="answer-options">
              {gad.responses.map((label, value) => (
                <label
                  key={value}
                  className={answers[step] === value ? "selected" : ""}
                >
                  <input
                    type="radio"
                    name={"item-" + step}
                    checked={answers[step] === value}
                    onChange={() => {
                      const a = [...answers];
                      a[step] = value;
                      setAnswers(a);
                      setCurrent({ ...current, screening: null });
                    }}
                  />
                  <span>{label}</span>
                  <span className="answer-score">{value}</span>
                </label>
              ))}
            </div>
          </fieldset>
        ) : (
          <>
            <div className="review-list">
              {gad.questions.map((q, i) => (
                <button key={q} onClick={() => setStep(i)}>
                  <span>
                    {i + 1}. {q}
                  </span>
                  <strong>
                    {answers[i] === null
                      ? "Not answered"
                      : gad.responses[answers[i]!]}
                  </strong>
                </button>
              ))}
            </div>
            <label className="field">
              How difficult have these problems made it for you to do your work,
              take care of things at home, or get along with other people?
              <select
                value={difficulty}
                onChange={(e) => setDifficulty(e.target.value)}
              >
                <option value="">Optional context — not scored</option>
                {[
                  "Not difficult at all",
                  "Somewhat difficult",
                  "Very difficult",
                  "Extremely difficult",
                ].map((v) => (
                  <option key={v}>{v}</option>
                ))}
              </select>
            </label>
          </>
        )}
        <div className="row between assessment-actions">
          <button
            className="button secondary"
            disabled={step === 0}
            onClick={() => setStep(step - 1)}
          >
            Back
          </button>
          {step < 7 ? (
            <button
              className="button"
              disabled={answers[step] === null}
              onClick={() => setStep(step + 1)}
            >
              {step === 6 ? "Review answers" : "Next question"}{" "}
              <ArrowRight size={16} />
            </button>
          ) : (
            <Link
              aria-disabled={!complete}
              className={"button" + (!complete ? " disabled" : "")}
              href={routerPath}
              onClick={(e) => {
                if (!complete || !finish()) e.preventDefault();
              }}
            >
              Calculate my screening result <ArrowRight size={16} />
            </Link>
          )}
        </div>
        {error && (
          <p role="alert" className="error">
            {error}
          </p>
        )}
      </section>
      <p className="attribution micro">
        {gad.attribution} <a href={gad.source}>Published form</a> ·{" "}
        <a href={gad.scoring_source}>Scoring guide</a>
      </p>
      <p className="micro">
        Screening is not diagnosis. These categories are not equivalent to UBFC
        CSAI scores.
      </p>
    </>
  );
}
function Results({ printed = false }: { printed?: boolean }) {
  const { current, setCurrent, save, storageError } = useStill();
  const [saved, setSaved] = useState(false);
  const anything = !!(current.screening || current.camera);
  if (!anything)
    return (
      <>
        <Heading label="YOUR RESULTS" title="Your perspective starts here." />
        <Empty title="No result to show yet.">
          <p>
            Complete the questionnaire, add camera observations, or open a saved
            session from history.
          </p>
          <Link className="button" href="/workspace/assessment">
            Begin questionnaire <ArrowRight size={16} />
          </Link>
        </Empty>
      </>
    );
  return (
    <>
      <Heading
        label={
          printed ? "SESSION REPORT" : "YOUR RESULTS / TWO SEPARATE SOURCES"
        }
        title={printed ? "A moment, on paper." : "A clearer perspective."}
        sub={new Date(current.date).toLocaleString()}
      />
      {current.screening ? (
        <section className="card screening-result">
          <div>
            <span className="eyebrow">QUESTIONNAIRE-DERIVED · GAD-7</span>
            <h2>
              {current.screening.category}
              <br />
              <em>reported symptoms.</em>
            </h2>
            <p>
              Based on your answers about the last two weeks.
              <br />A screening category, not a diagnosis.
            </p>
          </div>
          <div className="score-circle">
            <strong data-testid="screening-score">
              {current.screening.score}
            </strong>
            <span>OUT OF 21</span>
          </div>
          <div className="score-scale">
            {gad.bands.map((b) => (
              <span
                className={
                  b.label === current.screening!.category ? "active" : ""
                }
                key={b.label}
              >
                {b.label}
                <small>
                  {b.min}–{b.max}
                </small>
              </span>
            ))}
          </div>
          <p className="micro">
            If symptoms affect your daily life or concern you, consider
            discussing them with a qualified professional. The camera does not
            validate or change this result.
          </p>
        </section>
      ) : (
        <div className="notice">
          Questionnaire not completed. No screening result has been calculated.
        </div>
      )}
      {current.difficulty && (
        <p className="notice">
          Unscored day-to-day difficulty: {current.difficulty}
        </p>
      )}
      <div className="row between section-title">
        <h2>Camera observations</h2>
        {!printed && (
          <Link className="text-link" href="/workspace/camera">
            {current.camera
              ? "Record a new observation"
              : "Add an optional observation"}{" "}
            <ArrowUpRight size={16} />
          </Link>
        )}
      </div>
      <Observations camera={current.camera} />
      {current.camera && (
        <details className="card">
          <summary>Measurement software and settings</summary>
          <pre>{JSON.stringify(current.camera.versions, null, 2)}</pre>
        </details>
      )}
      <section className="card">
        <label className="field">
          A note to yourself (optional)
          <textarea
            rows={3}
            value={current.note}
            onChange={(e) => setCurrent({ ...current, note: e.target.value })}
            placeholder="What would you like to remember?"
          />
        </label>
        <p className="micro">
          A note stays temporary until you save this session or download a
          report.
        </p>
      </section>
      <section className="print-only">
        <h3>Session note</h3>
        <p>{current.note || "No note added."}</p>
        {current.camera && (
          <>
            <h3>Measurement software and settings</h3>
            <pre>{JSON.stringify(current.camera.versions, null, 2)}</pre>
          </>
        )}
      </section>
      <div className="report-actions no-print">
        <button
          className="button"
          onClick={() => {
            save();
            setSaved(true);
          }}
        >
          <Check size={16} />
          {saved
            ? "Save again in this browser"
            : "Save this session in this browser"}
        </button>
        <button
          className="button secondary"
          onClick={() => download(report(current), "still-session-report.json")}
        >
          <Download size={16} /> Download JSON report
        </button>
        <button className="button secondary" onClick={() => window.print()}>
          <Printer size={16} /> Print / save PDF
        </button>
      </div>
      {saved && !storageError && (
        <p role="status" className="notice">
          Saved locally in this browser. Raw questionnaire answers are not
          saved.
        </p>
      )}
      {storageError && (
        <p role="alert" className="error">
          {storageError}
        </p>
      )}
      <p className="micro">
        Still 1.0.0 · GAD-7 English · Screening and observations are separate.
        This report contains sensitive information; keep downloads private.
      </p>
      <p className="attribution micro">{gad.attribution}</p>
    </>
  );
}
function SavedRow({ session }: { session: Session }) {
  const { open } = useStill();
  return (
    <div className="saved-row">
      <div>
        <strong>
          {new Date(session.date).toLocaleDateString(undefined, {
            year: "numeric",
            month: "short",
            day: "numeric",
          })}
        </strong>
        <p>
          {session.screening
            ? `GAD-7 ${session.screening.score}/21 · ${session.screening.category}`
            : "Camera observations only"}{" "}
          ·{" "}
          {session.camera?.source === "prerecorded"
            ? "Prerecorded"
            : session.camera
              ? "Webcam"
              : "No camera"}
        </p>
      </div>
      <Link
        className="text-link"
        href="/workspace/results"
        onClick={() => open(session)}
      >
        Open session <ArrowUpRight size={16} />
      </Link>
    </div>
  );
}
function HistoryPage() {
  const { history, remove, storageError } = useStill();
  const [after, setAfter] = useState("");
  const [before, setBefore] = useState("");
  const [error, setError] = useState("");
  const [deleting, setDeleting] = useState("");
  const filtered = history.filter(
    (s) =>
      (!after || s.date.slice(0, 10) >= after) &&
      (!before || s.date.slice(0, 10) <= before),
  );
  async function erase(s: Session) {
    setDeleting(s.id);
    try {
      if (s.recordingId)
        await api("/jobs/" + s.recordingId, { method: "DELETE" });
      remove(s.id);
      setError("");
    } catch {
      setError(
        "The retained recording could not be deleted. Start the local backend and retry; the session has not been removed.",
      );
    } finally {
      setDeleting("");
    }
  }
  return (
    <>
      <Heading
        label="SAVED BY CHOICE"
        title="Your recent moments."
        sub="Only sessions you explicitly saved appear here. GAD-7 reflects two weeks, not moment-to-moment changes."
      />
      <div className="filters">
        <label className="field">
          From
          <input
            type="date"
            value={after}
            onChange={(e) => setAfter(e.target.value)}
          />
        </label>
        <label className="field">
          Through
          <input
            type="date"
            value={before}
            onChange={(e) => setBefore(e.target.value)}
          />
        </label>
        <button
          className="text-link"
          onClick={() => {
            setAfter("");
            setBefore("");
          }}
        >
          Clear dates
        </button>
      </div>
      {filtered.length ? (
        <section className="card">
          {filtered.map((s) => (
            <div key={s.id}>
              <SavedRow session={s} />
              <button
                className="text-link delete-link"
                disabled={!!deleting}
                onClick={() => void erase(s)}
              >
                <Trash2 size={14} />
                {deleting === s.id ? "Deleting…" : "Delete this saved session"}
              </button>
            </div>
          ))}
        </section>
      ) : (
        <Empty
          title={
            history.length
              ? "No sessions in this date range."
              : "Nothing saved yet."
          }
        >
          <p>
            Save a completed session when you want to keep it. There is no
            automatic history.
          </p>
        </Empty>
      )}
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {storageError && (
        <p className="error" role="alert">
          {storageError}
        </p>
      )}
      <Trend sessions={history} />
    </>
  );
}
function Tools() {
  const { reduced } = useStill();
  const systemReduced = useReducedMotion();
  const [running, setRunning] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [pace, setPace] = useState(4);
  const [checks, setChecks] = useState<boolean[]>(Array(5).fill(false));
  const [note, setNote] = useState("");
  const [message, setMessage] = useState("");
  useEffect(() => {
    try {
      setNote(localStorage.getItem("still:notes") || "");
    } catch {}
  }, []);
  useEffect(() => {
    if (!running) return;
    const timer = setInterval(() => setElapsed((x) => x + 1), 1000);
    return () => clearInterval(timer);
  }, [running]);
  const inhale = elapsed % (pace * 2) < pace;
  return (
    <>
      <Heading
        label="GENERAL WELLBEING / NOT TREATMENT"
        title="A little room to reset."
        sub="Optional tools for a pause. No performance targets, no promises of treatment."
      />
      <div className="two-grid">
        <section className="card breathing">
          <p className="eyebrow">PACED BREATHING</p>
          <div
            className={
              "breathing-orb " +
              (running && inhale && !reduced && !systemReduced
                ? "expanded"
                : "")
            }
            style={{ transitionDuration: pace + "s" }}
          >
            <Wind size={28} />
            <h3>
              {running
                ? inhale
                  ? "Breathe in"
                  : "Breathe out"
                : "At your pace"}
            </h3>
            <span>
              {Math.floor(elapsed / 60)}:{String(elapsed % 60).padStart(2, "0")}
            </span>
          </div>
          <label className="field">
            Seconds per inhale / exhale
            <select
              value={pace}
              disabled={running}
              onChange={(e) => {
                setPace(Number(e.target.value));
                setElapsed(0);
              }}
            >
              {[3, 4, 5, 6].map((n) => (
                <option value={n} key={n}>
                  {n} seconds each
                </option>
              ))}
            </select>
          </label>
          <div className="row">
            <button className="button" onClick={() => setRunning(!running)}>
              {running ? <Pause size={16} /> : <Play size={16} />}{" "}
              {running ? "Pause" : "Start"}
            </button>
            <button
              className="button secondary"
              onClick={() => {
                setRunning(false);
                setElapsed(0);
              }}
            >
              <RotateCcw size={16} />
              Reset
            </button>
          </div>
          <p className="micro">
            Breathe comfortably, without holding or forcing. Stop if
            uncomfortable. This is a general wellbeing timer, not anxiety
            treatment.
          </p>
        </section>
        <section className="card">
          <p className="eyebrow">A SIMPLE GROUNDING PAUSE</p>
          <h2>
            Notice
            <br />
            <em>what’s here.</em>
          </h2>
          {[
            "Five things you can see",
            "Four things you can feel",
            "Three things you can hear",
            "Two things you can smell",
            "One thing you can taste",
          ].map((x, i) => (
            <label className="check grounding" key={x}>
              <input
                type="checkbox"
                checked={checks[i]}
                onChange={() =>
                  setChecks(checks.map((v, j) => (i === j ? !v : v)))
                }
              />
              {x}
            </label>
          ))}
          <button
            className="text-link"
            onClick={() => setChecks(Array(5).fill(false))}
          >
            Reset checklist
          </button>
        </section>
      </div>
      <section className="card">
        <p className="eyebrow">A PRIVATE NOTE</p>
        <label className="field">
          Something you’d like to make space for
          <textarea
            rows={5}
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="No need to make it perfect."
          />
        </label>
        <div className="row">
          <button
            className="button"
            onClick={() => {
              try {
                localStorage.setItem("still:notes", note);
                setMessage("Note saved in this browser only.");
              } catch {
                setMessage("Saving failed; your note is still temporary.");
              }
            }}
          >
            Save note in this browser
          </button>
          <button
            className="button secondary"
            onClick={() => {
              localStorage.removeItem("still:notes");
              setNote("");
              setMessage("Saved note deleted.");
            }}
          >
            Delete note
          </button>
        </div>
        <p className="micro" role="status">
          {message ||
            "Typing does not save automatically. Browser storage is not encrypted."}
        </p>
      </section>
    </>
  );
}
function SettingsPage() {
  const s = useStill();
  const [recordings, setRecordings] = useState<
    { id: string; created: string }[]
  >([]);
  const [message, setMessage] = useState("");
  const [ready, setReady] = useState(false);
  const [busy, setBusy] = useState(false);
  const refresh = () =>
    api("/recordings")
      .then((r) => {
        setRecordings(r.recordings);
        setReady(true);
      })
      .catch(() => {
        setReady(false);
        setMessage(
          "Local backend unavailable. Server storage cannot be checked.",
        );
      });
  useEffect(() => {
    void refresh();
  }, []);
  return (
    <>
      <Heading label="SETTINGS & PRIVACY" title="Make this space yours." />
      <section className="card">
        <h3>Reading & motion</h3>
        <label className="field">
          Appearance
          <select value={s.theme} onChange={(e) => s.setTheme(e.target.value)}>
            <option value="light">Warm ivory</option>
            <option value="dark">Evening ink</option>
          </select>
        </label>
        <label className="check">
          <input
            type="checkbox"
            checked={s.reduced}
            onChange={(e) => s.setReduced(e.target.checked)}
          />{" "}
          Reduce decorative motion (system preference is always respected)
        </label>
      </section>
      <section className="card">
        <h3>Storage is always opt-in.</h3>
        <p>
          No automatic session saving. Raw item answers are never stored in
          history. Your current questionnaire answers remain temporary in
          memory.
        </p>
        <p>
          {s.history.length} browser-saved session
          {s.history.length === 1 ? "" : "s"} ·{" "}
          {ready
            ? `${recordings.length} retained local recording(s)`
            : "Server recording count unavailable"}
        </p>
        <button className="text-link" onClick={() => void refresh()}>
          Refresh local storage status
        </button>
        {recordings.map((r) => (
          <div className="saved-row" key={r.id}>
            <span>Recording · {new Date(r.created).toLocaleString()}</span>
            <button
              className="text-link"
              onClick={async () => {
                try {
                  await api("/jobs/" + r.id, { method: "DELETE" });
                  setMessage("Local recording deleted.");
                  void refresh();
                } catch {
                  setMessage(
                    "Deletion failed. Nothing has been reported as deleted.",
                  );
                }
              }}
            >
              Delete recording
            </button>
          </div>
        ))}
        <button
          className="button secondary"
          onClick={() =>
            download(
              {
                version: "Still 1.0.0",
                sessions: s.history,
                note: localStorage.getItem("still:notes") || "",
              },
              "still-saved-data.json",
            )
          }
        >
          <Download size={16} /> Export my saved data
        </button>
      </section>
      <section className="card danger-zone">
        <h3>A clean slate.</h3>
        <p>
          Delete all Still browser sessions and notes, the current in-memory
          session, and all jobs/recordings owned by the local service. Exported
          downloads are yours to remove separately.
        </p>
        <button
          className="button danger"
          disabled={busy}
          onClick={async () => {
            if (
              !window.confirm(
                "Delete all Still sessions, notes and local-server recordings? This cannot be undone.",
              )
            )
              return;
            setBusy(true);
            try {
              await api("/jobs", { method: "DELETE" });
              s.clear();
              setMessage(
                "All Still browser sessions, notes, jobs and retained recordings were deleted.",
              );
              void refresh();
            } catch {
              setMessage(
                "The local service is unavailable; deletion was not completed. Start it and retry.",
              );
            } finally {
              setBusy(false);
            }
          }}
        >
          <Trash2 size={16} />
          {busy ? "Deleting…" : "Delete all Still data"}
        </button>
        <button
          className="text-link"
          onClick={() => {
            if (
              window.confirm(
                "Delete browser sessions, notes and current answers only? Server recordings will remain until deleted separately.",
              )
            ) {
              s.clear();
              setMessage(
                "Browser data deleted. Server recordings were not deleted.",
              );
            }
          }}
        >
          Delete browser data only
        </button>
      </section>
      {message && (
        <p className="notice" role="status">
          {message}
        </p>
      )}
      {s.storageError && (
        <p className="error" role="alert">
          {s.storageError}
        </p>
      )}
      <Link className="text-link" href="/privacy">
        Read the complete storage explanation <ArrowUpRight size={16} />
      </Link>
    </>
  );
}
export function AppScreen({ section }: { section: string }) {
  const { reduced } = useStill();
  const system = useReducedMotion();
  let content;
  switch (section) {
    case "assessment":
      content = <Assessment />;
      break;
    case "camera":
      content = <CameraSession />;
      break;
    case "results":
      content = <Results />;
      break;
    case "history":
      content = <HistoryPage />;
      break;
    case "reports":
      content = <Results printed />;
      break;
    case "tools":
      content = <Tools />;
      break;
    case "settings":
      content = <SettingsPage />;
      break;
    default:
      content = <Dashboard />;
  }
  return (
    <motion.div
      key={section}
      initial={reduced || system ? false : { opacity: 0.5 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.16 }}
    >
      {content}
    </motion.div>
  );
}
