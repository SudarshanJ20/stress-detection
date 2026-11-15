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
  availability: string;
  facial: Record<
    string,
    {
      value: number | null;
      supported_windows: number;
      scheduled_windows: number;
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
  demoCapture?: { duration_seconds: number; completed_at: string };
  id: string;
  date: string;
  screening: Screening | null;
  camera: Camera | null;
  recordingId?: string;
  note: string;
  difficulty?: string;
};
export const DEMO_LABEL = "Demo mode — simulated result";
export const DEMO_EXAMPLE = Object.freeze({
  score: 62,
  unit: "%",
  label: "Illustrative score",
  category: "Moderate — example",
  explanation:
    "Simulated result for interface demonstration. This score is not calculated from your video or questionnaire.",
});
export const genuineSessions = (sessions: Session[]) =>
  sessions.filter((s) => s.mode !== "demo");
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
  return {
    report_version: "Still 1.0.0",
    date: s.date,
    mode:
      s.mode === "demo"
        ? DEMO_LABEL
        : "Questionnaire and optional observations",
    illustrative_example: s.mode === "demo" ? DEMO_EXAMPLE : null,
    demo_capture: s.mode === "demo" ? (s.demoCapture ?? null) : null,
    questionnaire: s.screening,
    webcam: s.camera ?? {
      availability: s.mode === "demo" ? "unavailable" : "not_added",
      explanation:
        s.mode === "demo"
          ? "Demo capture only. No video measurements were generated; recording data was discarded in the browser."
          : "No webcam observations were added.",
    },
    note: s.note,
    questionnaire_difficulty: s.difficulty || null,
    interpretation:
      "Questionnaire-derived screening covers the last two weeks and is not a diagnosis. Webcam observations and illustrative examples do not validate or change GAD-7.",
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
