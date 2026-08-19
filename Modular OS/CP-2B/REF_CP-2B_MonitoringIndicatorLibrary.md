<!-- REF_CP-2B_MonitoringIndicatorLibrary (T2 Library) | 2026-06-10 | Restored from CP-2B__SUPPORT__Workflow_Monitoring_and_Handoff_Rules §1–3 -->
<library_reference module="CP-2B" name="Monitoring Indicator Library">
<consumers>REF_CP-2B_07 (Monitoring Sensitivity Flags); CP-MON signal extraction; CP-SR early warning dashboard</consumers>

# CP-2B Monitoring Indicator Library

Suggested leading and lagging indicators for monitoring-trigger construction. Use only where relevant and source-supported.

## Trigger Construction Rules
- Triggers must be observable.
- Quantitative thresholds may be used only if sourced or calculated from sourced inputs.
- If thresholds are unsupported, use qualitative escalation signals and state: "Quantitative threshold not available in provided materials."
- Every trigger must map to a downside pathway row (CP-2B-DP-###).
- Distinguish leading indicators from lagging indicators.
- Every trigger must identify source_trace, observation frequency where source-supported, evidence basis, pathway linkage, and escalation consequence.
- Do not invent management guidance, thresholds, or covenant levels.

## Suggested Leading Indicators (27)
1. Order intake / bookings decline
2. Backlog conversion deterioration
3. Churn / retention weakening
4. NRR deterioration
5. Volume softness
6. Utilization decline
7. Price concessions or discounting
8. Gross margin compression
9. Input-cost inflation without pass-through
10. Labour / wage inflation without productivity offset
11. Mix shift toward lower-margin product, segment, customer, or geography
12. Receivables days increasing
13. Inventory build
14. Payables normalization / unwind
15. Deferred revenue reversal
16. Capex running above maintenance needs
17. Restructuring / integration cash costs above plan
18. Cash interest increase
19. Revolver draw
20. Cash balance decline
21. Restricted cash / trapped cash increase
22. Covenant headroom erosion
23. Refinancing delay
24. Spread widening / price decline
25. Rating outlook downgrade / negative watch
26. Sponsor dividend, acquisition, amendment, A&E, or LME-related action
27. Weakening disclosure, delayed reporting, or repeated one-off adjustments

## Suggested Lagging Indicators (12)
1. Revenue decline
2. EBITDA decline
3. EBITDA margin decline
4. FCF conversion decline
5. Negative FCF
6. Liquidity reduction
7. Leverage increase
8. Coverage deterioration
9. Covenant breach or waiver
10. Rating downgrade
11. Failed refinancing
12. Distressed exchange, A&E, or LME execution

## Output Control
- If a trigger is direction-only, state [Directional Only] and do not imply precision.
- If a trigger is assumption-based, label it [Analyst Inference] and explain what source evidence supports the inference.
- If evidence is missing, do not backfill with sector generic assumptions; log the gap.
</library_reference>
