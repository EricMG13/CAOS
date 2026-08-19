<!-- REF_CP-3C_09 (T2) | 2026-06-03 -->
<step_reference module="CP-3C" step="09" name="Gaps Ledger">
<input>All prior step outputs (T3C.1–T3C.8); cumulative gaps identified throughout workflow.</input>
<gate>Always executes.</gate>

## Instructions
1. Compile all gaps identified across Steps 1–8 into a consolidated ledger.
2. For each gap: record Gap ID (CP-3C-GAP-NNN), Missing Data, Why It Matters (portfolio relevance), Affected Sizing/Risk Budget/Trigger, Consequence for Confidence (High/Medium/Low impact), and Required Follow-Up Source.
3. Cover gaps in: mandate fit, current exposure, pro forma exposure, concentration capacity, sector/rating limits, liquidity, market date, downside loss budget, recovery, legal/covenant constraints, refinancing/LME risk, and implementation feasibility.
4. Flag gaps that prevent sizing posture assignment or force Requires More Work.

## Output
T3C.9: `Gap ID`|`Missing Data`|`Why It Matters`|`Affected Sizing / Risk Budget / Trigger`|`Consequence for Confidence`|`Required Follow-Up Source`
</step_reference>
