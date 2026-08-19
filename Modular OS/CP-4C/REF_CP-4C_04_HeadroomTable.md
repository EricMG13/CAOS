<!-- REF_CP-4C_04 (T2) | 2026-06-03 -->
<step_reference module="CP-4C" step="04" name="Headroom Table">
<input>T4C.2, T4C.3; maintenance/incurrence test provisions; CP-1 financial inputs; compliance certificates.</input>
<gate>Step 3 complete.</gate>

## Instructions
1. Build the Headroom Table for all identified covenant tests.
2. For max-ratio tests: headroom = covenant threshold − current tested ratio. Identify ratio distance to breach and, where supportable, incremental debt/EBITDA decline implied by threshold.
3. For min-ratio tests (coverage): headroom = current tested ratio − covenant threshold. Identify cushion to minimum.
4. If exact headroom unsupported, state [Insufficient Information] and identify whether the missing item is: current tested ratio, covenant definition, denominator, numerator, threshold, or basket usage.
5. Apply Calculation Rules: use governing legal definitions, not reported EBITDA.
6. Apply null-handling: Not Available / Provisional / Insufficient Information as appropriate.
7. Include status and limitation for each test.

## Output
T4C.4: `Test`|`Test Type`|`Threshold`|`Current Basis`|`Formula`|`Headroom`|`Status`|`Limitation`|`Risk Mechanic`|`Credit Implication`|`Evidence ID`
</step_reference>
