import type { Metadata } from "next";
import localFont from "next/font/local";
import { StateProvider } from "@/components/state";
import "./globals.css";
const editorial = localFont({
  src: "../public/fonts/editorial-latin.ttf",
  variable: "--font-editorial",
  display: "swap",
  weight: "300 700",
});
export const metadata: Metadata = {
  title: {
    default: "Still — A little space to understand yourself",
    template: "%s · Still",
  },
  description:
    "Answer the questionnaire, record a short video, and review your screening results and video analysis. Private processing on this computer.",
};
export default function Root({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={editorial.variable}>
        <a className="skip" href="#main">
          Skip to content
        </a>
        <StateProvider>{children}</StateProvider>
      </body>
    </html>
  );
}
