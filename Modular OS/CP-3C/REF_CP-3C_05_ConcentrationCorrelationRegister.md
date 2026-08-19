<!-- REF_CP-3C_05 (T2) | 2026-06-03 -->
<step_reference module="CP-3C" step="05" name="Concentration and Correlation Register">
<input>T3C.1 (holdings/exposure data), T3C.3 (sizing posture); concentration reports, mandate limits.</input>
<gate>Step 4 complete. If concentration data unavailable, populate with null and flag in Gaps Ledger.</gate>

## Instructions
1. Assess concentration and correlation across 7 exposure dimensions:
   - Issuer / group
   - Sector / subsector
   - Sponsor / ownership
   - Rating bucket
   - Maturity year / wall
   - Capital-structure layer
   - Correlated holdings / common factor
2. For each dimension: record Current Exposure, Proposed/Pro Forma Exposure, Limit/Capacity, Evidence Status (Source Fact / Calculation / Not Provided), Risk Mechanic, Portfolio Implication, and Source Trace.
3. Use null for unavailable numeric values — do not leave unexplained blanks.
4. If proposed size is provided, calculate pro forma exposure where data supports.
5. Flag dimensions where concentration exceeds or approaches limits.

## Output
T3C.5: `Exposure Dimension`|`Current Exposure`|`Proposed / Pro Forma Exposure`|`Limit / Capacity`|`Evidence Status`|`Risk Mechanic`|`Portfolio Implication`|`Source Trace`
</step_reference>
