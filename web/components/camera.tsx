"use client";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Camera as CameraIcon,
  Video,
  Square,
  Upload,
  ArrowRight,
  Sun,
  ScanFace,
  LockKeyhole,
  LoaderCircle,
  Download,
} from "lucide-react";
import { api, Camera } from "@/lib/session";
import { useStill } from "./state";
const labels: Record<string, string> = {
  receiving_video: "Transferring to your local Python service",
  queued: "Queued for local analysis",
  checking_video: "Checking decoded video and timing",
  extracting_face: "Extracting faces and tracking quality",
  screening_pulse: "Screening Green and POS pulse estimates",
  summarizing: "Preparing supported observations",
};
export default function CameraSession() {
  const { current, setCurrent } = useStill();
  const router = useRouter();
  const [stage, setStage] = useState("idle");
  const [seconds, setSeconds] = useState(0);
  const [error, setError] = useState("");
  const [blob, setBlob] = useState<Blob | null>(null);
  const [preview, setPreview] = useState("");
  const [source, setSource] = useState<"webcam" | "prerecorded">("webcam");
  const [keep, setKeep] = useState(false);
  const [health, setHealth] = useState<
    "checking" | "ready" | "offline" | "missing"
  >("checking");
  const video = useRef<HTMLVideoElement>(null);
  const stream = useRef<MediaStream | null>(null);
  const recorder = useRef<MediaRecorder | null>(null);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);
  const poll = useRef<ReturnType<typeof setTimeout> | null>(null);
  const controller = useRef<AbortController | null>(null);
  const job = useRef<string | null>(null);
  const finished = useRef(false);
  const active = useRef(false);
  const alive = useRef(true);
  const check = () => {
    setHealth("checking");
    api("/health")
      .then((r) => {
        if (alive.current) setHealth(r.model_available ? "ready" : "missing");
      })
      .catch(() => {
        if (alive.current) setHealth("offline");
      });
  };
  const stopTracks = () => {
    stream.current?.getTracks().forEach((t) => t.stop());
    stream.current = null;
    if (timer.current) clearInterval(timer.current);
  };
  useEffect(() => {
    alive.current = true;
    check();
    const onPageHide = () => {
      alive.current = false;
      stopTracks();
      controller.current?.abort();
      if (job.current && !finished.current)
        void api("/jobs/" + job.current, {
          method: "DELETE",
          keepalive: true,
        }).catch(() => {});
    };
    window.addEventListener("pagehide", onPageHide);
    return () => {
      window.removeEventListener("pagehide", onPageHide);
      alive.current = false;
      if (recorder.current?.state === "recording") recorder.current.stop();
      stopTracks();
      if (poll.current) clearTimeout(poll.current);
      controller.current?.abort();
      if (job.current && !finished.current)
        void api("/jobs/" + job.current, {
          method: "DELETE",
          keepalive: true,
        }).catch(() => {});
    };
  }, []);
  useEffect(
    () => () => {
      if (preview) URL.revokeObjectURL(preview);
    },
    [preview],
  );
  const stop = () => {
    if (recorder.current?.state === "recording") recorder.current.stop();
    stopTracks();
  };
  async function start() {
    if (active.current) return;
    active.current = true;
    setError("");
    setBlob(null);
    setPreview("");
    setSeconds(0);
    setStage("requesting");
    setSource("webcam");
    try {
      if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder)
        throw Error(
          "This browser cannot record video. Use a supported browser on localhost or choose a prerecorded file.",
        );
      const s = await navigator.mediaDevices.getUserMedia({
        audio: false,
        video: {
          facingMode: "user",
          width: { ideal: 1280 },
          height: { ideal: 720 },
          frameRate: { ideal: 30 },
        },
      });
      if (!alive.current) {
        s.getTracks().forEach((t) => t.stop());
        return;
      }
      stream.current = s;
      if (video.current) {
        video.current.srcObject = s;
        await video.current.play();
      }
      const mime = [
        "video/webm;codecs=vp8",
        "video/webm;codecs=vp9",
        "video/mp4",
      ].find((x) => MediaRecorder.isTypeSupported(x));
      const r = new MediaRecorder(
        s,
        mime ? { mimeType: mime, videoBitsPerSecond: 1800000 } : undefined,
      );
      recorder.current = r;
      const parts: BlobPart[] = [];
      r.ondataavailable = (e) => {
        if (e.data.size) parts.push(e.data);
      };
      r.onerror = () => {
        stopTracks();
        if (alive.current) {
          setError("Recording was interrupted. Please try again.");
          setStage("idle");
        }
      };
      r.onstop = () => {
        stopTracks();
        if (alive.current) {
          const b = new Blob(parts, { type: r.mimeType });
          setBlob(b);
          setPreview(URL.createObjectURL(b));
          setStage("ready");
        }
      };
      r.start(500);
      setStage("recording");
      const began = performance.now();
      timer.current = setInterval(() => {
        const t = (performance.now() - began) / 1000;
        setSeconds(Math.floor(t));
        if (t >= 35) stop();
      }, 200);
    } catch (e) {
      stopTracks();
      setStage("idle");
      setError(
        e instanceof DOMException && e.name === "NotAllowedError"
          ? "Camera permission was denied. You can retry in browser settings, use a prerecorded file, or continue without the camera."
          : e instanceof Error
            ? e.message
            : "Camera could not start.",
      );
    } finally {
      active.current = false;
    }
  }
  async function analyze() {
    if (!blob || active.current) return;
    active.current = true;
    finished.current = false;
    controller.current = new AbortController();
    setError("");
    setStage("receiving_video");
    try {
      const created = await api("/jobs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          request_id: crypto.randomUUID(),
          provenance: source,
          keep_recording: keep,
        }),
        signal: controller.current.signal,
      });
      job.current = created.id;
      await api("/jobs/" + created.id + "/video", {
        method: "PUT",
        headers: { "Content-Type": blob.type.split(";")[0] || "video/webm" },
        body: blob,
        signal: controller.current.signal,
      });
      const watch = async () => {
        try {
          const r = await api("/jobs/" + created.id, {
            signal: controller.current?.signal,
          });
          if (!alive.current) return;
          if (r.stage === "failed") {
            setError(r.message);
            setStage("ready");
            active.current = false;
            return;
          }
          if (r.stage === "completed" && r.result) {
            finished.current = true;
            setCurrent({
              ...current,
              camera: r.result as Camera,
              recordingId: r.recording_saved ? created.id : undefined,
            });
            active.current = false;
            router.push("/workspace/results");
            return;
          }
          setStage(r.stage);
          poll.current = setTimeout(watch, 1200);
        } catch (e) {
          if (alive.current) {
            setError(
              e instanceof Error
                ? e.message
                : "Analysis connection was interrupted.",
            );
            setStage("ready");
            active.current = false;
          }
        }
      };
      void watch();
    } catch (e) {
      if (job.current)
        void api("/jobs/" + job.current, { method: "DELETE" }).catch(() => {});
      if (alive.current) {
        setError(e instanceof Error ? e.message : "Analysis could not start.");
        setStage("ready");
        active.current = false;
      }
    }
  }
  async function cancel() {
    controller.current?.abort();
    if (poll.current) clearTimeout(poll.current);
    stop();
    if (job.current) {
      try {
        await api("/jobs/" + job.current, { method: "DELETE" });
        job.current = null;
      } catch {
        setError(
          "Connection lost. Deletion could not be confirmed; use Settings when the service is available.",
        );
      }
    }
    active.current = false;
    setStage(blob ? "ready" : "idle");
  }
  const busy = !["idle", "ready", "requesting", "recording"].includes(stage);
  return (
    <>
      {stage === "recording" && (
        <div className="recording-dock" aria-label="Camera recording controls">
          <span className="record-dot" />
          <span role="timer">Recording · {seconds}s / 35s</span>
          <button className="button" onClick={stop}>
            <Square size={15} />
            Stop camera
          </button>
        </div>
      )}
      <div className="page-heading">
        <p className="eyebrow">OPTIONAL / CAMERA OBSERVATIONS</p>
        <h1>
          A moment
          <br />
          <em>to observe.</em>
        </h1>
        <p>
          35 seconds, at your own pace. No anxiety model. No live estimates.
        </p>
      </div>
      {health !== "ready" && (
        <div className="notice" role="status">
          {health === "checking"
            ? "Checking local analysis service…"
            : health === "missing"
              ? "The local landmark model is missing. See setup instructions."
              : "Local Python service unavailable. Questionnaire screening still works."}
          <button className="text-link" onClick={check}>
            Check again
          </button>
        </div>
      )}
      <div className="camera-grid">
        <section className="camera-card">
          <div className="camera-view">
            {preview ? (
              <video
                src={preview}
                controls
                playsInline
                aria-label="Your recorded video preview"
              />
            ) : (
              <video
                ref={video}
                autoPlay
                muted
                playsInline
                aria-label="Live camera preview"
              />
            )}
            {["idle", "requesting"].includes(stage) && (
              <div className="camera-empty">
                <Video size={40} />
                <h3>Your camera is off.</h3>
                <p>Only you can turn it on.</p>
              </div>
            )}
            {stage === "recording" && (
              <div className="capture-label">
                <span className="record-dot" /> Camera recording · {seconds}s /
                35s
              </div>
            )}
            {source === "prerecorded" && preview && (
              <span className="capture-label">
                Prerecorded input — not a live measurement
              </span>
            )}
          </div>
          <div className="camera-controls">
            {stage === "recording" ? (
              <button className="button danger" onClick={stop}>
                <Square size={16} /> Stop recording · {seconds}s
              </button>
            ) : (
              <button
                className="button"
                disabled={busy || stage === "requesting"}
                onClick={start}
              >
                <CameraIcon size={17} />
                {stage === "requesting"
                  ? "Waiting for camera permission…"
                  : blob
                    ? "Record again"
                    : "Start camera"}
              </button>
            )}
            {busy && (
              <button
                className="button secondary"
                onClick={() => void cancel()}
              >
                Cancel local analysis
              </button>
            )}
          </div>
        </section>
        <aside>
          <article className="card">
            <p className="eyebrow">A LITTLE PREPARATION</p>
            <h3>
              Give the camera
              <br />a clear view.
            </h3>
            <p>
              <Sun size={17} /> Face a soft, even light.
            </p>
            <p>
              <ScanFace size={17} /> Keep one face fully in frame.
            </p>
            <p>
              <Video size={17} /> Stay comfortably still; avoid talking.
            </p>
            <p className="micro">
              The pipeline needs a full 30-second interval, plus boundary
              support. A shorter clip returns unavailable pulse estimates.
              Movement, multiple faces and tracking loss can prevent readings.
            </p>
          </article>
          <div className="notice">
            <LockKeyhole size={17} /> Nothing is sent until you choose Analyze.
            Processing uses your local Python service.
          </div>
        </aside>
      </div>
      {busy && (
        <div className="card processing" role="status" aria-live="polite">
          <LoaderCircle className="spin" />
          <div>
            <h3>{labels[stage] ?? "Analyzing locally"}</h3>
            <p>
              Real processing stages, with no arbitrary progress percentage.
            </p>
          </div>
        </div>
      )}
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      {blob && !busy && (
        <section className="card">
          <div className="row between">
            <div>
              <h3>
                {source === "prerecorded"
                  ? "Prerecorded input ready"
                  : "Recording ready"}
              </h3>
              <p>
                Video is in browser memory. Analysis sends it only to this
                computer.
              </p>
            </div>
            <button
              className="button"
              disabled={health !== "ready"}
              onClick={() => void analyze()}
            >
              Analyze on this computer <ArrowRight size={16} />
            </button>
          </div>
          <label className="check">
            <input
              type="checkbox"
              checked={keep}
              onChange={(e) => setKeep(e.target.checked)}
            />{" "}
            Keep the recording on the local server until I delete it (optional)
          </label>
          <button
            className="text-link"
            onClick={() => {
              const a = document.createElement("a");
              a.href = preview;
              a.download =
                "still-recording." +
                (blob.type.includes("mp4") ? "mp4" : "webm");
              a.click();
            }}
          >
            <Download size={16} /> Download recording
          </button>
          <button
            className="text-link"
            onClick={() => {
              setBlob(null);
              setPreview("");
              setStage("idle");
            }}
          >
            Discard browser recording
          </button>
        </section>
      )}
      <details className="card fallback">
        <summary>
          <Upload size={16} /> Use a clearly labeled prerecorded input
        </summary>
        <p>
          Choose a consented local video (WebM, MP4 or MOV, up to 100 MiB and
          four minutes). The report preserves its prerecorded source. No dataset
          video is bundled with this app.
        </p>
        <input
          aria-label="Prerecorded video"
          type="file"
          accept="video/webm,video/mp4,video/quicktime"
          disabled={busy || stage === "recording"}
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (!file) return;
            if (file.size > 100 * 1024 * 1024) {
              setError("Choose a recording smaller than 100 MiB.");
              return;
            }
            stopTracks();
            setBlob(file);
            setPreview(URL.createObjectURL(file));
            setSource("prerecorded");
            setStage("ready");
            setError("");
          }}
        />
      </details>
      <button
        className="text-link"
        onClick={() => router.push("/workspace/results")}
      >
        Continue without camera observations <ArrowRight size={15} />
      </button>
    </>
  );
}
