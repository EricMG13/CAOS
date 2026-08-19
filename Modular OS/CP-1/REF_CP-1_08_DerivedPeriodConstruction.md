<!-- REF_CP-1_08_DerivedPeriodConstruction (Tier 2) | 2026-06-02 -->
<step_reference module="CP-1" step="8" name="LTM/YTD/Derived Period Construction">
<input>T4.7 Normalized Financials.</input>
<gate priority="critical">Sub-period data must exist. Missing component → null. Do NOT estimate.</gate>

## Detailed Instructions
1. LTM = Most recent full-year + Current stub − Prior-year comparable stub.
2. YTD constructed where applicable.
3. **Derived Period Rule (CRITICAL):** ALL sub-period components must be available. Missing one = null for entire derived figure.
4. Record all constructions: component sources, formula, calculation status, limitations.
5. Ensure sub-period comparability. Mismatched stubs → Not Comparable.

## Output — T4.8 Constructed Period Register
`Metric Name` | `Derived Period Type` | `Full-Year Component` | `Current Stub` | `Prior-Year Stub` | `Derived Value` | `Calculation Status` | `Source Files` | `Limitations`

## Warnings
- Partial LTM/YTD = **PROHIBITED**. One missing component → entire figure = null.
- Mismatched stub periods → derivation invalid.
</step_reference>
