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
  const [videoStep, setVideoStep] = useState<
    "setup" | "recording" | "processing"
  >("setup");
  const [review, setReview] = useState(false);
  const heading = useRef<HTMLHeadingElement>(null);
  const router = useRouter();
  const onReview = useCallback((value: boolean) => setReview(value), []);
  useEffect(() => {
    heading.current?.focus();
  }, [phase]);
  const step =
    phase === "questionnaire"
      ? review
        ? 1
        : 0
      : phase === "camera"
        ? { setup: 2, recording: 3, processing: 4 }[videoStep]
        : 5;
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
            "Camera setup",
            "35-second recording",
            "Processing",
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
              ? "Questionnaire · GAD-7"
              : "Video analysis"}
          </p>
          <h1 ref={heading} tabIndex={-1}>
            {phase === "questionnaire"
              ? "A little space to reflect."
              : videoStep === "recording"
                ? "A moment, in frame."
                : videoStep === "processing"
                  ? "Preparing your results."
                  : "Ready when you are."}
          </h1>
          <p>
            {phase === "questionnaire"
              ? "Answer the questionnaire, record a short video, and review your screening results and video observations."
              : videoStep === "recording"
                ? "Keep your face in the frame until the recording ends."
                : videoStep === "processing"
                  ? "Your video is being processed on this computer."
                  : "Consent to local processing, set up your camera and record 35 seconds in good light."}
          </p>
        </div>
      )}
      {phase === "questionnaire" && (
        <>
          <Assessment
            onReview={onReview}
            onComplete={() => {
              setVideoStep("setup");
              setPhase("camera");
            }}
          />
        </>
      )}
      {phase === "camera" && (
        <VideoAnalysis
          combined
          onStepChange={setVideoStep}
          onBack={() => setPhase("questionnaire")}
          onCancel={() => router.push("/workspace")}
          onComplete={(camera, recordingId) => {
            setCurrent({
              ...current,
              mode: "genuine",
              assessment_type: "combined",
              camera,
              recordingId,
            });
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
              onClick={() => {
                setCurrent({
                  ...current,
                  assessment_type: "combined",
                  camera: null,
                  recordingId: undefined,
                });
                setVideoStep("setup");
                setPhase("camera");
              }}
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
