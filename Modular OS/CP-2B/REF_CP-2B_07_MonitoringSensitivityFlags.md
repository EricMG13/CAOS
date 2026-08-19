<!-- REF_CP-2B_07 (T2) | 2026-06-03 -->
<step_reference module="CP-2B" step="07" name="Monitoring Sensitivity Flags">
<input>Steps 1-6 outputs (especially Step 5 pathway rows)</input>
<gate>Step 6 complete.</gate>

## Instructions
Build monitoring triggers tied to pathway rows from Step 5. Rules:
- Triggers must be observable.
- Quantitative thresholds only if sourced or calculated from sourced inputs.
- If thresholds unsupported: use qualitative signals, state "Quantitative threshold not available in provided materials."
- Every trigger must map to a downside pathway row (CP-2B-DP-###).
- Distinguish leading vs lagging indicators.
- Do not invent management guidance, thresholds, or covenant levels.

See REF_CP-2B_MonitoringIndicatorLibrary.md for suggested leading/lagging indicator lists (27 leading, 12 lagging) and trigger construction rules.

## Output
**T2B.7 Monitoring Sensitivity Flags:** `Trigger ID`|`Indicator`|`Leading / Lagging`|`Threshold or Qualitative Signal`|`Linked Pathway Row`|`Escalation Consequence`|`Source Trace`|`Limitation`
- Trigger ID format: CP-2B-MON-001, CP-2B-MON-002, ...
</step_reference>
