<!-- REF_CP-2B_05 (T2) | 2026-06-03 -->
<step_reference module="CP-2B" step="05" name="Downside Pathway Register">
<input>Steps 1-4 outputs</input>
<gate>Step 4 complete.</gate>

## Instructions
Build the issuer-specific deterioration path using the 11 Standard Pathway Labels (see Active Prompt). Required pathway categories:
- First break point
- EBITDA/margin deterioration
- FCF conversion pressure
- Liquidity consumption
- Leverage/covenant/market-access deterioration
- Refinancing/maturity-wall risk
- PD/RV/security-selection consequence
- LGD/recovery consequence (where source-supported)
- Monitoring consequence

## Output
**T2B.5 Downside Pathway Register:** `Pathway Row ID`|`Pathway Category`|`Driver`|`Causal Vector`|`PD/LGD/RV/Monitoring Consequence`|`Source Trace`|`Confidence`|`Downstream Module`
- Row ID format: CP-2B-DP-001, CP-2B-DP-002, ...
- Confidence: High / Medium / Low / Not Assessable
</step_reference>
