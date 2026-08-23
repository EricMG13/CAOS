import type { Metadata, Viewport } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import { Suspense } from "react";
import Workspace from "../src/components/Workspace";
import "./globals.css";

const sans = Inter({ subsets: ["latin"], display: "swap", variable: "--font-sans" });
const mono = JetBrains_Mono({ subsets: ["latin"], display: "swap", variable: "--font-mono" });

export const metadata: Metadata = {
  title: "CAOS — Credit Operating System",
  description: "Evidence-forward institutional credit analysis",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  themeColor: "#0a0a0f",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en" className={`${sans.variable} ${mono.variable}`}><body><Suspense fallback={<div className="state-skeleton" role="status" aria-live="polite" aria-label="Loading"><span /><span /><span /></div>}><Workspace>{children}</Workspace></Suspense></body></html>;
}
