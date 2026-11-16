"use client";
import Link from "next/link";
import { useState } from "react";
import {
  ArrowRight,
  ArrowUpRight,
  Check,
  Download,
  Printer,
} from "lucide-react";
import { useStill } from "./state";
import { Heading, Empty } from "./screen-frames";
import { gad, report, download } from "@/lib/session";
import { Observations } from "./observations";
export function Results({ printed = false }: { printed?: boolean }) {
  const { current, setCurrent, save, storageError } = useStill();
  const [saved, setSaved] = useState(false);
  if (current.mode === "demo")
    return (
      <Empty title="No assessment result available.">
        <p>Start a new assessment to create your results.</p>
        <Link className="button" href="/workspace/guided">
          Start assessment
        </Link>
      </Empty>
    );
  if (
    current.assessment_type === "combined" &&
    (!current.screening || !current.camera)
  )
    return (
      <>
        <Heading
          label="ASSESSMENT IN PROGRESS"
          title="Your next step is ready."
        />
        <Empty title="Complete the recording and local processing.">
          <p>
            The combined assessment includes questionnaire results and video
            analysis.
          </p>
          <Link className="button" href="/workspace/guided">
            Resume assessment
          </Link>
        </Empty>
      </>
    );
  const anything = !!(current.screening || current.camera);
  if (!anything)
    return (
      <>
        <Heading label="YOUR RESULTS" title="Your perspective starts here." />
        <Empty title="No result to show yet.">
          <p>Complete an assessment or open a session you saved in History.</p>
          <Link className="button" href="/workspace/guided">
            Start assessment <ArrowRight size={16} />
          </Link>
        </Empty>
      </>
    );
  return (
    <>
      <Heading
        focus
        label={
          printed ? "SESSION REPORT" : "YOUR RESULTS / TWO SEPARATE SOURCES"
        }
        title={printed ? "A moment, on paper." : "A clearer perspective."}
        sub={new Date(current.date).toLocaleString()}
      />
      {current.screening ? (
        <section className="card screening-result">
          <div>
            <h2 className="eyebrow">Questionnaire results</h2>
            <h3 className="questionnaire-category">
              {current.screening.category}
              <br />
              <em>reported symptoms.</em>
            </h3>
            <p>
              GAD-7 · Based on your answers about the last two weeks.
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
            discussing them with a qualified professional.
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
        <h2>Video analysis</h2>
        {!printed && (
          <Link className="text-link" href="/workspace/camera">
            {current.camera
              ? "Record a new observation"
              : "Start a video session"}{" "}
            <ArrowUpRight size={16} />
          </Link>
        )}
      </div>
      <Observations camera={current.camera} />

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
