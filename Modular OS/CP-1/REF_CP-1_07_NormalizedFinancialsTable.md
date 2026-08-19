<!-- REF_CP-1_07_NormalizedFinancialsTable (Tier 2) | 2026-06-02 -->
<step_reference module="CP-1" step="7" name="Normalized Financials Table">
<input>T4.4 IS + T4.5 CFS + T4.6 BS.</input>
<gate>At least one of Steps 4–6 produced data.</gate>

## Detailed Instructions
1. Produce consolidated cross-statement table — IS, CFS, BS across all periods.
2. All figures on Step 3 normalization basis. No re-extraction from sources.
3. Consolidation only — no new data, no modifications.
4. Cross-check internal consistency:
   - Net Income (IS) vs. equity movements (BS)
   - Operating + investing + financing → Net Change in Cash (CFS)
   - Opening vs. closing BS positions vs. period flows
   - Flag material reconciliation differences as gaps

## Output — T4.7 Normalized Financials
`Line Item` | `Statement Source` (IS/CFS/BS) | `Period 1` … `Period N`

## Warnings
- Figures must match Steps 4–6 exactly. Discrepancy = normalization error.
- Cross-statement reconciliation failures → log with materiality assessment.
</step_reference>
