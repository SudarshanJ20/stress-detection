"use client";
import Link from "next/link";
import { useStill } from "./state";
import Image from "next/image";
import { motion, useReducedMotion } from "motion/react";
import { useEffect, useRef, useState } from "react";
import {
  ArrowUpRight,
  ArrowRight,
  ShieldCheck,
  ScanFace,
  NotebookPen,
  Wind,
  Check,
  LockKeyhole,
} from "lucide-react";
export function Hero() {
  const system = useReducedMotion();
  const { reduced } = useStill();
  const reduce = system || reduced;
  return (
    <section className="hero">
      <motion.div
        initial={reduce ? false : { opacity: 0, y: 25 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8 }}
        className="hero-copy"
      >
        <p className="eyebrow">
          <span className="tiny-line" /> A MOMENT FOR YOURSELF
        </p>
        <h1>
          Find a little
          <br />
          space.
          <br />
          <em>Feel more you.</em>
        </h1>
        <p className="lead">
          A thoughtful check-in with how you’re feeling.
          <br className="desktop" /> A clearer view of what your body is doing.
          <br className="desktop" /> Two perspectives. Room to understand both.
        </p>
        <div className="hero-actions">
          <Link className="button" href="/workspace/assessment">
            Begin your check-in <ArrowUpRight size={18} />
          </Link>
          <Link className="text-link" href="/about">
            How it works <ArrowRight size={15} />
          </Link>
        </div>
        <p className="micro">
          <LockKeyhole size={13} /> Private by default. No account needed.
        </p>
      </motion.div>
      <motion.div
        className="hero-visual"
        initial={reduce ? false : { opacity: 0, clipPath: "inset(8% 0 0 0)" }}
        animate={{ opacity: 1, clipPath: "inset(0% 0 0 0)" }}
        transition={{ duration: 1.1 }}
      >
        <Image
          src="/images/forest.webp"
          alt="A quiet pathway disappearing into a misty green forest"
          fill
          priority
          sizes="(max-width: 768px) 95vw, 50vw"
          className="hero-image"
        />
        <div className="image-topline">
          <span>A SMALL PAUSE, A NEW PERSPECTIVE</span>
          <span>01 — STILL</span>
        </div>
        <div className="photo-caption">
          <span className="caption-circle">
            <Wind size={26} />
          </span>
          <div>
            There is no right way
            <br />
            <em>to feel right now.</em>
          </div>
        </div>
        <div className="image-corner">TAKE YOUR TIME ↗</div>
      </motion.div>
      <div className="hero-foot">
        <span>SCREENING, WITH PERSPECTIVE</span>
        <span>Built for reflection. Grounded in transparency.</span>
        <ArrowRight size={18} />
      </div>
    </section>
  );
}
export function ProductPreview() {
  const [tab, setTab] = useState("Questionnaire");
  return (
    <section className="section preview-section">
      <div className="section-intro">
        <p className="eyebrow">A CLEARER PICTURE, IN YOUR HANDS</p>
        <h2>
          More understanding.
          <br />
          <em>Less guessing.</em>
        </h2>
        <p>
          Your answers tell one story. Webcam observations offer a separate view
          of facial activity and screened pulse. We keep the distinction clear.
        </p>
        <Link className="text-link" href="/about">
          Explore the assessment <ArrowUpRight size={16} />
        </Link>
      </div>
      <div className="product-preview card">
        <div className="row between">
          <span className="eyebrow">INSIDE YOUR CHECK-IN</span>
          <span className="pill">Interactive guide</span>
        </div>
        <div className="tabs" role="tablist" aria-label="Product guide">
          {["Questionnaire", "Webcam", "Your report"].map((t) => (
            <button
              id={"guide-" + t.replaceAll(" ", "-")}
              aria-controls="guide-panel"
              role="tab"
              aria-selected={tab === t}
              key={t}
              tabIndex={tab === t ? 0 : -1}
              onKeyDown={(event) => {
                const tabs = ["Questionnaire", "Webcam", "Your report"];
                const index = tabs.indexOf(t);
                const next =
                  event.key === "ArrowRight"
                    ? tabs[(index + 1) % 3]
                    : event.key === "ArrowLeft"
                      ? tabs[(index + 2) % 3]
                      : event.key === "Home"
                        ? tabs[0]
                        : event.key === "End"
                          ? tabs[2]
                          : null;
                if (next) {
                  event.preventDefault();
                  setTab(next);
                  document
                    .getElementById("guide-" + next.replaceAll(" ", "-"))
                    ?.focus();
                }
              }}
              onClick={() => setTab(t)}
            >
              {t}
            </button>
          ))}
        </div>
        <div
          id="guide-panel"
          aria-labelledby={"guide-" + tab.replaceAll(" ", "-")}
          className="preview-content"
          role="tabpanel"
        >
          <span className="large-icon">
            {tab === "Questionnaire" ? (
              <NotebookPen />
            ) : tab === "Webcam" ? (
              <ScanFace />
            ) : (
              <ShieldCheck />
            )}
          </span>
          <h3>
            {tab === "Questionnaire"
              ? "A check-in, not a label."
              : tab === "Webcam"
                ? "Observations, honestly presented."
                : "Only what you choose to keep."}
          </h3>
          <p>
            {tab === "Questionnaire"
              ? "Seven standard GAD-7 questions about the last two weeks. Your result comes from your answers—not your appearance."
              : tab === "Webcam"
                ? "An optional recording, analyzed on your local computer. Supported pulse estimates and geometric facial observations are shown with their limitations."
                : "Download or print a report with clearly separated sources. Sessions stay temporary unless you explicitly save a copy."}
          </p>
          <div className="preview-note">
            <Check size={16} />{" "}
            {tab === "Webcam"
              ? "No live numbers are estimated in this preview."
              : "This guide contains no sample health data."}
          </div>
        </div>
        <Link href="/workspace" className="preview-link">
          Open your space <ArrowUpRight size={18} />
        </Link>
      </div>
    </section>
  );
}
export function Story() {
  const root = useRef<HTMLDivElement>(null);
  const system = useReducedMotion();
  const { reduced } = useStill();
  const reduce = system || reduced;
  useEffect(() => {
    if (reduce || window.matchMedia("(prefers-reduced-motion: reduce)").matches)
      return;
    let cleanup = () => {};
    let alive = true;
    Promise.all([import("gsap"), import("gsap/ScrollTrigger")]).then(
      ([g, s]) => {
        if (!alive) return;
        g.gsap.registerPlugin(s.ScrollTrigger);
        const ctx = g.gsap.context(() => {
          g.gsap.from("[data-step]", {
            opacity: 1,
            y: 25,
            stagger: 0.12,
            scrollTrigger: {
              trigger: root.current,
              start: "top 85%",
              end: "bottom 65%",
              scrub: 0.6,
            },
          });
        }, root);
        cleanup = () => ctx.revert();
      },
    );
    return () => {
      alive = false;
      cleanup();
    };
  }, [reduce]);
  return (
    <section className="story section" ref={root}>
      <div className="row between">
        <div>
          <p className="eyebrow">A GENTLER WAY TO CHECK IN</p>
          <h2>
            One small step.
            <br />
            <em>Then another.</em>
          </h2>
        </div>
        <span className="muted">You decide how far to go.</span>
      </div>
      <div className="story-grid">
        {[
          [
            "01",
            "Reflect",
            "Answer seven questions about the past two weeks. No right answers, no rush.",
          ],
          [
            "02",
            "Observe",
            "Optionally record a short camera session. See what was measurable—and what wasn’t.",
          ],
          [
            "03",
            "Take it with you",
            "Review your results, find a wellbeing tool, and save a report only if you want to.",
          ],
        ].map(([n, h, p]) => (
          <article data-step key={n}>
            <span className="step-number">{n}</span>
            <h3>{h}</h3>
            <p>{p}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
