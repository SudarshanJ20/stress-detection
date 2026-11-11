"use client";
import { Session } from "@/lib/session";
export default function Trend({ sessions }: { sessions: Session[] }) {
  const dated = new Map<string, Session>();
  for (const s of [...sessions].sort((a, b) => a.date.localeCompare(b.date))) {
    if (s.screening) dated.set(s.date.slice(0, 10), s);
  }
  const points = [...dated.values()];
  if (points.length < 2)
    return (
      <div className="notice">
        A trend needs saved questionnaire results on at least two different
        days. Repeated same-day GAD-7 scores do not measure momentary changes.
      </div>
    );
  const coords = points.map((p, i) => ({
    x: 25 + (i * 550) / Math.max(1, points.length - 1),
    y: 155 - (p.screening!.score / 21) * 130,
    p,
  }));
  return (
    <section className="card">
      <h3>Saved questionnaire observations</h3>
      <p>
        Latest saved score per day. Each describes the preceding two weeks; this
        is not a momentary mood trend.
      </p>
      <svg
        viewBox="0 0 600 190"
        role="img"
        aria-label="Saved GAD-7 scores by day; values listed below"
      >
        <line
          x1="25"
          x2="575"
          y1="155"
          y2="155"
          stroke="currentColor"
          opacity=".2"
        />
        <polyline
          fill="none"
          stroke="var(--teal)"
          strokeWidth="2"
          points={coords.map((c) => `${c.x},${c.y}`).join(" ")}
        />
        {coords.map((c) => (
          <circle key={c.p.id} cx={c.x} cy={c.y} r="4" fill="var(--teal)" />
        ))}
      </svg>
      <ul>
        {points.map((p) => (
          <li key={p.id}>
            {new Date(p.date).toLocaleDateString()}: {p.screening!.score}/21,{" "}
            {p.screening!.category}
          </li>
        ))}
      </ul>
    </section>
  );
}
