import { Camera } from "@/lib/session";
import { Activity, ScanFace, Video } from "lucide-react";
const reasons: Record<string, string> = {
  no_complete_window: "No complete 30-second interval.",
  no_observations: "No usable observations in this interval.",
  insufficient_valid_data: "Too few usable face or region samples.",
  long_gap: "A gap in the usable signal was too long.",
  unsupported_window_boundary: "The signal does not cover the full interval.",
  insufficient_source_sampling_rate: "The source frame rate is too low.",
  flat_signal: "The recorded signal had too little variation.",
  diffuse_spectrum: "No sufficiently distinct pulse peak.",
  no_in_band_power: "No usable pulse-band signal.",
  unusable_channel_mean: "Color channels could not support a reading.",
  degenerate_pos_projection:
    "The color signal could not support POS extraction.",
  insufficient_pos_samples: "Too few samples for POS extraction.",
};
const regionNames: Record<string, string> = {
  forehead: "Forehead",
  cheek_image_left: "Cheek · image left",
  cheek_image_right: "Cheek · image right",
};
const reasonText = (reason: string) =>
  reasons[reason] || reason.replaceAll("_", " ");
export function Observations({ camera }: { camera: Camera | null }) {
  if (!camera)
    return (
      <section className="card empty">
        <Video size={30} />
        <h3>No video observations added.</h3>
        <p>
          Questionnaire-only session. No video was recorded for this result.
        </p>
      </section>
    );
  const windowSeconds = camera.window_seconds || 30;
  const available = camera.pulse.filter(
    (p) => p.status === "accepted" && p.estimated_bpm !== null,
  ).length;
  return (
    <>
      <div className="source-tag">
        <Video size={16} />
        {camera.source === "prerecorded"
          ? "Prerecorded input · not live"
          : "Recorded webcam session"}{" "}
        · {camera.duration_seconds.toFixed(2)} seconds decoded ·{" "}
        {camera.scheduled_windows} complete {windowSeconds}-second interval
        {camera.scheduled_windows === 1 ? "" : "s"}
      </div>
      {!camera.scheduled_windows && (
        <p className="notice">
          Unavailable: the decoded video contains no complete 30-second
          interval. Please record the full 35 seconds and retry.
        </p>
      )}
      <div className="two-grid">
        <section className="card">
          <ScanFace size={23} />
          <p className="eyebrow">FACE-TRACKING COVERAGE</p>
          <h3 data-testid="tracking-coverage">
            {camera.quality.tracked_coverage == null
              ? "Unavailable"
              : `${(camera.quality.tracked_coverage * 100).toFixed(1)}% of decoded frames`}
          </h3>
          <p>
            {camera.quality.processed_frames} decoded frames ·{" "}
            {camera.quality.missing_face_frames} no-face frames ·{" "}
            {camera.quality.multiple_face_frames} multiple-face frames.
          </p>
          <p className="micro">
            Source: retained single-face tracking. Missing or ambiguous faces
            are excluded.
          </p>
        </section>
        <section className="card pale">
          <Activity size={23} />
          <p className="eyebrow">FACIAL LANDMARK SUMMARIES</p>
          {[
            ["beh_mouth_mean", "Mouth opening · mean", "dimensionless ratio"],
            ["beh_eye_mean", "Eye opening · mean", "dimensionless ratio"],
            [
              "beh_motion_median",
              "Facial landmark motion · median",
              "face sizes per second",
            ],
          ].map(([key, label, unit]) => {
            const value = camera.facial[key];
            return (
              <div className="measurement" key={key}>
                <span>{label}</span>
                <strong data-testid={key}>
                  {value?.value == null
                    ? "Unavailable"
                    : value.value.toFixed(4)}
                </strong>
                <small>
                  {value?.value == null
                    ? value?.reasons?.map(reasonText).join(" ") ||
                      (camera.scheduled_windows
                        ? "Not enough usable landmark samples."
                        : "No complete 30-second interval.")
                    : unit}{" "}
                  · {value?.supported_windows || 0}/
                  {value?.scheduled_windows ?? camera.scheduled_windows}{" "}
                  supported intervals
                </small>
              </div>
            );
          })}
          <p className="micro">
            Source: tracked facial landmarks. Opening is a projected
            vertical-to-width ratio, averaged across valid frames; both eyes are
            required. Motion is normalized displacement of 468 landmarks per
            second and combines facial movement and expression. For multiple
            intervals, each displayed value is the median of supported interval
            statistics.
          </p>
        </section>
      </div>
      <section className="card">
        <p className="eyebrow">CAMERA-DERIVED PULSE · BPM</p>
        <h3>
          {available} of {camera.pulse.length} readings available.
        </h3>
        <p>
          Each method and region is screened separately. Unavailable readings
          remain empty; values are never substituted.
        </p>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Interval</th>
                <th>Method / region</th>
                <th>Reading</th>
                <th>Quality</th>
              </tr>
            </thead>
            <tbody>
              {camera.pulse.map((pulse) => (
                <tr
                  key={`${pulse.method}-${pulse.region}-${pulse.window_index}`}
                >
                  <td>
                    {pulse.window_index * windowSeconds}–
                    {(pulse.window_index + 1) * windowSeconds}s
                  </td>
                  <td>
                    {pulse.method.toUpperCase()} /{" "}
                    {regionNames[pulse.region] || pulse.region}
                  </td>
                  <td>
                    {pulse.status !== "accepted" || pulse.estimated_bpm == null
                      ? "Unavailable"
                      : `${pulse.estimated_bpm.toFixed(1)} BPM`}
                  </td>
                  <td>
                    {pulse.status === "accepted"
                      ? pulse.near_band_edge
                        ? "Supported · near search-band edge"
                        : "Supported by fixed quality screen"
                      : reasonText(
                          pulse.rejection_reason || "insufficient_valid_data",
                        )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {!camera.pulse.length && (
          <p>No complete intervals available for pulse screening.</p>
        )}
        <p className="micro">
          Source: video color changes in the forehead and cheeks, using Green
          and POS extraction. These are camera estimates, not a medical
          heart-rate reading.
        </p>
      </section>
      <details className="card">
        <summary>Recording timing and measurement details</summary>
        {camera.timing && (
          <>
            <p>
              {camera.timing.codec} · {camera.timing.decoded_frames} decoded
              frames · timestamps from the video decoder.
            </p>
            <p>
              First-to-last timestamp span:{" "}
              {camera.timing.pts_span_seconds?.toFixed(3)}s. Final frame extent:{" "}
              {camera.timing.last_frame_duration_seconds?.toFixed(4)}s.
            </p>
            <p>
              {camera.timing.timing_warnings.length
                ? `Timing flags: ${camera.timing.timing_warnings.join(", ").replaceAll("_", " ")}.`
                : "No decoded timing flags."}
            </p>
          </>
        )}
        <p>
          Summaries use complete 30-second intervals. Each opening or motion
          summary requires at least 90% usable samples and two observations.
          Motion excludes track breaks, clipped faces and gaps over 0.15s.
        </p>
        <dl className="observation-details">
          {Object.entries(camera.facial).map(([key, value]) => (
            <div key={key}>
              <dt>
                {value.label || key.replace("beh_", "").replaceAll("_", " ")} ·{" "}
                {value.statistic || key.split("_").at(-1)}
              </dt>
              <dd>
                {value.value == null ? "Unavailable" : value.value.toFixed(4)}{" "}
                {value.value == null
                  ? value.reasons?.map(reasonText).join(" ")
                  : value.unit ||
                    (key.includes("motion")
                      ? "face sizes per second"
                      : "dimensionless ratio")}
              </dd>
            </div>
          ))}
        </dl>
      </details>
    </>
  );
}
