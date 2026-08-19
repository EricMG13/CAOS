<!-- REF_CP-3B_05 (T2) | 2026-06-03 -->
<step_reference module="CP-3B" step="05" name="Legal / Covenant and LME Overlay">
<input>T3B.4; CP-4/CP-4C outputs (priming, leakage, weak collateral, covenant weakness); CP-3D outputs (refinancing/LME vulnerability).</input>
<gate>Step 4 complete. Skip with [Insufficient Information] if no legal/covenant or CP-4/CP-4C/CP-3D data available.</gate>

## Instructions
1. Overlay legal, covenant, and LME findings onto the structural positioning.
2. If CP-4/CP-4C identify priming, leakage, weak collateral, or covenant weakness: carry into structural and recovery assessment per instrument.
3. If CP-3D identifies refinancing or LME vulnerability: identify the exposed creditor class.
4. For each instrument: record Legal/Structural Finding, Priming Risk, Leakage Risk, Weak Collateral flag, Covenant Weakness flag, LME Vulnerability, Exposed Creditor Class, Source (CP-4/CP-4C/CP-3D reference), and Source Trace.
5. Flag instruments where legal review is unavailable — note impact on confidence.

## Output
T3B.5: `Instrument`|`Legal / Structural Finding`|`Priming Risk`|`Leakage Risk`|`Weak Collateral`|`Covenant Weakness`|`LME Vulnerability`|`Exposed Creditor Class`|`Source (CP-4 / CP-4C / CP-3D)`|`Source Trace`
</step_reference>
