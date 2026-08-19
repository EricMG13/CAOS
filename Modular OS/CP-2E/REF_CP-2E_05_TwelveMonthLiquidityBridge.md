<!-- REF_CP-2E_05 (T2) | 2026-06-03 -->
<step_reference module="CP-2E" step="05" name="12-Month Liquidity Bridge">
<input>T2E.2, T2E.3, T2E.4; all beginning liquidity, cash-use, and WC/capex data.</input>
<gate>Steps 2–4 complete.</gate>

## Instructions
1. Build an Excel-ready Markdown table consolidating the 12-month liquidity bridge.
2. Required rows: Beginning cash, Accessible revolver availability, Beginning accessible liquidity, Operating cash inflow/outflow, Working-capital impact, Cash interest, Cash taxes, Mandatory capex, Debt amortization/maturities, Other cash uses, Ending accessible liquidity.
3. For each row: record Amount, Source / Calculation basis, Status (use Liquidity Data Status Labels), Credit Comment, and Source Trace.
4. Use Python for all bridge arithmetic.
5. Ending accessible liquidity = Beginning accessible liquidity + operating cash inflow/outflow + WC impact − cash interest − cash taxes − mandatory capex − debt amortization/maturities − other cash uses + committed inflows (source-supported).
6. Flag any row where status is Provisional, Management-guided, or Analyst estimate.

## Output
T2E.5: `Bridge Item`|`Amount`|`Source / Calculation`|`Status`|`Credit Comment`|`Source Trace`
</step_reference>
