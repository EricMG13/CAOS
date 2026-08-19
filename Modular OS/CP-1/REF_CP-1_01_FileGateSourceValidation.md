<!-- REF_CP-1_01_FileGateSourceValidation (Tier 2) | 2026-06-02 -->
<step_reference module="CP-1" step="1" name="File Gate & Source Validation">
<input>User-provided source files + CP-0 registry (if available).</input>
<gate priority="critical">No financial sources → **BLOCKED.** Do not proceed.</gate>

## Detailed Instructions
1. Inventory all source files: name, type, period coverage, currency, unit, perimeter, accounting basis, evidence quality tier.
2. Evidence hierarchy: Tier 1 (Audited FS) > 2a (Unaudited w/ auditor) > 2b (w/o) > 2c (Lender/sponsor) > 2d (Rating) > 3a (Internal) > 3b (External).
3. Assess material sufficiency for IS + CFS + BS + KPIs. Flag downstream impact if insufficient.
4. Record analytical use and limitations per source.
5. Source-first discipline: complete before any extraction.

## Output — T4.1 Source Register
`Source File Name` | `Document Type` | `Period Coverage` | `Currency` | `Unit` | `Perimeter` | `Accounting Basis` | `Evidence Quality Tier` | `Analytical Use` | `Limitations`

## Warnings
- Do NOT classify from filenames alone — inspect content.
- Do NOT proceed if no financial sources available.
</step_reference>
