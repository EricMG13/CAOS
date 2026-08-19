<!-- REF_CP-2F_08 (T2) | 2026-06-03 -->
<step_reference module="CP-2F" step="08" name="Macro Sensitivity Summary">
<input>T2F.2–T2F.7; cumulative rate, hedge, FX, commodity, and inflation evidence from all prior steps.</input>
<gate>Steps 2–7 complete.</gate>

## Instructions
1. Build a consolidated macro sensitivity summary table covering all material macro drivers.
2. Drivers may include: base rates, inflation, FX, commodities, energy, wages, freight, demand sensitivity, and hedge cliffs.
3. For each driver: record Evidence, Risk Mechanic, FCF / Liquidity Impact, Refinancing / RV Implication, Monitoring Trigger (use Monitoring Trigger labels where applicable), and Source Trace.
4. Assign one Macro Risk Level: **Low** | **Moderate** | **High** | **Insufficient Information**.
5. Risk Level Guide:
   - **Low:** Source-supported limited exposure or effective mitigation.
   - **Moderate:** Exposure present but mitigants or pass-through evidence partially reduce FCF volatility.
   - **High:** Unsupported or unhedged exposure can materially pressure FCF, liquidity, debt service, covenant headroom, refinancing, recovery, or RV.
   - **Insufficient Information:** Decision-useful classification not supportable.
6. Support the risk level with Evidence → Risk Mechanic → Credit Implication chain.

## Output
T2F.8: `Macro Driver`|`Evidence`|`Risk Mechanic`|`FCF / Liquidity Impact`|`Refinancing / RV Implication`|`Monitoring Trigger`|`Source Trace`
+ Macro Risk Level: [Low / Moderate / High / Insufficient Information]
</step_reference>
