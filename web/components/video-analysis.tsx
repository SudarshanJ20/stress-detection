"use client";
import { useEffect, useLayoutEffect, useRef, useState } from "react";
import dynamic from "next/dynamic";
import { Check, LoaderCircle, ShieldCheck, Upload, Video } from "lucide-react";
import { api, Camera } from "@/lib/session";
const Capture = dynamic(() => import("./camera-capture"), {
  ssr: false,
  loading: () => (
    <div className="skeleton" role="status">
      Preparing camera controls…
    </div>
  ),
});
const processingStages = [
  ["receiving_video", "Receiving video"],
  ["queued", "Waiting for local processing"],
  ["decoding", "Decoding video and timestamps"],
  ["tracking", "Tracking facial landmarks"],
  ["extracting_features", "Extracting geometric features"],
  ["finishing_analysis", "Finishing video analysis"],
  ["preparing_results", "Preparing results"],
] as const;
export default function VideoAnalysis({
  onComplete,
  onBack,
  onCancel,
  onQuestionnaire,
  combined = false,
  onStepChange,
}: {
  onComplete: (camera: Camera, recordingId?: string) => void;
  onBack: () => void;
  onCancel: () => void;
  onQuestionnaire?: () => void;
  combined?: boolean;
  onStepChange?: (step: "setup" | "recording" | "processing") => void;
}) {
  const [input, setInput] = useState<Blob | null>(null);
  const [source, setSource] = useState<"webcam" | "prerecorded">("webcam");
  const [preview, setPreview] = useState("");
  const [elapsed, setElapsed] = useState<number | null>(null);
  const [consent, setConsent] = useState(false);
  const [keep, setKeep] = useState(false);
  const [stage, setStage] = useState(combined ? "consent" : "capture");
  const [error, setError] = useState("");
  const [health, setHealth] = useState("checking");
  const active = useRef(false);
  const cancelling = useRef(false);
  const attempt = useRef(0);
  const mounted = useRef(false);
  const job = useRef<string | null>(null);
  const request = useRef<AbortController | null>(null);
  const poll = useRef<ReturnType<typeof setTimeout> | null>(null);
  const finished = useRef(false);
  const complete = useRef(onComplete);
  complete.current = onComplete;
  const check = () => {
    setHealth("checking");
    api("/health")
      .then((r) => {
        if (mounted.current) setHealth(r.model_available ? "ready" : "missing");
      })
      .catch(() => {
        if (mounted.current) setHealth("offline");
      });
  };
  function interrupt() {
    request.current?.abort();
    if (poll.current) clearTimeout(poll.current);
  }
  useLayoutEffect(() => {
    mounted.current = true;
    const stop = () => {
      attempt.current++;
      interrupt();
      if (job.current && !finished.current)
        void api("/jobs/" + job.current, {
          method: "DELETE",
          keepalive: true,
        }).catch(() => {});
    };
    window.addEventListener("pagehide", stop);
    return () => {
      mounted.current = false;
      stop();
      window.removeEventListener("pagehide", stop);
    };
  }, []);
  useEffect(() => {
    check();
  }, []);
  useEffect(() => {
    if (!input || combined) {
      setPreview("");
      return;
    }
    const url = URL.createObjectURL(input);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [input, combined]);
  function received(
    blob: Blob,
    duration: number | null,
    provenance: "webcam" | "prerecorded",
  ) {
    if (active.current) return;
    setInput(blob);
    setElapsed(duration);
    setSource(provenance);
    if (!combined) {
      setConsent(false);
      setKeep(false);
    }
    setError("");
    setStage("review");
  }
  async function removeJob() {
    if (!job.current) return;
    const id = job.current;
    await api("/jobs/" + id, { method: "DELETE" });
    if (job.current === id) job.current = null;
  }
  async function failure(message: string, expectedAttempt: number) {
    interrupt();
    setInput(null);
    try {
      await removeJob();
    } catch {
      message +=
        " Deletion could not be confirmed. Retry cleanup below or use Settings when the local service returns.";
    }
    if (mounted.current && attempt.current === expectedAttempt) {
      active.current = false;
      setStage("error");
      setError(message);
    }
  }
  async function analyze() {
    if (active.current || !input || !consent || health !== "ready") return;
    active.current = true;
    const epoch = ++attempt.current;
    finished.current = false;
    const id = crypto.randomUUID();
    job.current = id;
    const controller = new AbortController();
    request.current = controller;
    setError("");
    setStage("receiving_video");
    try {
      await api("/jobs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          request_id: id,
          provenance: source,
          keep_recording: keep,
          consent_local_processing: true,
        }),
        signal: controller.signal,
      });
      if (!mounted.current || controller.signal.aborted) return;
      await api("/jobs/" + id + "/video", {
        method: "PUT",
        headers: { "Content-Type": input.type.split(";")[0] || "video/webm" },
        body: input,
        signal: controller.signal,
      });
      if (!mounted.current || controller.signal.aborted) return;
      setInput(null);
      const watch = async () => {
        if (!mounted.current || controller.signal.aborted) return;
        try {
          const response = await api("/jobs/" + id, {
            signal: controller.signal,
          });
          if (!mounted.current || controller.signal.aborted) return;
          if (response.stage === "failed") {
            await failure(
              response.message ||
                "Video processing could not finish. Please retry.",
              epoch,
            );
            return;
          }
          if (response.stage === "completed" && response.result) {
            if (!response.recording_saved) await removeJob();
            if (
              !mounted.current ||
              controller.signal.aborted ||
              attempt.current !== epoch
            )
              return;
            finished.current = true;
            active.current = false;
            job.current = null;
            complete.current(
              response.result as Camera,
              response.recording_saved ? id : undefined,
            );
            return;
          }
          setStage(
            response.stage === "screening_pulse"
              ? "finishing_analysis"
              : response.stage,
          );
          poll.current = setTimeout(watch, 500);
        } catch (cause) {
          if (!controller.signal.aborted)
            await failure(
              cause instanceof Error
                ? cause.message
                : "The local connection was interrupted.",
              epoch,
            );
        }
      };
      void watch();
    } catch (cause) {
      if (!controller.signal.aborted)
        await failure(
          cause instanceof Error
            ? cause.message
            : "Video transfer could not finish.",
          epoch,
        );
    }
  }
  async function cancel(action?: () => void) {
    if (cancelling.current) return;
    cancelling.current = true;
    attempt.current++;
    interrupt();
    active.current = true;
    setInput(null);
    setStage("cancelling");
    try {
      await removeJob();
      if (!mounted.current) return;
      active.current = false;
      setStage(combined ? "consent" : "capture");
      setError("");
      setConsent(false);
      action?.();
    } catch {
      if (!mounted.current) return;
      active.current = false;
      setStage("error");
      setError(
        "Deletion could not be confirmed. Retry cleanup or open Settings when the local service is available.",
      );
    } finally {
      cancelling.current = false;
    }
  }
  useEffect(() => {
    if (
      combined &&
      stage === "review" &&
      input &&
      consent &&
      health === "ready"
    )
      void analyze();
  }, [combined, stage, input, consent, health]);
  useEffect(() => {
    if (stage !== "capture")
      onStepChange?.(
        stage === "consent" || stage === "error" ? "setup" : "processing",
      );
  }, [stage, onStepChange]);
  const processing = !["consent", "capture", "review", "error"].includes(stage);
  const index = processingStages.findIndex(([key]) => key === stage);
  return (
    <>
      {health !== "ready" && (
        <div className="notice" role="status">
          {health === "checking"
            ? "Checking local processing…"
            : health === "missing"
              ? "Local video measurements are unavailable. Questionnaire screening still works."
              : "Local Python service unavailable. Questionnaire screening still works."}{" "}
          <button className="text-link" onClick={check}>
            Check again
          </button>
        </div>
      )}
      {stage === "consent" && (
        <section className="card capture-consent">
          <p className="eyebrow">CAMERA CONSENT & SETUP</p>
          <h2>A short recording. Local processing.</h2>
          <p>
            The combined assessment includes a 35-second video. After capture,
            it is sent to the local Python service on this computer to measure
            tracking coverage, facial opening ratios and landmark motion. Your
            microphone stays off and questionnaire answers are not sent.
          </p>
          <label className="check">
            <input
              type="checkbox"
              checked={consent}
              onChange={(event) => setConsent(event.target.checked)}
            />
            I consent to processing this video locally on this computer.
          </label>
          <label className="check">
            <input
              type="checkbox"
              checked={keep}
              onChange={(event) => setKeep(event.target.checked)}
            />
            Keep the recording on this computer until I delete it in Settings
            (optional).
          </label>
          <p className="micro">
            Temporary video and measurement files are deleted after processing,
            cancellation or failure. Only a recording you explicitly choose to
            keep is retained after successful processing. You can cancel or
            leave at any time.
          </p>
          <div className="report-actions">
            <button
              className="button"
              disabled={!consent || health !== "ready"}
              onClick={() => setStage("capture")}
            >
              Continue to camera
            </button>
            <button className="button secondary" onClick={onBack}>
              Back to review
            </button>
            <button className="text-link" onClick={onCancel}>
              Leave assessment
            </button>
          </div>
        </section>
      )}
      {stage === "capture" && (
        <Capture
          onRecording={(blob, duration) => received(blob, duration, "webcam")}
          onBack={onBack}
          onCancel={onCancel}
          onQuestionnaire={combined ? undefined : onQuestionnaire}
          onStatus={onStepChange}
        />
      )}
      {stage === "review" && combined && (
        <div className="skeleton" role="status">
          Recording complete. Preparing local processing…
        </div>
      )}
      {stage === "review" && !combined && (
        <section className="card capture-review">
          <div className="row between">
            <p className="eyebrow">VIDEO ANALYSIS</p>
            <span className="pill">
              {source === "prerecorded"
                ? "Prerecorded input — not live"
                : `Recorded · ${elapsed?.toFixed(2)} seconds`}
            </span>
          </div>
          <h2>A clear view. Your choice to process.</h2>
          {preview && (
            <video
              src={preview}
              controls
              playsInline
              aria-label="Your recorded video preview"
            />
          )}
          <p>
            Send this video to the Python service on this computer. Its decoded
            timestamps determine whether a complete 30-second interval is
            available.
          </p>
          <label className="check">
            <input
              type="checkbox"
              checked={consent}
              onChange={(e) => setConsent(e.target.checked)}
            />
            I consent to processing this video locally on this computer.
          </label>
          <label className="check">
            <input
              type="checkbox"
              checked={keep}
              onChange={(e) => setKeep(e.target.checked)}
            />
            Keep the recording on this computer until I delete it in Settings
            (optional).
          </label>
          <p className="micro">
            <ShieldCheck size={14} />
            Temporary video and measurement files are deleted after processing,
            cancellation or failure. Only an explicitly retained recording
            remains. Questionnaire answers are not sent.
          </p>
          <div className="report-actions">
            <button
              className="button"
              disabled={!consent || health !== "ready"}
              onClick={() => void analyze()}
            >
              Analyze on this computer
            </button>
            <button className="button secondary" onClick={() => void cancel()}>
              Retry video
            </button>
            <button className="text-link" onClick={() => void cancel(onCancel)}>
              Cancel assessment
            </button>
          </div>
        </section>
      )}
      {processing && (
        <section className="card local-processing" aria-live="polite">
          <LoaderCircle className="spin" size={28} />
          <p className="eyebrow">LOCAL VIDEO PROCESSING</p>
          <h2>
            {stage === "cancelling"
              ? "Cancelling and removing video…"
              : processingStages[index]?.[1] || "Processing locally…"}
          </h2>
          <p>The video stays on this computer. You can cancel at any time.</p>
          <ol>
            {processingStages.map(([key, label], i) => (
              <li
                key={key}
                aria-current={stage === key ? "step" : undefined}
                className={index > i ? "done" : ""}
              >
                {index > i ? (
                  <Check size={15} />
                ) : (
                  <span className="processing-marker" />
                )}
                {label}
              </li>
            ))}
          </ol>
          <button
            className="button secondary"
            disabled={stage === "cancelling"}
            onClick={() => void cancel()}
          >
            Cancel local analysis
          </button>
        </section>
      )}
      {stage === "error" && (
        <section className="card">
          <h2>Let’s try again.</h2>
          <button className="button" onClick={() => void cancel()}>
            {job.current ? "Retry cleanup" : "Retry video"}
          </button>
          {combined ? (
            <button className="text-link" onClick={() => void cancel(onCancel)}>
              Leave assessment
            </button>
          ) : (
            onQuestionnaire && (
              <button
                className="text-link"
                onClick={() => void cancel(onQuestionnaire)}
              >
                Open questionnaire-only results
              </button>
            )
          )}
        </section>
      )}
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      {stage === "capture" && !combined && (
        <details className="card fallback">
          <summary>
            <Upload size={16} />
            Use a clearly labeled prerecorded input
          </summary>
          <p>
            Choose a consented local WebM, MP4 or MOV file, up to 100 MiB and
            four minutes. It will be labeled prerecorded in results and reports.
            Nothing is uploaded until you consent and choose Analyze.
          </p>
          <input
            aria-label="Prerecorded video"
            type="file"
            accept="video/webm,video/mp4,video/quicktime"
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (!file) return;
              if (file.size > 100 * 1024 * 1024) {
                setError("Choose a video smaller than 100 MiB.");
                return;
              }
              received(file, null, "prerecorded");
            }}
          />
        </details>
      )}
      {!processing && stage !== "capture" && stage !== "consent" && (
        <button className="text-link" onClick={() => void cancel(onBack)}>
          Back to review
        </button>
      )}
      <p className="micro">
        <Video size={14} />
        Closing or leaving stops capture and requests removal of unfinished
        local jobs. If a connection is interrupted, deletion may need to be
        retried in Settings; temporary jobs expire within 30 minutes.
      </p>
    </>
  );
}
