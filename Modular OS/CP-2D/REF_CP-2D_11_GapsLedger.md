<!-- REF_CP-2D_11 (T2) | 2026-06-03 -->
<step_reference module="CP-2D" step="11" name="Gaps Ledger">
<input>All prior step outputs (T2D.1–T2D.10); cumulative gaps identified throughout workflow.</input>
<gate>Always executes.</gate>

## Instructions
1. Compile all gaps identified across Steps 1–10 into a consolidated ledger with sequential Gap IDs (CP-2D-GAP-001, etc.).
2. For each gap: record Missing Data, Why It Matters (credit relevance), Affected Section / Flag / Export Record, Consequence for Confidence (High / Medium / Low impact), Required Follow-Up Source.
3. Cover gaps in: ownership percentage, sponsor fund vintage / life-left, sponsor economics, equity contribution, dividend / distribution history, related-party payments, management fees, acquisition funding, amendment history, LME / restructuring history, board / control rights, governance documents, covenant reporting, basket usage, disclosure cadence, debt schedule, liquidity / revolver availability, maturity wall, legal capacity for RP / investments / debt / liens / asset transfers / unrestricted subsidiaries / priming / amendments.
4. Use Required Follow-Up Question Bank where relevant:
   - What is the current ownership percentage by sponsor / shareholder?
   - What is the sponsor fund vintage and remaining fund life?
   - What was the sponsor equity contribution at transaction close?
   - Has the issuer completed dividend recaps or shareholder distributions? Amount, timing, funding source?
   - What related-party, management, advisory, monitoring, transaction, or shareholder fees are paid?
   - What acquisitions have been completed, and how were they funded?
   - Has the issuer required covenant waivers, amendments, A&E, exchange offers, or restructuring?
   - Has the sponsor provided equity support, cure, deleveraging capital, or liquidity support?
   - What board / consent / veto rights does the sponsor or shareholder hold?
   - What reporting package is provided to lenders and how frequently?
   - Are compliance certificates, debt schedules, maturity schedules, liquidity schedules, and basket-usage trackers available?
   - Does CP-4C identify RP, investment, debt, lien, unrestricted-subsidiary, asset-transfer, priming, or amendment capacity?
   - Has any unrestricted-subsidiary, drop-down, priming, collateral-release, or non-pro-rata mechanism been used?

## Output
T2D.11: `Gap ID`|`Missing Data`|`Why It Matters`|`Affected Section / Flag / Export Record`|`Consequence for Confidence`|`Required Follow-Up Source`
</step_reference>
