<!-- REF_CP-2E_02 (T2) | 2026-06-03 -->
<step_reference module="CP-2E" step="02" name="Beginning Liquidity Register">
<input>T2E.1 Source Register; cash balance, revolver, and committed-facility source materials.</input>
<gate>Step 1 complete; Module Status ≠ Blocked.</gate>

## Instructions
1. Build the beginning accessible liquidity register using permitted Liquidity Component labels.
2. Include: cash, restricted cash, revolver commitment, undrawn revolver, accessible revolver capacity (after borrowing-base/covenant constraints), and other committed liquidity where disclosed.
3. For each component: record Source-Supported Amount, Accessibility Status, Source Trace, Limitation / Restriction, Risk Mechanic, and Credit Implication.
4. Distinguish reported cash from accessible liquidity. Distinguish committed available revolver from inaccessible or covenant-constrained capacity.
5. Do not assume undrawn revolver availability is accessible unless disclosed. Restricted cash excluded unless source explicitly confirms availability.
6. Calculate Beginning Accessible Liquidity = Cash + Accessible Revolver + Other Committed Accessible Liquidity.

## Output
T2E.2: `Liquidity Component`|`Source-Supported Amount`|`Accessibility Status`|`Source Trace`|`Limitation / Restriction`|`Risk Mechanic`|`Credit Implication`
</step_reference>
