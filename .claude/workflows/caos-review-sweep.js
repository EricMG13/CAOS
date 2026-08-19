export const meta = {
  name: 'caos-review-sweep',
  description: 'Item-by-item review sweep with adversarial verify + matrix synthesis. Pick a plan via args.plan: fe | be | security | perf | seam.',
  phases: [
    { title: 'Review', detail: 'one agent per item, sequential (session token cap)' },
    { title: 'Verify', detail: 'adversarial refute, batched 3 at a time' },
    { title: 'Synthesize', detail: 'write the REVIEW_MATRIX_*.md for this plan' },
  ],
}

// ---------------------------------------------------------------------------
// One skeleton, five configs. Launch:
//   Workflow({ name: 'caos-review-sweep', args: { plan: 'fe' } })
//   ...plan = 'be' | 'security' | 'perf' | 'seam'
// Optional: args.items = ['FE-6','FE-9'] to run a subset.
// Report-only. No code changes, no commits. Fix loops stay as /loop (see notes below).
// ---------------------------------------------------------------------------

const ADJ_PHASE1 =
  'single-team IDOR, XFF rate-key spoof, global login-bucket self-DoS, edge-secret-trust — all Phase-1 by-design, documented in SECURITY.md.'

const CONFIG = {
  fe: {
    matrixFile: 'caos/docs/qa/REVIEW_MATRIX_FRONTEND.md',
    root: 'caos/frontend/src',
    tool: 'GitNexus query()/context()',
    lenses:
      'correctness; mock-vs-live seam honesty (no seeded figure presented as live; ATLF-fabrication guard holds); ' +
      'CLAUDE.md design-token conformance (surfaces ramp, hairline borders, accent blue, tabular-nums with aligned decimals, ' +
      '32px uppercase Panel headers, 160ms motion honoring prefers-reduced-motion, color-is-signal-not-decoration); ' +
      'dead code; test-coverage gaps',
    adjudicated:
      'command sample-portfolio mock (intentional, on-screen labeled "Sample portfolio — not live"), /deepdive 643KB first-load ' +
      '(dense-desk by design, already next/dynamic-split), single-team IDOR.',
    items: [
      { id: 'FE-1', scope: 'app/command, app/monitor, components/command, lib/command' },
      { id: 'FE-2', scope: 'app/pipeline, app/upload, components/pipeline, components/upload, lib/pipeline' },
      { id: 'FE-3', scope: 'app/deepdive, components/deepdive, lib/deepdive, lib/evidence-sync.tsx' },
      { id: 'FE-4', scope: 'app/model, components/model, lib/model, lib/model-mode.ts (incl. ScenarioPanel)' },
      { id: 'FE-5', scope: 'app/reports, components/reports, lib/reports (light paper tear-sheet theme)' },
      { id: 'FE-6', scope: 'app/query, components/query, lib/query (walks/questions/views/synthesis; current-branch churn)' },
      { id: 'FE-7', scope: 'app/issuers, issuer-profile overlay components, lib/issuers.ts, lib/issuer-profile-charts.ts' },
      { id: 'FE-8', scope: 'app/research, app/settings, components/research, lib/research-prefs.ts' },
      { id: 'FE-9', scope: 'components/shared, components/charts, lib/{api,format,citations,chart-colors,a11y,use-modal-a11y,issuers}.ts, app/layout.tsx, app/error.tsx, app/global-error.tsx, app/not-found.tsx, app/globals.css (highest fan-in)' },
      { id: 'FE-10', scope: 'colocated *.test.ts(x) under caos/frontend/src + caos/tests/frontend e2e' },
    ],
  },

  be: {
    matrixFile: 'caos/docs/qa/REVIEW_MATRIX_BACKEND.md',
    root: 'caos/server',
    tool: 'GitNexus context()/impact()',
    lenses:
      'correctness (every CP-1-derived divide/multiply gated by engine.periods.is_finite_number; NaN/zero-denominator degrade paths; ' +
      'finding-gate abort semantics; trust boundary = unvalidated runtime_output); ' +
      'LLM fault isolation (each lane keeps one of: per-module Blocked gate / council return_exceptions / deterministic fallback; ' +
      'caos_llm_timeout_s on all clients); perf bounds (every Run/Chunk scan capped + ordered, no sync I/O on the event loop); ' +
      'security; test-coverage gaps',
    adjudicated:
      ADJ_PHASE1 + ' Also accepted: on-host backup, EDGAR in-process throttle, no-OCR (documented Phase-1 limits).',
    items: [
      { id: 'BE-1', scope: 'engine/{factpack,reported_cp1,edgar_cp1,adjusted,periods,metrics}.py + server/edgar.py — CP-1 spine, is_finite_number gate' },
      { id: 'BE-2', scope: 'engine/{capstructure,covenants,liquidity,downside,distress,relval,peers,coststructure,earnings,refinancing,budget,macro,catalysts,legal,sponsor,portfoliofit}.py — analytics' },
      { id: 'BE-3', scope: 'engine/{planner,registry,runner,gate,synth,council,debate,schemas,lineage,presets,fixtures,report}.py — orchestration + CP-5 gates' },
      { id: 'BE-4', scope: 'engine/{llm_client,openrouter,gemini,llm_safety}.py, server/llm.py — LLM lanes; verify NO lane has tools or writes' },
      { id: 'BE-5', scope: 'engine/{querygraph,queryoverlay,textscan,readiness}.py, server/{nlquery,retrieval,vault_export}.py — query lane, known perf cluster' },
      { id: 'BE-6', scope: 'server/routes/ (15 routers) + server/main.py — API surface, authz, validation, 404-detail masking' },
      { id: 'BE-7', scope: 'server/{identity,passwords,rate_limit,access_log,avscan,config,erase_analyst}.py — identity/security' },
      { id: 'BE-8', scope: 'server/{database,seed,ingest,scenario,run_executor,research_executor,deepresearch}.py, server/migrations/, server/scripts/' },
      { id: 'BE-9', scope: 'caos/tests/{server,perf,stress,cohort,fixtures} incl. golden-master drift alarm' },
    ],
  },

  security: {
    matrixFile: 'caos/docs/qa/REVIEW_MATRIX_SECURITY.md',
    root: 'caos/server',
    tool: 'GitNexus explain() for taint findings + context()',
    lenses:
      'authn/authz on every endpoint (signed-cookie identity, edge-proxy header assumptions); input validation at trust boundaries; ' +
      '404-detail masking preserved; rate-limit coverage; secrets handling (fail-closed at boot); ' +
      'injection surfaces (SQL / path-traversal / prompt)',
    adjudicated: ADJ_PHASE1,
    items: [
      { id: 'auth.py', scope: 'server/routes/auth.py' },
      { id: 'chat.py', scope: 'server/routes/chat.py' },
      { id: 'digest.py', scope: 'server/routes/digest.py' },
      { id: 'edgar.py', scope: 'server/routes/edgar.py' },
      { id: 'health.py', scope: 'server/routes/health.py' },
      { id: 'ingestion.py', scope: 'server/routes/ingestion.py — upload/path-traversal/AV-scan-before-parse' },
      { id: 'issuers.py', scope: 'server/routes/issuers.py' },
      { id: 'models.py', scope: 'server/routes/models.py' },
      { id: 'portfolio.py', scope: 'server/routes/portfolio.py' },
      { id: 'query.py', scope: 'server/routes/query.py' },
      { id: 'research.py', scope: 'server/routes/research.py' },
      { id: 'runs.py', scope: 'server/routes/runs.py — create-run asyncio.Lock, analyst_id stamping' },
      { id: 'scenario.py', scope: 'server/routes/scenario.py' },
      { id: 'settings.py', scope: 'server/routes/settings.py' },
      { id: 'sponsors.py', scope: 'server/routes/sponsors.py' },
      { id: 'main+identity', scope: 'server/main.py + server/identity.py — edge_origin_guard constant-time, cookie identity, boot secret checks' },
    ],
  },

  perf: {
    matrixFile: 'caos/docs/qa/REVIEW_MATRIX_PERF.md',
    root: 'caos/server',
    tool: 'GitNexus context() + confirm reachability from a real endpoint; caos/tests/perf harness where it applies',
    lenses:
      'every Run/Chunk/Document query has .order_by + .limit caps; no sync filesystem work (rglob/read_text/getmtime) or CPU-heavy ' +
      'work on the event loop (asyncio.to_thread it); no per-row N+1 (batch .in_() instead). Record a finding only if the hot path ' +
      'is reachable from a real endpoint.',
    adjudicated:
      'limiter + create-run lock + EDGAR throttle + model-mode all assume ONE process — Phase-1 single-worker by design, do not flag.',
    items: [
      { id: 'nlquery.py', scope: 'server/nlquery.py — execute_synthesis scan caps' },
      { id: 'retrieval.py', scope: 'server/retrieval.py — retrieve_corpus / retrieve_corpus_by_issuer caps' },
      { id: 'vault_export.py', scope: 'server/vault_export.py — sync_analyst_memos off-thread' },
      { id: 'querygraph.py', scope: 'engine/querygraph.py — _latest_run cap, per-run COUNT N+1' },
      { id: 'queryoverlay.py', scope: 'engine/queryoverlay.py' },
      { id: 'readiness.py', scope: 'engine/readiness.py — batched head-chunk query' },
      { id: 'textscan.py', scope: 'engine/textscan.py' },
      { id: 'routes/query.py', scope: 'server/routes/query.py' },
      { id: 'routes/ingestion.py', scope: 'server/routes/ingestion.py — off-thread vault write' },
      { id: 'routes/runs.py', scope: 'server/routes/runs.py' },
      { id: 'ingest.py', scope: 'server/ingest.py' },
      { id: 'run_executor.py', scope: 'server/run_executor.py' },
    ],
  },

  seam: {
    matrixFile: 'caos/docs/qa/REVIEW_MATRIX_SEAMS.md',
    root: 'caos',
    tool: 'GitNexus query() to find every frontend call site of each endpoint',
    lenses:
      'the mock↔live seam is the recurring #1 risk — judge whether each surface is honest about live-vs-seeded data',
    adjudicated:
      'FEATURE_TRACKER.csv is CRLF — if you touch it, edit in binary mode only (text-mode rewrite churns the whole diff).',
    items: [
      { id: 'SEAM-1', scope: 'API contract parity: frontend lib/api.ts (+ per-concept fetchers) vs caos/server/routes/* signatures + response models vs OpenAPI. Tracker claims 42/42 parity but there are now 53 endpoints — re-verify path/param/response/error drift.' },
      { id: 'SEAM-2', scope: 'Mock-vs-live honesty: every UI surface rendering seeded mock must be labeled or overlaid by live runs; no fabricated figure presented as live; ATLF-fabrication guard intact. HIGHEST RISK — audit first.' },
      { id: 'SEAM-3', scope: 'Error-surface parity: backend error / 404-masking shapes vs frontend error surfaces (error.tsx, global-error.tsx, not-found.tsx, error-surfaces).' },
      { id: 'SEAM-4', scope: 'Auth seam: edge proxy → signed cookie → analyst_id stamping on runs → frontend session handling.' },
    ],
  },
}

