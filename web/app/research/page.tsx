import { Navigation, Footer } from "@/components/navigation";
import data from "@/lib/research.json";
import Link from "next/link";
export const metadata = { title: "Research & limitations" };
const names: { [key: string]: string } = {
  mean: "Training mean",
  facial: "Facial",
  camera_bpm: "Camera BPM",
  facial_camera_bpm: "Combined",
  quality_values: "Quality",
  missingness: "Missingness",
};
export default function Page() {
  return (
    <>
      <Navigation />
      <main id="main" className="content-page">
        <p className="eyebrow">RESEARCH, WITHOUT THE EMBELLISHMENT</p>
        <h1>
          The full picture.
          <br />
          <em>Including the limits.</em>
        </h1>
        <p className="lead">
          Our locked evaluation compared six predefined models on ten reserved
          participants. External exposure history was unconfirmed: this was not
          a certified untouched cohort.
        </p>
        <div className="notice">
          These models predict UBFC post-session CSAI dimension means, not GAD-7
          categories. None is used in Still’s assessment flow.
        </div>
        {Object.entries(data).map(([target, groups]) => (
          <section key={target} className="card research-table">
            <h2>
              {target === "cognitive_post"
                ? "Cognitive anxiety"
                : "Somatic anxiety"}
            </h2>
            <p>
              {target === "cognitive_post" ? "Primary" : "Secondary"} outcome ·
              10 session outcomes · errors in the released 1–4 score units
            </p>
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Model</th>
                    <th>MAE</th>
                    <th>RMSE</th>
                    <th>R²</th>
                    <th>Better than mean</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(names).map(([key, name]) => {
                    const v = groups[key as keyof typeof groups];
                    return (
                      <tr key={key}>
                        <td>{name}</td>
                        <td>{v.mae.toFixed(4)}</td>
                        <td>{v.rmse.toFixed(4)}</td>
                        <td>{v.r2.toFixed(4)}</td>
                        <td>{v.better_than_mean}/10</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </section>
        ))}
        <div className="two-grid">
          <article className="card">
            <h3>What happened</h3>
            <p>
              Facial features reduced cognitive MAE by only 0.0058 score units.
              Five people improved and five worsened. No model beat training
              mean for somatic MAE or RMSE. The development-set BPM advantage
              did not carry over.
            </p>
            <p>
              All 120 predictions and all participants were retained. One
              missing BPM summary used frozen training-only imputation. All 180
              scheduled windows remained represented.
            </p>
          </article>
          <article className="card pale">
            <h3>What this doesn’t establish</h3>
            <p>
              Ten evaluation participants and six training participants provide
              limited evidence. Fixed task order, speech, movement, recording
              conditions and missingness remain confounds. Session scores do not
              establish momentary anxiety or ordinary webcam performance.
            </p>
            <p>
              No refitting, clipping, tuning, confidence intervals, significance
              tests or deployment-model selection were added.
            </p>
          </article>
        </div>
        <Link className="button" href="/workspace">
          Back to your space
        </Link>
      </main>
      <Footer />
    </>
  );
}
