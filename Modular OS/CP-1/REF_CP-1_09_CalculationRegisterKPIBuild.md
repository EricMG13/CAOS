<!-- REF_CP-1_09_CalculationRegisterKPIBuild (Tier 2) | 2026-06-02 -->
<step_reference module="CP-1" step="9" name="Calculation Register & KPI Build">
<input>T4.7 Normalized Financials + T4.8 Constructed Period Register.</input>
<gate>Normalized data available for at least some periods.</gate>

## Detailed Instructions
1. Calculate all canonical KPIs where inputs available:
   - **Leverage:** Debt/EBITDA, Net Debt/EBITDA, Sr Sec/EBITDA
   - **Coverage:** EBITDA/Cash Int, (EBITDA−Capex)/Cash Int, FFO/Debt
   - **Cash Flow:** FCF, FCF Conversion (FCF/EBITDA), DCF
   - **Liquidity:** Cash+Undrawn Committed, Liquidity/Debt
   - **Margin:** Gross %, EBITDA %, EBIT %, Net Income %
   - **Growth:** Revenue %, EBITDA %
2. Full audit trail per KPI: name, formula, numerator (value+source), denominator (value+source), period, currency, unit, value, calc status, evidence tier, limitations.
3. Calculation status (8 values): `Verified` | `Calculated` | `Estimated` | `Proxy` | `Not Calculable` | `Partial` | `Conflicted` | `Not Available`
4. Populate KPI Dashboard with trend direction and analyst notes.

## Output — T4.9 Calculation Register
`Metric Name` | `Formula` | `Numerator Value` | `Numerator Source` | `Denominator Value` | `Denominator Source` | `Period` | `Currency` | `Unit` | `Calculated Value` | `Calculation Status` | `Evidence Quality Tier` | `Limitations`

## Output — T4.10 KPI Dashboard
`KPI Category` | `Metric Name` | `Period 1…N` | `Trend Direction` | `Analyst Note`

## Warnings
- Null input → KPI = Not Calculable. Do NOT estimate missing inputs.
- Use only canonical 8-value calculation status.
</step_reference>
