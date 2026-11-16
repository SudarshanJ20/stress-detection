"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Check, RotateCcw, ShieldCheck } from "lucide-react";
import { Assessment } from "./questionnaire";
import VideoAnalysis from "./video-analysis";
import { Results } from "./results";
import { useStill } from "./state";
export default function GuidedAssessment() {
  const { current, setCurrent, newSession } = useStill();
  const [phase, setPhase] = useState<"questionnaire" | "camera" | "results">(
    "questionnaire",
  );
  const [review, setReview] = useState(false);
  const heading = useRef<HTMLHeadingElement>(null);
  const router = useRouter();
  const onReview = useCallback((value: boolean) => setReview(value), []);
  useEffect(() => {
    heading.current?.focus();
  }, [phase]);
  const step =
    phase === "questionnaire" ? (review ? 1 : 0) : phase === "camera" ? 2 : 3;
  return (
    <div className="guided-demo guided-real">
      <div className="local-source-banner">
        <ShieldCheck size={21} />
        <div>
          <strong>On this computer. By your choice.</strong>
          <span>
            Questionnaire screening and measured video observations, clearly
            separated.
          </span>
        </div>
      </div>
      <nav className="demo-steps no-print" aria-label="Assessment progress">
        <ol>
          {[
            "Questionnaire",
            "Review answers",
            "Video & local analysis",
            "Results",
          ].map((label, index) => (
            <li
              key={label}
              aria-current={step === index ? "step" : undefined}
              className={step >= index ? "is-reached" : ""}
            >
              <span>{step > index ? <Check size={14} /> : index + 1}</span>
              <small>{label}</small>
            </li>
          ))}
        </ol>
      </nav>
      {phase !== "results" && (
        <div className="page-heading">
          <p className="eyebrow">
            {phase === "questionnaire"
              ? "Anxiety screening — questionnaire"
              : "Video observations — webcam"}
          </p>
          <h1 ref={heading} tabIndex={-1}>
            {phase === "questionnaire"
              ? "A little space to reflect."
              : "Ready when you are."}
          </h1>
          <p>
            {phase === "questionnaire"
              ? "Answer seven questions about the last two weeks. Then review your answers and choose whether to add video observations."
              : "Record 35 seconds in good light. Review the recording before consenting to processing on this computer."}
          </p>
        </div>
      )}
      {phase === "questionnaire" && (
        <>
          <Assessment
            onReview={onReview}
            onComplete={() => setPhase("camera")}
          />
          <Link href="/workspace/assessment" className="text-link">
            Questionnaire only
          </Link>
        </>
      )}
      {phase === "camera" && (
        <VideoAnalysis
          onBack={() => setPhase("questionnaire")}
          onCancel={() => router.push("/workspace")}
          onQuestionnaire={() => {
            setCurrent({ ...current, camera: null, recordingId: undefined });
            setPhase("results");
          }}
          onComplete={(camera, recordingId) => {
            setCurrent({ ...current, mode: "genuine", camera, recordingId });
            setPhase("results");
          }}
        />
      )}
      {phase === "results" && (
        <>
          <Results />
          <div className="report-actions no-print">
            <button
              className="button secondary"
              onClick={() => setPhase("camera")}
            >
              <RotateCcw size={16} />
              Retry video
            </button>
            <button
              className="button secondary"
              onClick={() => setPhase("questionnaire")}
            >
              Review questionnaire
            </button>
            <button
              className="button secondary"
              onClick={() => {
                if (
                  window.confirm(
                    "Start a new assessment? Unsaved answers and observations will be cleared.",
                  )
                ) {
                  newSession();
                  setPhase("questionnaire");
                }
              }}
            >
              Start a new assessment
            </button>
            <Link href="/workspace" className="text-link">
              Return to dashboard
            </Link>
          </div>
        </>
      )}
      <p className="demo-memory micro">
        Temporary by default. Internal navigation keeps questionnaire answers;
        reloading or closing clears unsaved answers. Only an explicit save keeps
        a result in this browser. Saved recordings can be deleted in Settings.
      </p>
    </div>
  );
}
