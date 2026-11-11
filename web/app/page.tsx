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
            <Camera size={17} /> Camera is always optional
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
              Thoughts deserve privacy. Answers stay in your browser. Recordings
              are sent to your own local Python service only when you choose
              Analyze. Nothing is automatically uploaded to a cloud service.
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
                "Do I have to use my camera?",
                "No. The questionnaire works independently. Camera observations are optional and never change your GAD-7 score.",
              ],
              [
                "Can the camera tell how anxious I am?",
                "We do not make that claim. It reports supported pulse estimates, facial geometric activity and recording quality. No anxiety probability or combined score is produced.",
              ],
              [
                "What happens when I close the page?",
                "Unsaved answers and observations are cleared from the browser session. Local processing artifacts expire or are deleted after analysis. Explicitly saved browser sessions and recordings stay until deleted.",
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
          <Link className="button light" href="/workspace/assessment">
            Make space for a check-in <ArrowUpRight size={18} />
          </Link>
        </section>
      </main>
      <Footer />
    </>
  );
}
