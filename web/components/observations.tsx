import { Camera } from "@/lib/session";
import { Activity, ScanFace, Video } from "lucide-react";
export function Observations({ camera }: { camera: Camera | null }) {
  if (!camera)
    return (
      <section className="card empty">
        <Video size={30} />
        <h3>No camera observations added.</h3>
        <p>
          The questionnaire result stands on its own. Camera capture is
          optional.
        </p>
      </section>
    );
  const percent = (x: number | null) =>
    x === null ? "Unavailable" : `${(100 * x).toFixed(1)}% of decoded frames`;
  return (
    <>
      <div className="source-tag">
        <Video size={16} />
        {camera.source === "prerecorded"
          ? "Prerecorded input · not live"
          : "Recorded webcam session"}{" "}
        · {camera.duration_seconds.toFixed(1)} seconds
      </div>
      {!camera.scheduled_windows && (
        <p className="notice">
          Insufficient recording length: no complete 30-second interval. Pulse
          and window-based facial summaries are unavailable.
        </p>
      )}
      <section className="two-grid">
        <article className="card">
          <ScanFace size={22} />
          <p className="eyebrow">TRACKING QUALITY</p>
          <h3>{percent(camera.quality.tracked_coverage)}</h3>
          <p>
            {camera.quality.multiple_face_frames} multiple-face frames ·{" "}
            {camera.quality.missing_face_frames} no-face frames. Invalid
            observations are excluded.
          </p>
          <p>
            Track events:{" "}
            {Object.entries(camera.quality.track_event_counts)
              .map(([k, v]) => `${k}: ${v}`)
              .join(" · ") || "none"}
            .
          </p>
        </article>
        <article className="card pale">
          <Activity size={22} />
          <p className="eyebrow">FACIAL GEOMETRIC PROXIES</p>
          {[
            ["beh_mouth_mean", "Mouth opening ratio"],
            ["beh_eye_mean", "Eye opening ratio"],
            ["beh_motion_median", "Facial motion / second"],
          ].map(([key, label]) => {
            const f = camera.facial[key];
            return (
              <div className="measurement" key={key}>
                <span>{label}</span>
                <strong>
                  {f?.value == null ? "Unavailable" : f.value.toFixed(4)}
                </strong>
                <small>
                  {f?.supported_windows ?? 0}/
                  {f?.scheduled_windows ?? camera.scheduled_windows} windows
                  supported
                </small>
              </div>
            );
          })}
          <p className="micro">
            Projected 2D ratios and normalized motion—not emotion or anxiety
            labels. Motion excludes clipped faces and track breaks.
          </p>
        </article>
      </section>
      <section className="card">
        <p className="eyebrow">
          SCREENED CAMERA PULSE · NOT VALIDATED ACCURACY
        </p>
        <h3>Every region. Both methods.</h3>
        <p>
          Accepted FFT estimates are screening outputs, not a heart-health
          assessment. A region can be available while its pulse is rejected.
        </p>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Interval</th>
                <th>Method / region</th>
                <th>Estimate</th>
                <th>Availability</th>
              </tr>
            </thead>
            <tbody>
              {camera.pulse.map((p) => (
                <tr key={`${p.method}-${p.region}-${p.window_index}`}>
                  <td>
                    {p.window_index * 30}–{(p.window_index + 1) * 30}s
                  </td>
                  <td>
                    {p.method.toUpperCase()} / {p.region.replaceAll("_", " ")}
                  </td>
                  <td>
                    {p.estimated_bpm == null
                      ? "Unavailable"
                      : `${p.estimated_bpm.toFixed(1)} BPM`}
                  </td>
                  <td>
                    {p.status === "accepted"
                      ? p.near_band_edge
                        ? "Accepted · near search-band edge"
                        : "Accepted by fixed screen"
                      : p.rejection_reason?.replaceAll("_", " ") ||
                        "Unsupported"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {camera.pulse.length === 0 && (
          <p>No complete intervals to screen. No value has been substituted.</p>
        )}
        <p className="micro">
          No calibrated confidence percentage is available. Camera/wrist
          synchronization remains unverified; no wrist comparison is shown.
        </p>
      </section>
    </>
  );
}
