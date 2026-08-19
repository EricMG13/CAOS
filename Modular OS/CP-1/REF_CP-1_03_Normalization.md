<!-- REF_CP-1_03_Normalization (Tier 2) | 2026-06-02 -->
<step_reference module="CP-1" step="3" name="Normalization">
<input>T4.1 + T4.2 + raw financial data from sources.</input>
<gate>Source data available for at least one period.</gate>

## Detailed Instructions
1. Establish canonical basis: single currency (with FX rates + source), single unit, single perimeter, single accounting basis.
2. Record every adjustment: what, source file, type, before/after, rationale, affected periods.
3. Flag incomplete normalization — carry figure with limitation marker.
4. Once established, basis applies to ALL subsequent steps. Currency/unit switching = **prohibited**.

## Output — T4.3 Normalization Register
`Adjustment Description` | `Source File` | `Adjustment Type` | `Before Value` | `After Value` | `Rationale` | `Affected Periods`

## Warnings
- Currency/unit switching after normalization is **PROHIBITED**.
- Unresolvable accounting basis differences must be flagged, not silently chosen.
</step_reference>
