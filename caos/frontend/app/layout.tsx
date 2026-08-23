import type { Metadata } from "next";
import { Suspense } from "react";
import Workspace from "../src/components/Workspace";
import "./globals.css";

export const metadata: Metadata = {
  title: "CAOS — Credit Operating System",
  description: "Evidence-forward institutional credit analysis",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body><Suspense fallback={<div className="state-skeleton" role="status" aria-live="polite" aria-label="Loading"><span /><span /><span /></div>}><Workspace>{children}</Workspace></Suspense></body></html>;
}
