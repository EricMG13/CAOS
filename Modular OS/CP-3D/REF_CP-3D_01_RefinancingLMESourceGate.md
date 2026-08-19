<!-- REF_CP-3D_01 (T2) | 2026-06-03 -->
<step_reference module="CP-3D" step="01" name="Refinancing / LME Source Gate">
<input>All available source materials: debt schedules, maturity profiles, credit agreements, indentures, CP-1/CP-1A financials, CP-2B downside pathways, CP-2E liquidity bridge, CP-4/CP-4C legal/covenant outputs, CP-2D sponsor evidence, market data, lender presentations, term sheets, rating agency reports.</input>
<gate>Always executes. This IS the gate check. BLOCKING: Minimum maturity/debt-schedule data must be available. If no debt maturity or capital structure data: Module Status = Blocked, STOP.</gate>

## Instructions
1. Catalogue all sources: source_document_id, source_document_name, source_quality, period/date, entity_covered, data_supplied, limitation, downstream_use.
2. Verify minimum evidence: maturity/debt-schedule data available.
3. If no maturity data: Module Status = Blocked, STOP.
4. Assess source quality: governing executed legal documents outrank drafts, summaries, term sheets, posting memoranda, lender presentations, and third-party covenant-review reports.
5. Check availability of each evidence category: maturity/debt schedule, liquidity/FCF, market data, legal/covenant (CP-4/CP-4C), sponsor/governance (CP-2D), downside (CP-2B), liquidity bridge (CP-2E).
6. Flag draft, unsigned, stale, incomplete, or conflicting documents — reduce confidence.
7. Assign Module Status: Full Run / Ready with Limitations / Blocked.

## Output
T3D.1: `source_document_id`|`source_document_name`|`source_quality`|`period / date`|`entity_covered`|`data_supplied`|`limitation`|`downstream_use`
+ Module Status: Full Run / Ready with Limitations / Blocked

<!-- Upstream re-anchor (common_rules #10): at this gate, re-import and verify the specific upstream module outputs this module consumes (CP-1/CP-1A financials, CP-2B downside, CP-2E liquidity bridge, CP-4/CP-4C legal/covenant, CP-2D sponsor) with their run_id/period. If a required upstream value is absent or its run_id/period mismatches this run, mark [Insufficient Information] and gate the dependent step — do not re-derive or infer the upstream value from memory. -->
