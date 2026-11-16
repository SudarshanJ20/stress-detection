import Link from "next/link";
import { Navigation, Footer } from "@/components/navigation";
import { Hero, ProductPreview, Story } from "@/components/landing";
import { ArrowUpRight, ShieldCheck, Camera, Leaf } from "lucide-react";
export default function Home() {
  return (
    <>
      <Navigation />
      <main id="main">
        <Hero />
        <div className="principle-strip">
          <span>
            <ShieldCheck size={17} /> Private by default
          </span>
          <span>
            <Leaf size={17} /> At your own pace
          </span>
          <span>
            <Camera size={17} /> 35-second video recording
          </span>
        </div>
        <ProductPreview />
        <section className="privacy-feature section">
          <div className="privacy-art" aria-hidden="true">
            <div className="orbit one" />
            <div className="orbit two" />
            <div className="orbit three" />
            <ShieldCheck size={48} />
            <span>YOUR SPACE. YOUR CHOICE.</span>
          </div>
          <div>
            <p className="eyebrow">A QUIET COMMITMENT</p>
            <h2>
              Your wellbeing.
              <br />
              <em>Your data.</em>
            </h2>
            <p>
              Answers stay in your browser. With your consent, your recording is
              processed by the local Python service on this computer. Temporary
              video and measurement files are cleaned up after processing.
            </p>
            <Link href="/privacy" className="text-link">
              Read our privacy promise <ArrowUpRight size={16} />
            </Link>
          </div>
        </section>
        <Story />
        <section className="section faq">
          <div>
            <p className="eyebrow">A FEW THINGS TO KNOW</p>
            <h2>
              Clarity comes
              <br />
              <em>first.</em>
            </h2>
          </div>
          <div>
            {[
              [
                "Is Still a diagnosis?",
                "No. GAD-7 is a screening questionnaire. Its categories describe reported symptoms over two weeks, not a diagnosis. A qualified professional can help interpret concerns.",
              ],
              [
                "What does the assessment include?",
                "The combined assessment includes the GAD-7 questionnaire, answer review, camera consent and setup, a 35-second recording, local processing and results. A separately named Questionnaire only route is available for screening without recording.",
              ],
              [
                "What will my results show?",
                "Questionnaire results shows your GAD-7 score and screening category for the last two weeks. Video analysis shows measured tracking coverage, mouth and eye opening ratios, landmark motion and screened camera pulse, with availability and quality indicators.",
              ],
              [
                "What happens when I close the page?",
                "Unsaved answers and results clear when you close or reload. Leaving stops capture and requests cancellation of unfinished processing. Temporary files are cleaned up; if the connection is interrupted, deletion may need a retry in Settings. Explicitly saved sessions and retained recordings stay until you delete them.",
              ],
            ].map(([q, a]) => (
              <details key={q}>
                <summary>
                  {q}
                  <span>+</span>
                </summary>
                <p>{a}</p>
              </details>
            ))}
          </div>
        </section>
        <section className="closing">
          <p className="eyebrow">
            YOU DON’T HAVE TO FIGURE EVERYTHING OUT TODAY.
          </p>
          <h2>
            Just begin <em>here.</em>
          </h2>
          <Link className="button light" href="/workspace/guided">
            Start assessment <ArrowUpRight size={18} />
          </Link>
        </section>
      </main>
      <Footer />
    </>
  );
}
