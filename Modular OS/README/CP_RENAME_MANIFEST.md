# CP Rename Manifest — L7 Active Prompt Standardisation
Version: 1.1 | Updated: 08 June 2026
Resolves: Audit L-1
Status: COMPLETED — both L7 prompts renamed to CP-<ID>_ACTIVE_PROMPT.md; all 24 modules now follow the canonical convention. Cross-references (MODULES_REFERENCE_v2, MODULE_EXECUTION_ORDER_v2, SYSTEM_ROUTE_MAP_v2) reference modules by ID, not filename, so no edits were required there.

## Issue
L0–L6 Active Prompts follow the convention: `CP-[ID]_ACTIVE_PROMPT.md`.
L7 Active Prompts use a different convention with embedded canonical names:
- `CP-SR_SectorReview_ActivePrompt.md`
- `CP-MON_CreditPulse_ActivePrompt.md`

## Required Renames

| Current Filename | Standard Filename |
|---|---|
| CP-SR_SectorReview_ActivePrompt.md | CP-SR_ACTIVE_PROMPT.md |
| CP-MON_CreditPulse_ActivePrompt.md | CP-MON_ACTIVE_PROMPT.md |

## Instructions
1. Rename files in Modular OS folder.
2. Update internal cross-references in MODULES_REFERENCE_v2.md, MODULE_EXECUTION_ORDER_v2.md, SYSTEM_ROUTE_MAP_v2.md, EXAMPLE_PATHWAYS_v2.md, and CP_ONBOARDING_DOCUMENTATION_v3.txt.
3. Verify no REF files reference the old filenames.
4. File content remains unchanged — rename only.

## Naming Convention (Canonical)
Pattern: `CP-[ID]_ACTIVE_PROMPT.md`
Examples: `CP-0_ACTIVE_PROMPT.md`, `CP-6A_ACTIVE_PROMPT.md`, `CP-SR_ACTIVE_PROMPT.md`, `CP-MON_ACTIVE_PROMPT.md`
