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
          A questionnaire can help you reflect on symptoms. Video observations
          add separately sourced facial measurements. Processing stays on this
          computer.
        </p>
        <div className="two-grid">
          <article className="card">
            <span className="eyebrow">Questionnaire results</span>
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
              Questionnaire only <ArrowUpRight size={16} />
            </Link>
          </article>
          <article className="card pale">
            <span className="eyebrow">Video analysis</span>
            <h2>
              Video observations,
              <br />
              <em>with context.</em>
            </h2>
            <p>
              Consent to local processing, set up your camera and record 35
              seconds. Your report shows face-tracking coverage, geometric
              opening ratios and landmark motion summaries when supported.
            </p>
            <p>
              Quality checks may leave facial measurements unavailable.
              Temporary recordings are deleted after processing unless you
              explicitly choose to keep them. Questionnaire answers stay in the
              browser.
            </p>
            <Link className="text-link" href="/workspace/guided">
              Start an assessment <ArrowUpRight size={16} />
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
            The questionnaire covers symptoms over the last two weeks. Screening
            is not a diagnosis.
          </p>
        </section>
      </main>
      <Footer />
    </>
  );
}
