"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { Menu, X, ArrowUpRight, Leaf } from "lucide-react";
const links = [
  ["/", "Home"],
  ["/about", "The assessment"],
  ["/resources", "Resources"],
  ["/privacy", "Our privacy promise"],
];
export function Logo() {
  return (
    <Link className="logo" href="/" aria-label="Still home">
      <span className="brand-icon">
        <Leaf size={22} />
      </span>
      still<span className="brand-dot">.</span>
    </Link>
  );
}
export function Navigation() {
  const path = usePathname();
  const [open, setOpen] = useState(false);
  const dialog = useRef<HTMLDialogElement>(null);
  const toggle = (value: boolean) => {
    setOpen(value);
    if (value) dialog.current?.showModal();
    else dialog.current?.close();
  };
  useEffect(() => {
    dialog.current?.close();
  }, [path]);
  return (
    <>
      <header className="site-header">
        <Logo />
        <nav className="desktop-nav" aria-label="Main">
          {links.map(([url, label]) => (
            <Link
              aria-current={path === url ? "page" : undefined}
              key={url}
              href={url}
            >
              {label}
            </Link>
          ))}
        </nav>
        <Link className="button small nav-cta" href="/workspace">
          Your space <ArrowUpRight size={15} />
        </Link>
        <button
          className="icon-button mobile-menu"
          aria-label="Open navigation"
          aria-expanded={open}
          onClick={() => toggle(true)}
        >
          <Menu />
        </button>
      </header>
      <dialog
        ref={dialog}
        className="mobile-drawer"
        onClose={() => setOpen(false)}
        onClick={(e) => {
          if (e.target === dialog.current) toggle(false);
        }}
      >
        <div>
          <div className="row between">
            <Logo />
            <button
              className="icon-button"
              aria-label="Close navigation"
              onClick={() => toggle(false)}
            >
              <X />
            </button>
          </div>
          <nav aria-label="Mobile">
            {[...links, ["/workspace", "Your space"]].map(([u, l]) => (
              <Link onClick={() => toggle(false)} href={u} key={u}>
                {l}
              </Link>
            ))}
          </nav>
          <p className="muted">A quiet place to begin.</p>
        </div>
      </dialog>
    </>
  );
}
export function Footer() {
  return (
    <footer className="site-footer">
      <div>
        <Logo />
        <p>A little space. A clearer perspective.</p>
        <span className="eyebrow">ANXIETY SCREENING & WELLBEING</span>
      </div>
      <div>
        <b>Explore</b>
        <Link href="/about">The assessment</Link>
        <Link href="/workspace/tools">Wellbeing tools</Link>
        <Link href="/research">Research & limitations</Link>
      </div>
      <div>
        <b>Your privacy</b>
        <Link href="/privacy">How your data is handled</Link>
        <Link href="/workspace/settings">Storage & deletion</Link>
        <Link href="/resources">Support resources</Link>
      </div>
      <div className="footer-bottom">
        A local major-project presentation. Screening is not a diagnosis.{" "}
        <span>No account. No analytics. Your choice to save.</span>
      </div>
    </footer>
  );
}
