"use client";
import { useEffect, useRef } from "react";
import { Leaf } from "lucide-react";
export function Heading({
  label,
  title,
  sub,
  focus = false,
}: {
  label: string;
  title: string;
  sub?: string;
  focus?: boolean;
}) {
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    if (focus) heading.current?.focus();
  }, [focus]);
  return (
    <div className="page-heading">
      <p className="eyebrow">{label}</p>
      <h1 ref={heading} tabIndex={focus ? -1 : undefined}>
        {title}
      </h1>
      {sub && <p>{sub}</p>}
    </div>
  );
}
export function Empty({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="card empty">
      <Leaf size={28} />
      <h3>{title}</h3>
      {children}
    </div>
  );
}
