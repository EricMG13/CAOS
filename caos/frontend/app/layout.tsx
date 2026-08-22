import type { Metadata } from "next";
import { Suspense } from "react";
import Workspace from "../src/components/Workspace";
import "./globals.css";

export const metadata: Metadata = {
  title: "CAOS — Credit Operating System",
  description: "Evidence-forward institutional credit analysis",
};

export default function RootLayout() {
  return <html lang="en"><body><Suspense fallback={null}><Workspace /></Suspense></body></html>;
}
