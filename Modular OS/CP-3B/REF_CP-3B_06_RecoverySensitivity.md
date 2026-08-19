<!-- REF_CP-3B_06 (T2) | 2026-06-03 -->
<step_reference module="CP-3B" step="06" name="Recovery Sensitivity by Instrument">
<input>T3B.2–T3B.5; CP-4/CP-4C recovery evidence where available.</input>
<gate>Steps 4–5 complete.</gate>

## Instructions
1. Assign a Recovery Sensitivity Label to each instrument:
   - **Low:** Strong priority, collateral/guarantor support, limited senior dilution risk.
   - **Moderate:** Meaningful protection but recovery can move with EV, collateral value, incremental debt, or guarantor changes.
   - **High:** Materially exposed to EV, structural subordination, priming, weak guarantors, or collateral leakage.
   - **Binary / highly uncertain:** Depends on litigation, LME participation, asset transfer, non-pro-rata exchange, or uncertain collateral/guarantor perimeter.
   - **Insufficient Information:** Missing ranking, collateral, guarantor, intercreditor, or recovery data.
2. For each: provide Evidence, Risk Mechanic, Credit Implication, Confidence (using Evidence Confidence Labels), and Source Trace.
3. Use Evidence → Risk Mechanic → Credit Implication chain.
4. Do not infer recovery values unless supported by provided evidence.

## Output
T3B.6: `Instrument`|`Recovery Sensitivity`|`Evidence`|`Risk Mechanic`|`Credit Implication`|`Confidence`|`Source Trace`
</step_reference>
