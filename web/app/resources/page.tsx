import { Navigation, Footer } from "@/components/navigation";
import { ArrowUpRight, BookOpen, Wind, NotebookPen } from "lucide-react";
export const metadata = { title: "Resources" };
export default function Page() {
  return (
    <>
      <Navigation />
      <main id="main" className="content-page">
        <p className="eyebrow">A PLACE TO KEEP LEARNING</p>
        <h1>
          A little guidance.
          <br />
          <em>From trusted sources.</em>
        </h1>
        <p className="lead">
          These resources offer context and practical information. They don’t
          replace a conversation with a qualified professional.
        </p>
        <div className="resource-grid">
          {[
            {
              title: "Understanding anxiety",
              org: "NATIONAL INSTITUTE OF MENTAL HEALTH",
              url: "https://www.nimh.nih.gov/health/topics/anxiety-disorders",
              text: "An overview of anxiety conditions, symptoms and professional care.",
              icon: BookOpen,
            },
            {
              title: "Doing what matters",
              org: "WORLD HEALTH ORGANIZATION",
              url: "https://www.who.int/publications/i/item/9789240003927",
              text: "An illustrated guide to general skills for coping with stress.",
              icon: Wind,
            },
            {
              title: "About GAD-7",
              org: "UNIVERSITY OF WASHINGTON",
              url: "https://www.hiv.uw.edu/page/mental-health-screening/gad-7",
              text: "The published questionnaire, response scale and interpretation.",
              icon: NotebookPen,
            },
          ].map((r) => (
            <a
              className="card resource-card"
              key={r.org}
              href={r.url}
              target="_blank"
              rel="noreferrer"
            >
              <r.icon size={26} />
              <p className="eyebrow">{r.org}</p>
              <h2>{r.title}</h2>
              <p>{r.text}</p>
              <span className="text-link">
                Read resource <ArrowUpRight size={16} />
              </span>
            </a>
          ))}
        </div>
      </main>
      <Footer />
    </>
  );
}
