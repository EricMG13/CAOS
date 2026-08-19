# REF_CP-EMAIL — Canonical Location & Deduplication Manifest
Version: 1.0 | Updated: 08 June 2026
Resolves: Audit M-5

## Canonical File
**Name:** `REF_CP-EMAIL_SourceRoutingMatrix.md`
**Canonical Location:** `/Modular OS/References/REF_CP-EMAIL_SourceRoutingMatrix.md`

## Problem
15+ duplicate copies of this file exist across different SharePoint locations.
Only the canonical copy above should be referenced by Active Prompts.

## Deduplication Rules
1. All Active Prompts referencing this file MUST use the canonical path above.
2. Duplicate copies in other locations should be deleted after confirming no Active Prompt references the non-canonical path.
3. Future updates MUST be made to the canonical copy only.

## Affected Modules
- CP-SR (SectorReview) — Step A.2
- CP-MON (CreditPulse) — Step A
- CP-0 (SourceReadiness) — email source classification
- CP-1A (BusinessTransactionFactPack) — supplementary email evidence
- CP-2C (EventCatalystRegister) — event-driven email signals
- CP-2B (DownsidePathway) — distress signals via email
- CP-4 (LegalCovenantInterpreter) — amendment/waiver notifications
- CP-5 (ResearchIntegrityQA) — email source audit lane

## Action Required
- [ ] Verify canonical path exists
- [ ] Update all Active Prompt REF references to canonical path
- [ ] Delete non-canonical duplicates
- [ ] Confirm via CP-5 audit lane
