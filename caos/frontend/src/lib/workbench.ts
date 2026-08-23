export const routeDestinations = [
  ["cases", "Cases"],
  ["sources", "Sources"],
  ["run-console", "Run Console"],
  ["deep-dive", "Deep-Dive"],
  ["rv-screener", "RV Screener"],
  ["command-center", "Command Center"],
  ["model-builder", "Model Builder"],
  ["report-studio", "Report Studio"],
  ["admin-studio", "Admin Studio"],
] as const;

export type Destination = (typeof routeDestinations)[number][1];
export type WorkflowId = "overview" | "sources" | "analyse" | "compare" | "model" | "publish";

export type Snapshot = {
  id: string;
  digest: string;
  accepted_at: string;
  source_set_version?: number | null;
  artifacts: { id: string; module_id: string; digest: string }[];
};

export type SnapshotView = {
  accepted: Snapshot | null;
  latest_accepted: Snapshot | null;
  switch_required: boolean;
  diff?: { changed?: boolean } | null;
};

export type CaseRecord = {
  id: string;
  name: string;
  issuer: string;
  sector: string;
  source_count?: number;
  accepted_snapshot?: Snapshot | null;
  pathway_fit?: { fit: string; message: string };
  current_execution_id?: string | null;
  deep_research_available?: boolean;
  deep_research_unavailable_reason?: string | null;
};

export type Workflow = {
  id: WorkflowId;
  label: string;
  href: string;
  destinations: readonly Destination[];
  tools?: readonly { label: string; href: string; destination: Destination }[];
};

export const workflows: readonly Workflow[] = [
  { id: "overview", label: "Overview", href: "/command-center", destinations: ["Cases", "Command Center"], tools: [{ label: "Case register", href: "/cases", destination: "Cases" }] },
  { id: "sources", label: "Sources", href: "/sources", destinations: ["Sources"] },
  { id: "analyse", label: "Analyse", href: "/deep-dive", destinations: ["Run Console", "Deep-Dive"], tools: [{ label: "Run", href: "/run-console", destination: "Run Console" }, { label: "Review", href: "/deep-dive", destination: "Deep-Dive" }] },
  { id: "compare", label: "Compare", href: "/rv-screener", destinations: ["RV Screener"] },
  { id: "model", label: "Model", href: "/model-builder", destinations: ["Model Builder"] },
  { id: "publish", label: "Publish", href: "/report-studio", destinations: ["Report Studio"] },
];

export function destinationFromSlug(slug: string): Destination {
  return routeDestinations.find(([route]) => route === slug)?.[1] ?? "Cases";
}

export function workflowFor(destination: Destination): Workflow {
  return workflows.find((workflow) => workflow.destinations.includes(destination)) ?? workflows[0];
}

export function withQuery(path: string, values: Record<string, string | undefined>) {
  const [route, rawQuery] = path.split("?");
  // `trailingSlash: true` + `output: "export"` writes each route's client payload to
  // `<route>/index.txt`. The router only requests that file when the pathname it holds
  // ends in a slash; otherwise it requests `<route>.txt`, gets a 404, and degrades the
  // transition into a full document load after it has already pushed the history entry.
  const pathname = `${route.replace(/\/$/, "")}/`;
  const query = new URLSearchParams(rawQuery);
  for (const [key, value] of Object.entries(values)) {
    if (value) query.set(key, value);
    else query.delete(key);
  }
  return `${pathname}${query.size ? `?${query}` : ""}`;
}

export function evidenceKind(value: string): "source" | "artifact" | null {
  const id = value.trim();
  if (/^src_[a-zA-Z0-9]+$/.test(id)) return "source";
  if (/^art_[a-zA-Z0-9]+$/.test(id)) return "artifact";
  return null;
}
