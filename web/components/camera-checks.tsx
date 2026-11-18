"use client";
import { RefObject, useEffect, useState } from "react";

type Reading = {
  brightness: number;
  dark: number;
  clipped: number;
  change: number | null;
  width: number;
  height: number;
  reportedFps: number | null;
};

// Advisory, full-frame preview measurements only. No face/pulse inference or storage.
export default function CameraChecks({
  video,
  active,
}: {
  video: RefObject<HTMLVideoElement | null>;
  active: boolean;
}) {
  const [reading, setReading] = useState<Reading | null>(null);
  useEffect(() => {
    setReading(null);
    if (!active) return;
    const canvas = document.createElement("canvas");
    canvas.width = 160;
    canvas.height = 90;
    const context = canvas.getContext("2d", { willReadFrequently: true });
    let previous: Float32Array | null = null;
    const sample = () => {
      const preview = video.current;
      if (!context || !preview || preview.readyState < 2) return;
      try {
        context.drawImage(preview, 0, 0, 160, 90);
        const pixels = context.getImageData(0, 0, 160, 90).data;
        const gray = new Float32Array(160 * 90);
        let sum = 0,
          dark = 0,
          clipped = 0,
          change = 0;
        for (let i = 0; i < gray.length; i++) {
          const value =
            0.299 * pixels[4 * i] +
            0.587 * pixels[4 * i + 1] +
            0.114 * pixels[4 * i + 2];
          gray[i] = value;
          sum += value;
          if (value <= 20) dark++;
          if (value >= 235) clipped++;
          if (previous) change += Math.abs(value - previous[i]);
        }
        const track = (
          preview.srcObject as MediaStream | null
        )?.getVideoTracks()[0];
        const fps = track?.getSettings().frameRate;
        setReading({
          brightness: sum / gray.length,
          dark: (100 * dark) / gray.length,
          clipped: (100 * clipped) / gray.length,
          change: previous ? change / gray.length : null,
          width: preview.videoWidth,
          height: preview.videoHeight,
          reportedFps:
            typeof fps === "number" && Number.isFinite(fps) && fps > 0
              ? fps
              : null,
        });
        previous = gray;
      } catch {
        previous = null;
        setReading(null);
      }
    };
    sample();
    const interval = setInterval(sample, 500);
    return () => {
      clearInterval(interval);
      previous = null;
    };
  }, [active, video]);
  if (!active) return null;
  return (
    <div className="card" data-testid="camera-checks">
      <p className="eyebrow">PREVIEW CHECKS · FULL FRAME</p>
      <h3>Set up before you start.</h3>
      <dl className="camera-check-values">
        <div>
          <dt>Brightness / 255</dt>
          <dd>{reading ? reading.brightness.toFixed(0) : "Unavailable"}</dd>
        </div>
        <div>
          <dt>Dark / bright pixels</dt>
          <dd>
            {reading
              ? `${reading.dark.toFixed(1)}% / ${reading.clipped.toFixed(1)}%`
              : "Unavailable"}
          </dd>
        </div>
        <div>
          <dt>Image change / 255</dt>
          <dd>
            {reading?.change != null
              ? reading.change.toFixed(1)
              : "Unavailable"}
          </dd>
        </div>
        <div>
          <dt>Camera format</dt>
          <dd>
            {reading ? `${reading.width} × ${reading.height}` : "Unavailable"}
          </dd>
        </div>
        <div>
          <dt>Reported frame rate</dt>
          <dd>
            {reading?.reportedFps != null
              ? `${reading.reportedFps.toFixed(1)} fps`
              : "Unavailable"}
          </dd>
        </div>
      </dl>
      <p className="micro">
        Sampled every half second from the whole preview, including the
        background. Dark ≤20; bright ≥235. Image change includes movement and
        lighting changes. These are setup aids, not face or pulse quality
        scores. Frame rate is reported by the browser; decoded timestamps are
        checked after recording.
      </p>
    </div>
  );
}
