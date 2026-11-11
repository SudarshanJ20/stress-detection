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
          A questionnaire can help you reflect on symptoms. A camera can observe
          what is measurable. Still gives each its own space.
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
            <span className="eyebrow">02 / WEBCAM-DERIVED</span>
            <h2>
              Your observations,
              <br />
              <em>with context.</em>
            </h2>
            <p>
              An optional 35-second recording supports a complete 30-second
              analysis interval. Facial opening and motion are geometric
              proxies. Green and POS pulse estimates are screened separately for
              each region; unsupported readings stay unavailable.
            </p>
            <p>
              These observations never alter your screening score. This short
              recording is not equivalent to the three-task UBFC session
              contract, and no anxiety regression model is deployed.
            </p>
            <Link className="text-link" href="/research">
              Read the actual research <ArrowUpRight size={16} />
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
            GAD-7 categories are not equivalent to UBFC’s author-computed CSAI
            anxiety means. Research labels cannot validate a GAD-7 result.
          </p>
        </section>
      </main>
      <Footer />
    </>
  );
}
