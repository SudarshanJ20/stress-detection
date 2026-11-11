import { AppScreen } from "@/components/workspace";
import { notFound } from "next/navigation";
const sections = [
  "assessment",
  "camera",
  "results",
  "history",
  "reports",
  "tools",
  "settings",
];
export function generateStaticParams() {
  return sections.map((section) => ({ section }));
}
export default async function Page({
  params,
}: {
  params: Promise<{ section: string }>;
}) {
  const { section } = await params;
  if (!sections.includes(section)) notFound();
  return <AppScreen section={section} />;
}
