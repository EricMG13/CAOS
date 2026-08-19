<!-- REF_CP-3D_03 (T2) | 2026-06-03 -->
<step_reference module="CP-3D" step="03" name="Liquidity, FCF, and Market Access Assessment">
<input>T3D.1, T3D.2; CP-1/CP-1A financials, CP-2E liquidity bridge, market data (pricing/spreads/yields).</input>
<gate>Step 2 complete.</gate>

## Instructions
1. Assess liquidity position: cash, revolver availability, revolver draw status, other liquidity sources.
2. Assess FCF generation: current and projected, cash interest burden, capex requirements.
3. Assess market access: current trading levels (price/spread/yield), distressed trading flag, rating/outlook, market appetite for issuer/sector.
4. For each dimension: record Factor, Evidence, Current Level/Status, Direction (using Probability Direction Labels), Risk Mechanic, Credit Implication, Confidence, and Source Trace.
5. If current market data is missing: mark conclusions as [Market Data Not Provided] or [Insufficient Information].
6. Flag negative FCF/cash burn, high cash interest burden, distressed trading, revolver draw, ratings downgrade/negative outlook.

## Output
T3D.3: `Factor`|`Evidence`|`Current Level / Status`|`Direction`|`Risk Mechanic`|`Credit Implication`|`Confidence`|`Source Trace`
