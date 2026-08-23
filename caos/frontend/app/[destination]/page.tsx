import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { destinationFromSlug, routeDestinations } from "../../src/lib/workbench";

export function generateStaticParams() {
  return routeDestinations.map(([destination]) => ({ destination }));
}

export async function generateMetadata({ params }: { params: Promise<{ destination: string }> }): Promise<Metadata> {
  const { destination } = await params;
  const known = routeDestinations.some(([route]) => route === destination);
  return { title: known ? `CAOS — ${destinationFromSlug(destination)}` : "CAOS — Not found" };
}

export default async function DestinationPage({ params }: { params: Promise<{ destination: string }> }) {
  const { destination } = await params;
  if (!routeDestinations.some(([route]) => route === destination)) notFound();
  return null;
}