// ---------------------------------------------------------------------------

const FINDINGS_SCHEMA = {
  type: 'object',
  required: ['findings'],
  properties: {
    findings: {
      type: 'array',
      items: {
        type: 'object',
        required: ['file', 'line', 'severity', 'summary'],
        properties: {
          file: { type: 'string', description: 'repo-relative path' },
          line: { type: 'number' },
          severity: { type: 'string', enum: ['high', 'med', 'low'] },
          lens: { type: 'string' },
          summary: { type: 'string' },
          failure: { type: 'string', description: 'concrete inputs/state -> wrong output/crash' },
        },
      },
    },
  },
}

const VERDICT_SCHEMA = {
  type: 'object',
  required: ['refuted'],
  properties: {
    refuted: { type: 'boolean' },
    severity: { type: 'string', enum: ['high', 'med', 'low'] },
    reason: { type: 'string' },
  },
}

// ---------------------------------------------------------------------------

const plan = (args && args.plan) || 'fe'
const cfg = CONFIG[plan]
if (!cfg) {
  log(`unknown plan "${plan}" — choose one of: ${Object.keys(CONFIG).join(', ')}`)
  return { error: 'unknown plan', plan }
}

let items = cfg.items
if (args && Array.isArray(args.items) && args.items.length) {
  const want = new Set(args.items)
  items = cfg.items.filter(it => want.has(it.id))
  log(`subset: ${items.map(it => it.id).join(', ')}`)
}

