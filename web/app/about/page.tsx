import { Navigation, Footer } from "@/components/navigation";
import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
export const metadata = { title: "About the assessment" };
export default function Page() {
  return (
    <>
      <Navigation />
      <main id="main" className="content-page">
        <p className="eyebrow">UNDERSTAND THE DIFFERENCE</p>
        <h1>
          Two perspectives.
          <br />
          <em>Never one label.</em>
        </h1>
        <p className="lead">
          A questionnaire can help you reflect on symptoms. The guided demo
          illustrates a future camera experience with a fixed simulated result.
          Still keeps each source clear.
        </p>
        <div className="two-grid">
          <article className="card">
            <span className="eyebrow">01 / QUESTIONNAIRE-DERIVED</span>
            <h2>
              Your experience,
              <br />
              <em>in your words.</em>
            </h2>
            <p>
              GAD-7 asks seven standard questions about the last two weeks.
              Complete responses produce a sum from 0 to 21 and a published
              symptom-severity category. Screening is not diagnosis; discuss
              concerns with a qualified professional.
            </p>
            <p>
              The unscored difficulty question adds context and never changes
              the total.
            </p>
            <Link className="text-link" href="/workspace/assessment">
              Take the questionnaire <ArrowUpRight size={16} />
            </Link>
          </article>
          <article className="card pale">
            <span className="eyebrow">02 / DEMO MODE — SIMULATED RESULT</span>
            <h2>
              A guided experience,
              <br />
              <em>with context.</em>
            </h2>
            <p>
              Explore camera setup, a 35-second recording and an illustrative
              results dashboard. The same predefined sample appears for
              everyone. It is not calculated from your video or questionnaire.
            </p>
            <p>
              Demo mode — simulated result. No video is uploaded, no
              measurements are generated and the recording is discarded. Your
              genuine questionnaire score remains separate.
            </p>
            <Link className="text-link" href="/workspace/demo">
              Explore the guided demo <ArrowUpRight size={16} />
            </Link>
          </article>
        </div>
        <section className="card attribution">
          <h3>Source and attribution</h3>
          <p>
            GAD-7 developed by Drs. Robert L. Spitzer, Janet B.W. Williams, Kurt
            Kroenke and colleagues, with an educational grant from Pfizer Inc.
            The published form permits reproduction, translation, display and
            distribution without permission. Item wording and response choices
            are preserved.
          </p>
          <a href="https://www.hiv.uw.edu/page/mental-health-screening/gad-7">
            Published form and permission
          </a>
          <p>
            The questionnaire covers symptoms over the last two weeks. It does
            not measure momentary anxiety or become more reliable because you
            record a video.
          </p>
        </section>
      </main>
      <Footer />
    </>
  );
}
