<!-- CP-3 System Reference (T4) | 2026-06-03 -->

## Identity
module_id: CP-3 | module_name: RelativeValueSecuritySelection | schema_family: Nested | layer: L3

## Dependencies
UP: CP-1, CP-1C, CP-2, CP-2E | DOWN (Analytical): CP-3B, CP-3C, CP-6A, CP-6E | DOWN (Infra): CP-5B, CP-5, CP-RENDER, CP-EXTRACT

## Governance Rules
1. CP-3 is not standalone fundamental underwriting — it relies on CP-1/CP-2 family outputs and converts them into security-selection and RV conclusions.
2. RV conclusions require dated market evidence. Without dated market data, RV = Unclear and recommendation ≠ Preferred.
3. Scores are decision-support tools, not ratings. Missing factor evidence → range, Not Scorable, or Not Assessable.
4. A security may be Preferred only when fundamentals, structure, downside protection, liquidity, refinancing, and market compensation are collectively supportive.
5. Every material conclusion must complete: Evidence → Risk Mechanic → Credit Implication.

## Evidence Hierarchy
Sourced Fact > Calculated Metric > Analyst Inference > Insufficient Information > Unsupported Conclusion

## Execution Modes
CLO Screening | Single-Name RV | Capital-Structure RV | Watchlist Monitoring

## Score Direction
1 (Conservative/creditor-favorable/low-risk) → 5 (Aggressive/creditor-unfavorable/high-risk)

## Score Confidence Tags
High | Medium | Low | Not Assessable

## Credit Tier Mapping
≥1.0 and <2.0 = High Quality | ≥2.0 and <3.0 = Acceptable | ≥3.0 and <3.8 = Stretched | ≥3.8 and ≤5.0 = Weak | Not Scorable
(Bands are continuous and non-overlapping — `<` is exclusive, so 3.79… is Stretched and 3.80 is Weak; the 3.8 split is the investable/reject boundary and no score falls into a gap.)

## Relative-Value Labels
Cheap | Fair | Rich | Unclear

## Recommendation Labels
Preferred | Neutral | Avoid | Requires More Work

## Fail/Restrict
- **Blocked:** Module Status = Blocked when no CP-1/CP-2 or equivalent fundamental evidence is available.
- **Restricted:** Module Status = Ready with Limitations when partial evidence available (e.g., no market data → all RV = Unclear, no legal data → structural/recovery views flagged).
- **Scoring Restricted:** No precise composite score if factor evidence materially incomplete.
- **RV Restricted:** RV = Unclear when dated market data absent; recommendation cannot be Preferred without market evidence.
- **Ranking Restricted:** Avoid forced ranking when evidence insufficient — use Requires More Work.

## Version: 2026-06-03
