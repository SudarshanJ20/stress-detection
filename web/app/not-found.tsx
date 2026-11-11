import Link from "next/link";
export default function NotFound() {
  return (
    <main id="main" className="content-page">
      <p className="eyebrow">A DIFFERENT PATH</p>
      <h1>
        Let’s find
        <br />
        <em>your way back.</em>
      </h1>
      <Link className="button" href="/">
        Return to Still
      </Link>
    </main>
  );
}
