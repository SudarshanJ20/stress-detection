import gad from "./gad7.json";
export { gad };
export type Pulse = {
  method: string;
  region: string;
  window_index: number;
  status: string;
  estimated_bpm: number | null;
  rejection_reason: string | null;
  near_band_edge: boolean | null;
};
export type Camera = {
  source: "webcam" | "prerecorded";
  duration_seconds: number;
  scheduled_windows: number;
  window_seconds?: number;
  timing?: {
    codec: string;
    decoded_frames: number;
    decode_complete: boolean;
    pts_span_seconds: number;
    last_frame_duration_seconds: number;
    observed_duration_seconds: number;
    timing_warnings: string[];
    timestamp_source: string;
  };
  availability: string;
  facial: Record<
    string,
    {
      value: number | null;
      supported_windows: number;
      scheduled_windows: number;
      label?: string;
      statistic?: string;
      unit?: string;
      source?: string;
      reasons?: string[];
    }
  >;
  pulse: Pulse[];
  quality: {
    tracked_coverage: number | null;
    region_coverage: Record<string, number>;
    multiple_face_frames: number;
    missing_face_frames: number;
    processed_frames: number;
    track_event_counts: Record<string, number>;
  };
  versions: Record<string, unknown>;
  interpretation: string;
};
export type Screening = {
  score: number;
  category: string;
  source: string;
  timeframe: string;
  version: string;
};
export type Session = {
  mode?: "genuine" | "demo";
  assessment_type?: "combined" | "questionnaire_only" | "video_only";
  id: string;
  date: string;
  screening: Screening | null;
  camera: Camera | null;
  recordingId?: string;
  note: string;
  difficulty?: string;
};
export const genuineSessions = (sessions: Session[]) =>
  sessions.filter(
    (s) =>
      s.mode !== "demo" &&
      (s.assessment_type !== "combined" || Boolean(s.screening && s.camera)),
  );
export function scoreGad(answers: (number | null)[]): Screening {
  if (
    answers.length !== 7 ||
    answers.some((x) => !Number.isInteger(x) || x === null || x < 0 || x > 3)
  )
    throw Error("Answer all seven questions.");
  const score = answers.reduce<number>((a, b) => a + (b ?? 0), 0);
  return {
    score,
    category: gad.bands.find((b) => score >= b.min && score <= b.max)!.label,
    source: "GAD-7 questionnaire",
    timeframe: gad.timeframe,
    version: gad.version,
  };
}
export function report(s: Session) {
  if (s.mode === "demo")
    throw Error("Developer fixtures cannot be exported as assessment reports.");
  if (s.assessment_type === "combined" && (!s.screening || !s.camera))
    throw Error(
      "Complete the questionnaire and video analysis before exporting this assessment.",
    );
  return {
    report_version: "Still 1.0.0",
    date: s.date,
    mode:
      s.screening && s.camera
        ? "Combined assessment"
        : s.screening
          ? "Questionnaire only"
          : "Video analysis",
    assessment_type:
      s.assessment_type ??
      (s.screening && s.camera
        ? "combined"
        : s.screening
          ? "questionnaire_only"
          : "video_only"),
    recording_retained_locally: Boolean(s.recordingId),
    section_labels: {
      questionnaire: "Questionnaire results",
      webcam: "Video analysis",
    },
    questionnaire: s.screening,
    webcam: s.camera ?? {
      availability: "not_added",
      explanation:
        "Questionnaire-only session. No video was recorded for this result.",
    },
    note: s.note,
    questionnaire_difficulty: s.difficulty || null,
    interpretation:
      "Questionnaire screening covers the last two weeks and is not a diagnosis. Video observations are separately attributed camera measurements.",
    questionnaire_attribution: gad.attribution,
    sources: [gad.source, gad.scoring_source],
  };
}
export function download(value: unknown, name: string) {
  const url = URL.createObjectURL(
    new Blob([JSON.stringify(value, null, 2)], { type: "application/json" }),
  );
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
export async function api(path: string, options: RequestInit = {}) {
  let r: Response;
  try {
    r = await fetch("/api/local" + path, {
      ...options,
      headers: { "X-Still-Local": "1", ...options.headers },
    });
  } catch {
    throw Error(
      "The local analysis service is unavailable. Start the Python backend and try again.",
    );
  }
  if (!r.ok) {
    let detail = "The local service could not complete this request.";
    try {
      detail = (await r.json()).detail ?? detail;
    } catch {}
    throw Error(detail);
  }
  return r.json();
}
