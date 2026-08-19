<!-- REF_CP-1C_05 (T2) | 2026-06-02 -->
<step_reference module="CP-1C" step="05" name="Outlier Register">
<input>T4.3-T4.6</input>
<gate>Sufficient peer data</gate>

## Instructions
Apply outlier logic per the Outlier Rules in REF_CP-1C_ValuationAndOutlierRules.md. Per outlier: entity, metric, value, peer range, deviation, direction (5 labels), credit translation (6 dimensions). If borrower outlier → flag prominently. Comparability-caused → Non-Comparable.

Additional rules: quantify deviation magnitude against the peer range; assess cause (operational difference / data quality / comparability misalignment / one-off event); if an outlier distorts peer statistics, recalculate excluding it and show both versions; flag outlier-status changes across periods with credit implication.

## Output
T4.7: `Entity`|`Metric`|`Value`|`Peer Range (Min/Max/Med/Avg)`|`Deviation`|`Direction`|`Operating Impl`|`CF Impl`|`Lev/Liq Impl`|`Refi Impl`|`Valuation Impl`|`Downstream Handoff`
</step_reference>
