<!-- REF_CP-1_05_CashFlowStatementCoverage (Tier 2) | 2026-06-02 -->
<step_reference module="CP-1" step="5" name="Cash Flow Statement Coverage">
<input>Normalized source data (Step 3 basis).</input>
<gate>Always executes. If CFS unavailable, produce empty table + log gaps.</gate>

## Detailed Instructions
1. Extract + normalize full CFS for every available period.
2. Required line items:
   OCF (before/after WC) | WC Change | Capex (Maint/Growth/Total) | FCF (Levered/Unlevered) | Dividends | Acquisitions | Disposals | Debt Issuance/Repayment | Equity Issuance/Buyback | Net Cash Change | Cash Taxes Paid | Cash Interest Paid
3. Same source-tracing and null-storage rules as Step 4.

## Output — T4.5 Cash Flow Statement
`Line Item` | `Period 1` … `Period N`

## Warnings
- Capex split rarely disclosed. Null for sub-categories; carry Total Capex. Flag CP-2 impact.
- Cash Interest Paid (CFS) may differ from Interest Expense Cash (IS). Distinguish carefully.
</step_reference>
