import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "CAOS — Credit Operating System",
  description: "Evidence-forward institutional credit analysis",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
