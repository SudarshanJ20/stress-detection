"use client";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { ArrowRight } from "lucide-react";
import { useStill } from "./state";
import { gad, scoreGad } from "@/lib/session";
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
      <p>{sub}</p>
    </div>
  );
}
export function Assessment({
  onComplete,
  onReview,
}: {
  onComplete?: () => void;
  onReview?: (review: boolean) => void;
}) {
  const { answers, setAnswers, current, setCurrent } = useStill();
  const [step, setStep] = useState(() => {
    const first = answers.findIndex((a) => a === null);
    return first < 0 ? 7 : first;
  });
  const [difficulty, setDifficulty] = useState(current.difficulty || "");
  const [error, setError] = useState("");
  useEffect(() => {
    onReview?.(step === 7);
  }, [step, onReview]);
  const question = useRef<HTMLFieldSetElement>(null);
  useEffect(() => {
    question.current?.focus();
  }, [step]);
  const routerPath = "/workspace/results";
  const complete = answers.every((x) => x !== null);
  function finish() {
    try {
      setCurrent({
        ...current,
        assessment_type: onComplete ? "combined" : "questionnaire_only",
        camera: null,
        recordingId: undefined,
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
      {!onComplete && (
        <Heading
          label="Questionnaire results · GAD-7"
          title="Make room for how you feel."
          sub="Take your time. Navigating within the app keeps your answers. Reloading or closing clears unsaved progress."
        />
      )}
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
          role="progressbar"
          aria-valuemin={0}
          aria-valuemax={7}
          aria-valuenow={answers.filter((x) => x !== null).length}
          aria-label={`${answers.filter((x) => x !== null).length} of 7 answered`}
        >
          {gad.questions.map((_, i) => (
            <span className={answers[i] !== null ? "filled" : ""} key={i} />
          ))}
        </div>
        <p className="timeframe">{gad.timeframe}</p>
        <div className="demo-step-content" key={step}>
          {step < 7 ? (
            <fieldset ref={question} tabIndex={-1}>
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
                How difficult have these problems made it for you to do your
                work, take care of things at home, or get along with other
                people?
                <select
                  value={difficulty}
                  onChange={(e) => {
                    setDifficulty(e.target.value);
                    setCurrent({ ...current, difficulty: e.target.value });
                  }}
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
        </div>
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
          ) : onComplete ? (
            <button
              className="button"
              disabled={!complete}
              onClick={() => {
                if (finish()) onComplete?.();
              }}
            >
              Continue to camera <ArrowRight size={16} />
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
        GAD-7 covers the last two weeks. Screening is not a diagnosis.
      </p>
    </>
  );
}
