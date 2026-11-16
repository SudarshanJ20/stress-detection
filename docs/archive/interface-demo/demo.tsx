"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import dynamic from "next/dynamic";
import { motion, useReducedMotion } from "motion/react";
import {
  ArrowRight,
  Check,
  Download,
  Printer,
  RotateCcw,
  ShieldCheck,
  Video,
  NotebookPen,
} from "lucide-react";
import { useStill } from "./state";
import { Assessment } from "./questionnaire";
import { DEMO_LABEL, DEMO_EXAMPLE, download, report, gad } from "@/lib/session";
const DemoCamera = dynamic(() => import("./demo-camera"), {
  ssr: false,
  loading: () => (
    <div className="skeleton" role="status">
      Preparing camera controls…
    </div>
  ),
});
export default function GuidedDemo() {
  const state = useStill();
  const {
    demoPhase: phase,
    setDemoPhase,
    demoSession: session,
    setDemoSession,
    demoAnswers,
    resetDemo,
    reduced,
  } = state;
  const router = useRouter();
  const systemReduced = useReducedMotion();
  const [review, setReview] = useState(false);
  const [error, setError] = useState("");
  const heading = useRef<HTMLHeadingElement>(null);
  const onReview = useCallback((value: boolean) => setReview(value), []);
  const phaseIndex =
    phase === "questionnaire"
      ? review
        ? 1
        : 0
      : phase === "camera"
        ? 2
        : phase === "processing"
          ? 3
          : 4;
  useEffect(() => {
    heading.current?.focus();
  }, [phase]);
  useEffect(() => {
    if (phase !== "processing") return;
    const timer = setTimeout(() => {
      if (!session.screening || !session.demoCapture) {
        setError(
          "The demo could not finish. Review your answers and retry recording.",
        );
        setDemoPhase("camera");
      } else setDemoPhase("results");
    }, 1800);
    return () => clearTimeout(timer);
  }, [phase, session.screening, session.demoCapture, setDemoPhase]);
  function cancel() {
    if (
      window.confirm(
        "Cancel this demo? Its temporary answers and result will be cleared. Nothing has been saved or uploaded.",
      )
    ) {
      resetDemo();
      router.push("/workspace");
    }
  }
  function questionnaireOnly() {
    state.setAnswers([...demoAnswers]);
    state.setCurrent({
      id: crypto.randomUUID(),
      date: new Date().toISOString(),
      mode: "genuine",
      screening: session.screening,
      camera: null,
      note: "",
      difficulty: session.difficulty,
    });
    resetDemo();
    router.push("/workspace/results");
  }
  function fresh() {
    if (
      window.confirm(
        "Start a new demo? This clears the current temporary demo answers and result.",
      )
    ) {
      resetDemo();
      setReview(false);
    }
  }
  const gatedPhase = !session.screening && phase !== "questionnaire";
  return (
    <div className="guided-demo">
      <div className="demo-banner">
        <ShieldCheck size={19} />
        <div>
          <strong>{DEMO_LABEL}</strong>
          <span>
            Interface demonstration · fixed example · no video-based anxiety
            assessment
          </span>
        </div>
      </div>
      <nav className="demo-steps no-print" aria-label="Assessment progress">
        <ol>
          {[
            "Questionnaire",
            "Review",
            "Camera & capture",
            "Demo transition",
            "Results",
          ].map((label, index) => (
            <li
              key={label}
              aria-current={phaseIndex === index ? "step" : undefined}
              className={phaseIndex >= index ? "is-reached" : ""}
            >
              <span>
                {phaseIndex > index ? <Check size={14} /> : index + 1}
              </span>
              <small>{label}</small>
            </li>
          ))}
        </ol>
      </nav>
      <div className="page-heading">
        <p className="eyebrow">A GUIDED DEMONSTRATION</p>
        <h1 tabIndex={-1} ref={heading}>
          {phase === "questionnaire"
            ? "A little space to reflect."
            : phase === "camera"
              ? "Ready when you are."
              : phase === "processing"
                ? "Bringing the example together."
                : "Your check-in, in perspective."}
        </h1>
        <p>
          {phase === "questionnaire"
            ? "Seven questions about the last two weeks, followed by a 35-second camera experience. Your questionnaire score stays separate from the simulated example."
            : phase === "camera"
              ? "A 35-second video interaction. The illustrative result is predefined and never calculated from this recording."
              : phase === "processing"
                ? "Demo transition — illustrative animation only. No video analysis or anxiety inference is taking place."
                : "A fixed design example alongside your genuine questionnaire-derived screening result."}
        </p>
      </div>
      {gatedPhase ? (
        <div className="card">
          <h2>Complete your questionnaire first.</h2>
          <button
            className="button"
            onClick={() => setDemoPhase("questionnaire")}
          >
            Review questionnaire
          </button>
        </div>
      ) : (
        <>
          {phase === "questionnaire" && (
            <>
              <Assessment
                demo
                onReview={onReview}
                onComplete={() => setDemoPhase("camera")}
              />
              <div className="row demo-secondary no-print">
                <Link className="text-link" href="/workspace/assessment">
                  Questionnaire only <ArrowRight size={16} />
                </Link>
                <button className="text-link" onClick={cancel}>
                  Cancel demo
                </button>
              </div>
            </>
          )}
          {phase === "camera" && (
            <DemoCamera
              onBack={() => setDemoPhase("questionnaire")}
              onCancel={cancel}
              onQuestionnaire={questionnaireOnly}
              onComplete={(duration) => {
                setDemoSession({
                  ...session,
                  mode: "demo",
                  demoCapture: {
                    duration_seconds: duration,
                    completed_at: new Date().toISOString(),
                  },
                });
                setDemoPhase("processing");
              }}
            />
          )}
          {phase === "processing" && (
            <section className="card demo-transition" aria-live="polite">
              <div className="demo-transition-art" aria-hidden="true">
                <NotebookPen size={30} />
                <ArrowRight size={22} />
                <Video size={30} />
              </div>
              <p className="eyebrow">DEMO TRANSITION</p>
              <h2>A considered view.</h2>
              <p>
                Preparing the predefined interface example.
                <br />
                Your video is already discarded. No measurements are being
                generated.
              </p>
              <button
                className="text-link"
                onClick={() => setDemoPhase("camera")}
              >
                Cancel transition / retry video
              </button>
            </section>
          )}
          {phase === "results" && (
            <motion.div
              initial={reduced || systemReduced ? false : { y: 12 }}
              animate={{ y: 0 }}
              transition={{ duration: 0.3 }}
            >
              <div className="demo-results-grid">
                <section className="card demo-illustration">
                  <p className="eyebrow">
                    ILLUSTRATIVE EXAMPLE · FIXED FOR EVERYONE
                  </p>
                  <div className="demo-outcome">
                    <div
                      className="demo-score"
                      aria-label="Illustrative score 62 percent"
                    >
                      <strong>
                        {DEMO_EXAMPLE.score}
                        <small>%</small>
                      </strong>
                      <span>{DEMO_EXAMPLE.label}</span>
                    </div>
                    <div>
                      <h2>{DEMO_EXAMPLE.category}</h2>
                      <p>{DEMO_EXAMPLE.explanation}</p>
                    </div>
                  </div>
                  <p className="micro">
                    A proposed visual design, not your anxiety level,
                    probability, confidence or detection accuracy.
                  </p>
                </section>
                <section className="card demo-questionnaire">
                  <NotebookPen size={23} />
                  <p className="eyebrow">QUESTIONNAIRE-DERIVED · GAD-7</p>
                  <div className="demo-real-score">
                    <strong data-testid="demo-screening-score">
                      {session.screening?.score}
                    </strong>
                    <span>/ 21</span>
                  </div>
                  <h2>{session.screening?.category} reported symptoms</h2>
                  <p>
                    Based on your answers about the last two weeks. Screening is
                    not a diagnosis. The simulated example does not confirm or
                    change this result.
                  </p>
                  <div className="demo-bands">
                    {gad.bands.map((band) => (
                      <span
                        key={band.label}
                        className={
                          session.screening?.category === band.label
                            ? "active"
                            : ""
                        }
                      >
                        {band.label}
                        <small>
                          {band.min}–{band.max}
                        </small>
                      </span>
                    ))}
                  </div>
                </section>
              </div>
              <section className="card demo-observations">
                <Video size={23} />
                <div>
                  <p className="eyebrow">WEBCAM OBSERVATIONS · UNAVAILABLE</p>
                  <h3>No measurements generated.</h3>
                  <p>
                    This demo records the interaction only. Pulse, face activity
                    and signal quality are unavailable. No camera data
                    contributed to either score.
                  </p>
                  <span className="source-tag">
                    Source: browser webcam capture ·{" "}
                    {session.demoCapture?.duration_seconds.toFixed(2)} seconds
                    elapsed · discarded
                  </span>
                </div>
              </section>
              <div className="demo-report card">
                <div>
                  <p className="eyebrow">A CLEAR RECORD</p>
                  <h3>Your sources, kept separate.</h3>
                  <p>
                    {DEMO_LABEL}. Reports include the fixed example, your
                    questionnaire score and explicit measurement unavailability.
                    Demo sessions are not saved to history or trends.
                  </p>
                </div>
                <div className="report-actions no-print">
                  <button
                    className="button"
                    onClick={() =>
                      download(report(session), "still-demo-report.json")
                    }
                  >
                    <Download size={16} />
                    Download demo report
                  </button>
                  <button
                    className="button secondary"
                    onClick={() => window.print()}
                  >
                    <Printer size={16} />
                    View / print report
                  </button>
                </div>
              </div>
              <div className="report-actions no-print">
                <button
                  className="button secondary"
                  onClick={() => setDemoPhase("camera")}
                >
                  <RotateCcw size={16} />
                  Retry video
                </button>
                <button
                  className="button secondary"
                  onClick={() => setDemoPhase("questionnaire")}
                >
                  Review questionnaire
                </button>
                <button className="button secondary" onClick={fresh}>
                  Start a new assessment
                </button>
                <Link className="text-link" href="/workspace">
                  Return to dashboard <ArrowRight size={16} />
                </Link>
              </div>
              <p className="micro">
                If symptoms affect daily life or concern you, consider
                discussing them with a qualified professional.
              </p>
              <p className="attribution micro">{gad.attribution}</p>
            </motion.div>
          )}
        </>
      )}
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      <p className="demo-memory micro">
        Temporary session · navigating within Still keeps answers; reloading or
        closing clears them. Starting a new demo or Cancel clears demo progress.
        No recording is saved or uploaded.
      </p>
    </div>
  );
}
