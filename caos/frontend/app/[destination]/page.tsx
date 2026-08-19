import type { Metadata } from "next";
import Workspace from "../../src/components/Workspace";

const destinations = ["cases", "sources", "run-console", "deep-dive", "rv-screener", "command-center", "model-builder", "report-studio", "admin-studio"];

export function generateStaticParams() {
  return destinations.map((destination) => ({ destination }));
}

export async function generateMetadata({ params }: { params: Promise<{ destination: string }> }): Promise<Metadata> {
  const { destination } = await params;
  const label = destination.split("-").map((part) => part[0].toUpperCase() + part.slice(1)).join(" ");
  return { title: `CAOS — ${label === "Rv Screener" ? "RV Screener" : label === "Deep Dive" ? "Deep-Dive" : label}` };
}

export default async function DestinationPage({ params }: { params: Promise<{ destination: string }> }) {
  const { destination } = await params;
  const label = destination.split("-").map((part) => part[0].toUpperCase() + part.slice(1)).join(" ");
  return <Workspace destination={label === "Run Console" ? "Run Console" : label === "Rv Screener" ? "RV Screener" : label === "Deep Dive" ? "Deep-Dive" : label === "Command Center" ? "Command Center" : label === "Model Builder" ? "Model Builder" : label === "Report Studio" ? "Report Studio" : label} />;
}
