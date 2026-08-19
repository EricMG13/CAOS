<!-- REF_CP-3D_08 (T2) | 2026-06-03 -->
<step_reference module="CP-3D" step="08" name="Creditor Class Exposure and Recovery Implications">
<input>T3D.2–T3D.7; capital structure, legal/structural evidence, path assessment, vulnerability score.</input>
<gate>Step 7 complete.</gate>

## Instructions
1. Map each creditor class to its exposure under the most likely and most adverse refinancing/LME paths.
2. For each creditor class: record Creditor Class (e.g., 1L term loan, 2L notes, unsecured), Exposure Under Base Case, Exposure Under Stress Case, Exposure Under LME Case, Recovery Implication, Priming/Subordination Risk, and Source Trace.
3. Identify which creditor classes are most vulnerable to:
   - Priming (new senior/pari debt ahead)
   - Subordination (uptier leaving non-participants junior)
   - Collateral leakage (asset movement reducing recovery)
   - Non-pro-rata treatment (selective exchange favoring participants)
4. Connect creditor-class exposure to downstream: CP-3B (instrument preference), CP-3C (sizing constraints).
5. Use Evidence → Risk Mechanic → Credit Implication chain.

## Output
T3D.8: `Creditor Class`|`Exposure: Base Case`|`Exposure: Stress Case`|`Exposure: LME Case`|`Recovery Implication`|`Priming / Subordination Risk`|`Source Trace`
