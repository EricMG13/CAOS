# Handoff: Sector RV Review Fixes

## Objective
Implement the reviewed Sector RV cleanup pass in the existing Command Center surface. Keep the diff small: mostly `caos/frontend/src/components/command/SectorRV.tsx` and `caos/frontend/src/components/command/SectorRV.test.tsx`; avoid touching `rvdata.ts` unless a test proves it is necessary.

## Current State
- Current tree was clean in the prior session.
- GitNexus CLI reported index up to date at `HEAD` `89b88bc`; MCP registry may show a stale cached commit.
- Existing code already has broader RV pieces: `buildRVRows`, benchmark provenance, instrument/portfolio RV fields, compound RV chip, carry RV, and cross-sector heatmap.
- Prior gates: `tsc` passed, `SectorRV.test.tsx` passed, `rvdata.test.ts` passed. ESLint failed on explicit `any` in `SectorRV.test.tsx:25` and warned on unused `i` in `SectorRV.tsx:390`.

## Implementation Plan
1. Run required pre-edit checks:
   - Use GitNexus `impact` before editing `SectorRV`, `CrossSectorHeatmap`, `DeltaCell`, and any touched helper.
   - If impact is high/critical, stop and report before editing.

2. Fix evidence honesty:
   - Change `EvidenceBadge` to accept `row: RVRow`.
   - Peer tick: `✓` only when `row.rvProvenance` exists; otherwise `◯`.
   - Recovery tick remains `◯` with “recovery/LGD not in feed”.
   - Update the peer-table call site from `<EvidenceBadge />` to `<EvidenceBadge row={r} />`.

3. Replace static caveat strings with a tiny honesty helper:
   - Prefer a new `caos/frontend/src/lib/command/rvCaveat.ts` if tests need direct coverage.
   - Export minimal helpers/state for `kind`, `asOf`, `staleness`, `posture`, and `postureSource`.
   - For now: `kind = SEED-REF`, `asOf = 2026-07-06`, posture is derived/not CP-SR, staleness is current for 0-90 days.
   - Do not wire a live endpoint or CP-SR.

4. Finish Steps 5-7 from the handoff:
   - `DeltaCell`: numeric cells keep column-contextual `aria-label`; null cells render `—` without `aria-label`.
   - `CrossSectorHeatmap`: sort sectors by median RV descending across visible buckets, then sector name ascending; keep bucket order fixed.
   - Heatmap caption: show “filters not applied” only when column filters are active.
   - Right-column wrapper: add `max-h-[360px] overflow-hidden`.
   - Update peer table caption to `sorted |rvBp| ↓`.

5. Fix lint-only issues:
   - Replace explicit `any` in test ResizeObserver stub with a concrete callback type.
   - Remove or rename unused `i` in `sorted.map`.

## Tests
Run from `caos/frontend`:

```bash
npx eslint src/components/command/SectorRV.tsx src/components/command/SectorRV.test.tsx
npx tsc --noEmit
npx vitest run src/components/command/SectorRV.test.tsx
npx vitest run src/lib/command/rvdata.test.ts
```

Add or update tests for:
- Evidence ticks show peer `◯` when `rvProvenance` is absent.
- Caveat helper/state renders `SEED-REF`, derived/not CP-SR posture, current staleness, and as-of date.
- Delta null cells do not get `aria-label`; numeric delta cells do.
- Heatmap caption switches when filters are active.
- Heatmap sector ordering follows median RV descending.
- Right column contains `max-h-[360px] overflow-hidden`.

## Constraints
- No new dependencies.
- Preserve one-universe invariant: scatter, table, sector read, and top-of-book derive from `filtered`; heatmap intentionally uses the full universe.
- Keep deterministic reads only. No LLM prose.
- Do not fabricate recovery/LGD.
- Keep the diff boring and small.
