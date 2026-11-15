"use client";
import { useLayoutEffect, useRef, useState } from "react";
import {
  Camera,
  Video,
  Square,
  Sun,
  UserRound,
  ShieldCheck,
} from "lucide-react";
const DURATION_MS = 35_000;
type Stage =
  "idle" | "requesting" | "ready" | "preparing" | "recording" | "incomplete";
export default function DemoCamera({
  onComplete,
  onBack,
  onCancel,
  onQuestionnaire,
}: {
  onComplete: (duration: number) => void;
  onBack: () => void;
  onCancel: () => void;
  onQuestionnaire: () => void;
}) {
  const [stage, setStage] = useState<Stage>("idle");
  const [error, setError] = useState("");
  const [elapsed, setElapsed] = useState(0);
  const [countdown, setCountdown] = useState(3);
  const [prepare, setPrepare] = useState(true);
  const video = useRef<HTMLVideoElement>(null);
  const stream = useRef<MediaStream | null>(null);
  const recorder = useRef<MediaRecorder | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const mounted = useRef(false);
  const busy = useRef(false);
  const generation = useRef(0);
  const started = useRef(0);
  const recording = useRef(false);
  const finishRef = useRef(onComplete);
  finishRef.current = onComplete;
  const clearTimer = () => {
    if (timer.current) clearTimeout(timer.current);
    timer.current = null;
  };
  const release = () => {
    clearTimer();
    recording.current = false;
    if (recorder.current) {
      recorder.current.onstop = null;
      recorder.current.ondataavailable = null;
      recorder.current.onerror = null;
      if (recorder.current.state !== "inactive") recorder.current.stop();
      recorder.current = null;
    }
    stream.current?.getTracks().forEach((t) => {
      t.onended = null;
      t.stop();
    });
    stream.current = null;
    if (video.current) video.current.srcObject = null;
  };
  const discard = () => {
    generation.current++;
    release();
    busy.current = false;
  };
  useLayoutEffect(() => {
    mounted.current = true;
    const hide = () => {
      discard();
      setStage("idle");
    };
    const visibility = () => {
      if (document.hidden && busy.current) {
        discard();
        setStage("incomplete");
        setError(
          "Capture was interrupted while this tab was hidden. Please retry the complete 35 seconds.",
        );
      }
    };
    window.addEventListener("pagehide", hide);
    document.addEventListener("visibilitychange", visibility);
    return () => {
      mounted.current = false;
      discard();
      window.removeEventListener("pagehide", hide);
      document.removeEventListener("visibilitychange", visibility);
    };
  }, []);
  async function requestCamera() {
    if (busy.current) return;
    discard();
    busy.current = true;
    const attempt = generation.current;
    setError("");
    setElapsed(0);
    setStage("requesting");
    try {
      if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder)
        throw new Error(
          "Video recording is unavailable in this browser. Try a supported browser on localhost, or use questionnaire only.",
        );
      const media = await navigator.mediaDevices.getUserMedia({
        audio: false,
        video: {
          facingMode: "user",
          width: { ideal: 1280 },
          height: { ideal: 720 },
          frameRate: { ideal: 30 },
        },
      });
      if (!mounted.current || attempt !== generation.current) {
        media.getTracks().forEach((t) => t.stop());
        return;
      }
      stream.current = media;
      media.getVideoTracks().forEach((t) => {
        t.onended = () => {
          discard();
          setStage("incomplete");
          setError(
            "The camera disconnected. Reconnect it and retry the recording.",
          );
        };
      });
      if (!video.current)
        throw new Error("The preview could not open. Please try again.");
      video.current.srcObject = media;
      await video.current.play();
      if (!mounted.current || attempt !== generation.current) return;
      setStage("ready");
    } catch (cause) {
      if (!mounted.current || attempt !== generation.current) return;
      release();
      setStage("idle");
      const name = cause instanceof DOMException ? cause.name : "";
      setError(
        name === "NotAllowedError"
          ? "Camera permission was denied. Allow camera access in browser settings and retry, or choose questionnaire only."
          : name === "NotFoundError"
            ? "No camera was found. Connect a camera and retry, or choose questionnaire only."
            : name === "NotReadableError"
              ? "The camera is busy or unavailable. Close other camera apps and retry, or choose questionnaire only."
              : cause instanceof Error
                ? cause.message
                : "The camera could not start. Please retry or choose questionnaire only.",
      );
    } finally {
      if (attempt === generation.current) busy.current = false;
    }
  }
  function stopCapture() {
    if (!recording.current || !recorder.current) return;
    const duration = (performance.now() - started.current) / 1000;
    recording.current = false;
    clearTimer();
    setElapsed(duration);
    const r = recorder.current;
    // Do not pass delayed/background capture off as a completed exact-length interaction.
    const complete = duration >= 35 && duration < 35.5 && !document.hidden;
    r.onstop = () => {
      release();
      busy.current = false;
      if (!mounted.current) return;
      if (complete) finishRef.current(duration);
      else {
        setStage("incomplete");
        setError(
          duration < 35
            ? `Incomplete recording — ${duration.toFixed(1)} of 35 seconds. Retry to complete the demo.`
            : "Browser timing was interrupted. Retry to capture an uninterrupted 35-second session.",
        );
      }
    };
    if (r.state !== "inactive") r.stop();
    else {
      release();
      busy.current = false;
      setStage("incomplete");
      setError("Recording stopped unexpectedly. Please retry.");
    }
    stream.current?.getTracks().forEach((t) => {
      t.onended = null;
      t.stop();
    });
  }
  function beginRecording() {
    try {
      if (!stream.current?.active)
        throw new Error("Camera is no longer ready. Please enable it again.");
      const mime = [
        "video/webm;codecs=vp8",
        "video/webm;codecs=vp9",
        "video/mp4",
      ].find((type) => MediaRecorder.isTypeSupported(type));
      const r = new MediaRecorder(
        stream.current,
        mime ? { mimeType: mime } : undefined,
      );
      recorder.current = r;
      // Capture chunks are deliberately discarded. No Blob, replay URL, upload or file is created.
      r.ondataavailable = () => {};
      r.onerror = () => {
        discard();
        setStage("incomplete");
        setError("Recording failed. No result was generated. Please retry.");
      };
      r.start(250);
      started.current = performance.now();
      recording.current = true;
      setStage("recording");
      setElapsed(0);
      const tick = () => {
        const now = performance.now() - started.current;
        setElapsed(now / 1000);
        if (now >= DURATION_MS) stopCapture();
        else timer.current = setTimeout(tick, Math.min(100, DURATION_MS - now));
      };
      timer.current = setTimeout(tick, 100);
    } catch (cause) {
      discard();
      setStage("incomplete");
      setError(
        cause instanceof Error
          ? cause.message
          : "Recording could not start. Please retry.",
      );
    }
  }
  function startRecording() {
    if (busy.current || stage !== "ready") return;
    busy.current = true;
    setError("");
    if (!prepare) {
      beginRecording();
      return;
    }
    setStage("preparing");
    setCountdown(3);
    const began = performance.now();
    const tick = () => {
      const remaining = 3000 - (performance.now() - began);
      if (remaining <= 0) beginRecording();
      else {
        setCountdown(Math.ceil(remaining / 1000));
        timer.current = setTimeout(tick, Math.min(100, remaining));
      }
    };
    timer.current = setTimeout(tick, 100);
  }
  const leave = (action: () => void) => {
    discard();
    setStage("idle");
    action();
  };
  const active = stage === "recording" || stage === "preparing";
  return (
    <>
      <div className="demo-camera-grid">
        <section className="card demo-camera-card">
          <div className="row between">
            <span className="eyebrow">CAMERA SETUP</span>
            <span className="pill" role="status" aria-live="polite">
              {stage === "ready"
                ? "Camera ready"
                : stage === "recording"
                  ? "Recording"
                  : stage === "preparing"
                    ? "Get ready"
                    : "Camera off"}
            </span>
          </div>
          <div className="demo-viewfinder">
            <video
              ref={video}
              autoPlay
              muted
              playsInline
              aria-label="Your camera preview"
            />
            {!stream.current && (
              <div className="demo-camera-placeholder">
                <Camera size={40} />
                <h2>A moment, in frame.</h2>
                <p>Your preview appears after you enable the camera.</p>
              </div>
            )}
            {stage === "ready" && (
              <div className="demo-frame" aria-hidden="true" />
            )}
            {stage === "preparing" && (
              <div className="demo-countdown" role="status" aria-live="polite">
                {countdown}
                <small>Preparation · not recording yet</small>
              </div>
            )}
            {stage === "recording" && (
              <div className="demo-capture-status">
                <span className="status-dot" /> Recording ·{" "}
                {Math.max(0, 35 - elapsed).toFixed(1)}s remaining
              </div>
            )}
          </div>
          <div
            className="demo-timer"
            role="progressbar"
            aria-label="Recording elapsed seconds"
            aria-valuemin={0}
            aria-valuemax={35}
            aria-valuenow={Math.min(35, Math.floor(elapsed))}
          >
            <span
              style={{ width: `${Math.min(100, (elapsed / 35) * 100)}%` }}
            />
          </div>
          <p className="micro">
            {stage === "ready"
              ? "Preview ready. Face detection is not active in this demo."
              : "No live face detection, pulse measurement or anxiety inference in this demo."}
          </p>
          {stage === "ready" && (
            <label className="check">
              <input
                type="checkbox"
                checked={prepare}
                onChange={(e) => setPrepare(e.target.checked)}
              />
              3-second preparation countdown
            </label>
          )}
          <div className="report-actions">
            {(stage === "idle" || stage === "incomplete") && (
              <button className="button" onClick={() => void requestCamera()}>
                <Camera size={16} />
                {stage === "incomplete" ? "Retry camera" : "Enable camera"}
              </button>
            )}
            {stage === "requesting" && (
              <button className="button" disabled>
                Requesting permission…
              </button>
            )}
            {stage === "ready" && (
              <button className="button" onClick={startRecording}>
                <Video size={16} />
                Start recording
              </button>
            )}
            {stage === "recording" && (
              <button className="button" onClick={stopCapture}>
                <Square size={16} />
                Stop recording
              </button>
            )}
            {stage === "preparing" && (
              <button
                className="button secondary"
                onClick={() => {
                  discard();
                  setStage("idle");
                }}
              >
                Cancel countdown
              </button>
            )}
            <button className="button secondary" onClick={() => leave(onBack)}>
              Back to review
            </button>
            <button className="text-link" onClick={() => leave(onCancel)}>
              Cancel demo
            </button>
          </div>
          {error && (
            <p role="alert" className="error">
              {error}
            </p>
          )}
          {!active && (
            <button
              className="text-link"
              onClick={() => leave(onQuestionnaire)}
            >
              Continue with questionnaire only
            </button>
          )}
        </section>
        <aside className="demo-guidance">
          <div className="card pale">
            <Sun size={24} />
            <h3>Find soft, even light.</h3>
            <p>Face a window or lamp. Avoid a bright light behind you.</p>
            <UserRound size={24} />
            <h3>Settle into the frame.</h3>
            <p>
              Place the camera at eye level and sit comfortably. The frame is a
              positioning guide, not a face detector.
            </p>
          </div>
          <div className="card">
            <ShieldCheck size={24} />
            <h3>Only on this device.</h3>
            <p>
              Video only. No microphone. This demo does not upload your
              recording to Python or any other service. Capture data is
              discarded immediately.
            </p>
            <p className="micro">
              A full 35 seconds completes the interaction. Stopping early means
              retrying. Leaving this page stops the camera; your questionnaire
              answers remain in memory.
            </p>
          </div>
        </aside>
      </div>
      {stage === "recording" && (
        <div className="recording-dock">
          <span>
            Recording · {Math.max(0, 35 - elapsed).toFixed(1)}s remaining
          </span>
          <button className="button" onClick={stopCapture}>
            <Square size={14} />
            Stop
          </button>
        </div>
      )}
    </>
  );
}
