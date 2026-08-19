<!-- REF_CP-3C_03 (T2) | 2026-06-03 -->
<step_reference module="CP-3C" step="03" name="Position Sizing Posture Table">
<input>T3C.1, T3C.2; SUPPORT__Position_Sizing_and_Risk_Budget.txt rules.</input>
<gate>Step 2 complete.</gate>

## Instructions
1. Assign sizing posture per issuer/security using Sizing Posture Taxonomy: Avoid / Watchlist / Starter Position / Core Hold / Hold Existing Only / Reduce / Trim / Requires More Work.
2. Apply Minimum Evidence for Core: all 7 items required. If any missing, Core may not be assigned unless labelled as hypothetical framework-only view.
3. Apply Starter Conditions: CP-3 favourable/conditional, downside identifiable, mandate data not clearly adverse, liquidity allows exit.
4. Sizing posture must be explicitly linked to evidence via Evidence → Risk Mechanic → Portfolio Implication.
5. If portfolio constraints are missing, do not express a numeric size unless user provided one.
6. If a proposed size is provided, test it against concentration, liquidity, downside, and mandate constraints.
7. Assign Confidence: High / Medium / Low / Not Assessable.

## Output
T3C.3: `Name / Instrument`|`Sizing Posture`|`Evidence`|`Reason`|`Key Risk`|`Implementation Note`|`Confidence`|`Source Trace`
</step_reference>
