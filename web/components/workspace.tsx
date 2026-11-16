"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, useEffect, useRef } from "react";
import {
  LayoutDashboard,
  NotebookPen,
  Camera,
  ChartNoAxesCombined,
  History,
  FileText,
  Wind,
  Settings,
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
import { useReducedMotion } from "motion/react";
import { Logo } from "./navigation";
import { useStill } from "./state";
import { gad, report, download, api, Session } from "@/lib/session";
import { Assessment } from "./questionnaire";
import { Results } from "./results";
import { Heading, Empty } from "./screen-frames";
const GuidedAssessment = dynamic(() => import("./guided-assessment"), {
  ssr: false,
  loading: () => (
    <div className="skeleton" role="status">
      Preparing your assessment…
    </div>
  ),
});
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
  ["guided", "Guided assessment", NotebookPen],
  ["assessment", "Questionnaire only", NotebookPen],
  ["camera", "Video session", Camera],
  ["results", "Your results", ChartNoAxesCombined],
  ["history", "Session history", History],
  ["reports", "Reports", FileText],
  ["tools", "Wellbeing tools", Wind],
  ["settings", "Settings & privacy", Settings],
] as const;
export function WorkspaceShell({ children }: { children: React.ReactNode }) {
  const path = usePathname();
  const [open, setOpen] = useState(false);
  const drawer = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    drawer.current?.close();
    setOpen(false);
  }, [path]);
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
            onClick={() => {
              setOpen(true);
              drawer.current?.showModal();
            }}
            aria-label="Open workspace navigation"
            aria-expanded={open}
          >
            {open ? <X /> : <Menu />}
          </button>
        </header>
        <dialog
          ref={drawer}
          className="mobile-drawer"
          onClose={() => setOpen(false)}
          onClick={(event) => {
            if (event.target === drawer.current) drawer.current?.close();
          }}
        >
          <div>
            <div className="row between">
              <Logo />
              <button
                className="icon-button"
                aria-label="Close workspace navigation"
                onClick={() => drawer.current?.close()}
              >
                <X />
              </button>
            </div>
            <nav aria-label="Mobile workspace">
              {nav.map(([slug, name]) => (
                <Link
                  key={slug}
                  href={"/workspace" + (slug ? "/" + slug : "")}
                  onClick={() => drawer.current?.close()}
                >
                  {name}
                </Link>
              ))}
            </nav>
          </div>
        </dialog>
        <main id="main" className="workspace-main">
          {children}
        </main>
        <footer className="workspace-footer">
          <span>Still · Screening & Video Analysis</span>
          <Link href="/privacy">Your data choices</Link>
        </footer>
      </div>
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
            Answer the questionnaire, record a short video, and review your
            screening results and video observations.
          </p>
          <Link className="button" href="/workspace/guided">
            {answers.some((a) => a !== null)
              ? "Resume assessment"
              : "Start assessment"}{" "}
            <ArrowUpRight size={18} />
          </Link>
          <Link className="text-link" href="/workspace/assessment">
            {done && done < 7
              ? `Resume check-in · ${done}/7 answered`
              : "Questionnaire only"}{" "}
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
              <Link
                href={
                  current.assessment_type === "combined" && !current.camera
                    ? "/workspace/guided"
                    : "/workspace/results"
                }
                className="text-link"
              >
                {current.assessment_type === "combined" && !current.camera
                  ? "Continue assessment"
                  : "View results"}{" "}
                <ArrowRight size={15} />
              </Link>
            </>
          ) : (
            <>
              <h3>
                A blank page is
                <br />a good beginning.
              </h3>
              <p>
                Your results will appear after questionnaire review and video
                processing.
              </p>
            </>
          )}
        </section>
        <Link href="/workspace/camera" className="card dashboard-camera">
          <Camera size={24} />
          <p className="eyebrow">A SEPARATE PERSPECTIVE</p>
          <h3>A clearer view.</h3>
          <p>
            Record 35 seconds for face-tracking, geometric and pulse
            measurements processed on this computer.
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
        <p className="eyebrow">
          {session.screening && session.camera
            ? "Combined assessment"
            : session.screening
              ? "Questionnaire only"
              : "Video analysis"}
        </p>
        <p>
          {session.screening
            ? `Questionnaire results · GAD-7 ${session.screening.score}/21 · ${session.screening.category}`
            : "Video analysis only"}{" "}
          ·{" "}
          {session.camera?.source === "prerecorded"
            ? "Video analysis · Prerecorded"
            : session.camera
              ? "Video analysis · Webcam"
              : "Video analysis not included"}
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
  let content;
  switch (section) {
    case "guided":
      content = <GuidedAssessment />;
      break;
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
    <div key={section} className="workspace-screen">
      {content}
    </div>
  );
}