// ponytail: verifiers batched to 3, not fired all at once — session token cap trips
// on 6+ concurrent agents (caos-workflow-token-limit). Peak concurrency stays <= 3.
async function verifyInBatches(findings, itemId) {
  const out = []
  for (let i = 0; i < findings.length; i += 3) {
    const slice = findings.slice(i, i + 3)
    const done = await parallel(
      slice.map(f => () =>
        agent(
          `Adversarially REFUTE this ${plan} review finding. Read the actual code at ${f.file}:${f.line} before deciding. ` +
            `Claim (${f.severity}): ${f.summary}. ${f.failure ? 'Alleged failure: ' + f.failure + '. ' : ''}` +
            `Severity inflation is the norm — default refuted=true if the claim does not hold under scrutiny or is adjudicated-accepted. ` +
            `If real, return refuted=false and your own severity.`,
          { label: `verify:${itemId}`, phase: 'Verify', schema: VERDICT_SCHEMA, effort: 'low' },
        ).then(v => ({ ...f, item: itemId, survived: !!v && v.refuted === false, verifiedSeverity: v ? v.severity : null })),
      ),
    )
    out.push(...done.filter(Boolean))
  }
  return out
}

const surviving = []
const auditedIds = []

for (const it of items) {
  if (budget.total && budget.remaining() < 60_000) {
    log(`budget floor hit after ${auditedIds.length}/${items.length} items — stopping clean`)
    break
  }
  phase('Review')
  const review = await agent(
    `Audit CAOS ${plan.toUpperCase()} item ${it.id} under ${cfg.root}. Scope: ${it.scope}. ` +
      `Lenses: ${cfg.lenses}. Use ${cfg.tool} (via ToolSearch) to map symbols and fan-in before judging. ` +
      `Report-only — no code changes. Do NOT flag adjudicated-accepted: ${cfg.adjudicated} ` +
      `Return findings as data (empty array if the item is clean); each with file, line, severity, lens, summary, failure.`,
    { label: `review:${it.id}`, phase: 'Review', schema: FINDINGS_SCHEMA },
  )
  auditedIds.push(it.id)
  if (!review || !review.findings || !review.findings.length) {
    log(`${it.id}: clean (0 raw findings)`)
    continue
  }
  const verified = await verifyInBatches(review.findings, it.id)
  const kept = verified.filter(f => f.survived)
  surviving.push(...kept)
  log(`${it.id}: ${kept.length}/${review.findings.length} findings survived verify`)
}

phase('Synthesize')
const md = await agent(
  `Write ${cfg.matrixFile} (create it, overwrite if present). ` +
    `Section 1: a status table with one row per audited item — columns: item id, status (AUDITED), verified-finding count. ` +
    `Audited item ids: ${JSON.stringify(auditedIds)}. ` +
    `Section 2: a findings table sorted by severity (high first) — columns: severity, item, file:line, lens, summary, failure. ` +
    `Verified findings JSON: ${JSON.stringify(surviving)}. ` +
    `Use the Write tool to save the file, then return the full markdown you wrote so it is recoverable if the write fails.`,
  { label: 'matrix', phase: 'Synthesize' },
)

return {
  plan,
  matrixFile: cfg.matrixFile,
  itemsAudited: auditedIds.length,
  itemsTotal: items.length,
  verifiedFindings: surviving.length,
  markdown: md,
}
