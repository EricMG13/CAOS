<!-- REF_CP-1C_ValuationAndOutlierRules (T2 Library) | 2026-06-10 | Restored from CP-1C__SUPPORT__Metric_Alignment_Calculation_Outlier_and_Valuation_Rules §2.6.3, 2.7.3–2.7.4, 2.8, 2.9.5 -->
<library_reference module="CP-1C" name="Valuation and Outlier Rules">
<consumers>REF_CP-1C_03 (Metric Alignment); REF_CP-1C_05 (Outlier Register); REF_CP-1C_06A/06B/06C (Comps & Implied EV)</consumers>

# CP-1C Valuation and Outlier Rules

## Non-Comparability Triggers (9)
The following situations trigger Not Comparable or Comparable with Limitations:
1. Different EBITDA definitions (reported vs adjusted vs credit-agreement) without reconciliation.
2. Different FYE alignment without period adjustment.
3. IFRS vs US GAAP treatment of leases, pensions, or intangibles without adjustment.
4. Currency mismatch without exchange-rate disclosure.
5. Different leverage definition (gross vs net, total vs senior) without reconciliation.
6. Perimeter difference (consolidated vs restricted group vs guarantor group).
7. Peer data more than 12 months older than borrower data without disclosure.
8. Different capex classification (maintenance vs growth vs total).
9. Peer metric calculated from insufficient source data.

## Outlier Rules
- Apply outlier classification to both borrower and peers. If the borrower is an outlier among its peer group, flag it prominently and state the credit implication.
- Quantify outlier materiality: state the datapoint, the peer range (min, max, median, average where available), and the magnitude of the deviation.
- Do not dismiss outliers without credit-relevant explanation. Assess whether the outlier reflects (a) genuine operational difference, (b) data-quality issue, (c) comparability misalignment, or (d) one-off event.
- If an outlier distorts peer statistics, recalculate the statistic excluding the outlier and show both versions.
- Outlier classification must be consistent across periods. If outlier status changes between periods, flag the change and the credit implication.
- Where an outlier results from a known comparability limitation (different definition, accounting standard, or perimeter), classify it as Non-Comparable rather than Favorable or Unfavorable.

## Enterprise Value Formula
EV = Equity Value (market cap or transaction equity value) + Total Debt + Minority Interests + Preferred Equity − Cash & Cash Equivalents − Short-Term Investments (if liquid and available).
State the EV formula explicitly. If any component is estimated or unavailable, flag the limitation.

## Implied EV Formulas
- Implied EV from EV/EBITDA = Peer EV/EBITDA multiple × Borrower EBITDA.
- Implied EV from EV/Revenue = Peer EV/Revenue multiple × Borrower Revenue.
- Implied EV from Transaction EV/EBITDA = Transaction multiple × Borrower EBITDA.
- Implied EV from Transaction EV/Revenue = Transaction multiple × Borrower Revenue.
- Implied EV Range: Low = minimum peer multiple × borrower metric; Median = median peer multiple × borrower metric; High = maximum peer multiple × borrower metric.

Each implied-EV calculation must state: the multiple source, the borrower metric used, the period, the definition, and the calculation status.

## Valuation Discipline (12 Points)
1. All multiples must be sourced, with source file and date stated.
2. All multiples must use the same metric definition as the borrower metric they are compared against, or the definition difference must be flagged.
3. Stale multiples (more than 12 months old) must be labelled as such.
4. Transaction multiples must state transaction date, transaction type, buyer/seller, and perimeter.
5. Public-company multiples must state the market-cap date and the financial period used for the denominator.
6. Do not average multiples from non-comparable entities.
7. Do not present implied EV without stating all assumptions and limitations.
8. Do not present implied EV as a recovery estimate or debt-coverage conclusion — that belongs to CP-4 / CP-4C.
9. Implied EV calculations are indicative context, not definitive valuations.
10. If the borrower is private and no equity value is available, state the limitation and use implied-EV methods only.
11. Currency must be consistent across all valuation calculations, or exchange rates disclosed.
12. Sector multiples require a minimum of 3 comparable datapoints to be meaningful.

## Valuation Calculation Constraints
- EV/EBITDA and EV/Revenue must use the same-period EBITDA and Revenue as the borrower comparison basis.
- Transaction multiples must use the EBITDA or Revenue figure contemporaneous with the transaction date.
- Do not blend trading multiples and transaction multiples in the same average or median without flagging.

## Numeric Hygiene
- Percentages: decimals or percentage notation, consistent throughout the module.
- Multiples: Nx format (e.g., 5.2x).
- Currency stated for every absolute figure.
- Rounding matches the precision established by CP-1 or the peer source.
- Null handling: if any input to a formula is null, the result is null — not zero, not estimated.

## Label Taxonomies (closed sets — use only these values)
- **Comparability Status** (REF_CP-1C_03 `Comparability Status`): `Comparable` | `Comparable with Limitations` | `Not Comparable` | `Insufficient Information`.
- **Calculation Status** (any computed peer/borrower metric): `Reported` | `Calculated` | `Derived` | `Provisional` | `Not Comparable` | `Insufficient Information`.
- **Outlier Direction** (REF_CP-1C_05 `Direction`, the "5 labels"): `Favorable` | `Unfavorable` | `Mixed` | `Non-Comparable` | `Insufficient Information`.
  - Where an outlier arises from a comparability limitation (definition / accounting standard / perimeter), classify `Non-Comparable`, not `Favorable`/`Unfavorable`.
  - Each outlier maps to the 6 credit-translation dimensions in REF_CP-1C_05's output: operating, cash-flow, leverage/liquidity, refinancing, valuation-context, and downstream handoff.

## 11-Point Metric Alignment Standard (AP1–AP11, REF_CP-1C_03)
Every planned comparison records: AP1 borrower definition · AP2 peer definition · AP3 source period ·
AP4 currency · AP5 accounting basis (IFRS/US GAAP) · AP6 actual vs pro forma basis · AP7 reported vs
adjusted basis · AP8 LTM/YTD/quarterly/annualized basis · AP9 source quality / provenance · AP10
normalization treatment · AP11 resulting comparability status. Any unbridged mismatch on AP1–AP10
drives AP11 to `Not Comparable` or `Comparable with Limitations`.

## Peer Statistic Rules
Do not calculate average, median, quartile, range, standard deviation, or percentile unless sufficient
comparable datapoints exist (minimum 2 for any "range"/"average" label; minimum 3 for a meaningful
sector multiple). Exclude non-comparable datapoints from summary statistics and state why. Do not rank
the borrower where the peer set is incomplete or definitions differ materially.
</library_reference>
