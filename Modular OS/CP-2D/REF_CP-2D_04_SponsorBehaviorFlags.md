<!-- REF_CP-2D_04 (T2) | 2026-06-03 -->
<step_reference module="CP-2D" step="04" name="Sponsor / Shareholder Behavior Flags">
<input>T2D.2, T2D.3; all sponsor action, transaction, distribution, LME, amendment, and support evidence.</input>
<gate>Steps 2–3 complete.</gate>

## Instructions
1. Build a source-backed behavior flag register. Assign sequential Flag IDs (CP-2D-FLAG-001, etc.).
2. For each flag: record Behavior Type (dividend recap / distribution / support / LME / amendment / acquisition / disposal / reporting / other), Documented Action, Behavior Category (Supportive / Neutral / Mixed / Extraction-Oriented / Creditor-Adverse / Insufficient Information per Taxonomy A–E), Amount / Funding Source, Legal-Capacity Link (CP-4 / CP-4C / document / Insufficient Information), Risk Mechanic, Credit Implication, Evidence Quality, Source Trace, Limitation.
3. Cover where supported: dividend recap history, shareholder distributions, management/monitoring/advisory fees, related-party leakage, LME history, priming/uptier/drop-down/non-pro-rata, amendment/waiver/A&E/exchange/restructuring, sponsor equity support/cure/injection/deleveraging, acquisition funding, disposal/asset-sale behavior, open-market repurchases, creditor-aligned or creditor-adverse refinancing, transparency/reporting behavior.
4. Apply Taxonomy categories strictly per evidence; do not infer behavior from sponsor identity.

## Output
T2D.4: `Flag ID`|`Behavior Type`|`Documented Action`|`Behavior Category`|`Amount / Funding Source`|`Legal-Capacity Link`|`Risk Mechanic`|`Credit Implication`|`Evidence Quality`|`Source Trace`|`Limitation`
</step_reference>
