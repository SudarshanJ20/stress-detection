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
    "A private, local space for GAD-7 screening and separate webcam observations. No diagnosis or combined anxiety score.",
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
