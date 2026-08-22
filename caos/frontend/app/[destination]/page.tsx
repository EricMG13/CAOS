import type { Metadata } from "next";
import Workspace from "../../src/components/Workspace";
import { destinationFromSlug, routeDestinations } from "../../src/lib/workbench";

export function generateStaticParams() {
  return routeDestinations.map(([destination]) => ({ destination }));
}

export async function generateMetadata({ params }: { params: Promise<{ destination: string }> }): Promise<Metadata> {
  const { destination } = await params;
  return { title: `CAOS — ${destinationFromSlug(destination)}` };
}

export default async function DestinationPage({ params }: { params: Promise<{ destination: string }> }) {
  const { destination } = await params;
  return <Workspace destination={destinationFromSlug(destination)} />;
}
