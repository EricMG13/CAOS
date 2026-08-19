# REF_CP-MON_C — Signal Extraction
# Version: 1.1 | 2026-06-10 | Signal quality rules added (from CP-2B monitoring standard)

Convert payloads into factual Signal objects. XBRL maps to canonical metrics. HTML/PDF cleaned into claims. Market thresholds: spread +25bps 1d/+75bps 30d; CDS +30bps 1d/+100bps 30d; equity -5% 1d/-15% 30d; loan bid -1pt 1d/-3pts 30d. NER: ORG, PERSON, MONEY, PERCENT, DATE, RATIO, INSTRUMENT, RATING, CUSIP/ISIN, COVENANT.

## Signal Quality Rules
- Every signal must be observable and carry source_trace, as-of date, and evidence basis. No synthetic or inferred signals.
- Tag each operating/financial signal **Leading** or **Lagging** using REF_CP-2B_MonitoringIndicatorLibrary.md (CP-2B module) as the controlled vocabulary; tag the fragility group using REF_CP-2B_FragilityDriverTaxonomy.md.
- Quantitative thresholds beyond the market thresholds above may be applied only if sourced (covenant levels, management guidance, CP-2B/CP-SR thresholds) — do not invent threshold levels, covenant headroom, or guidance figures.
- Where an issuer has CP-2B output, link extracted signals to the matching downside pathway row (CP-2B-DP-###) or monitoring trigger (CP-2B-MON-###); the link feeds the Materiality Scoring booster in REF_CP-MON_E.
- Separate source fact from characterization: promotional or management language is extracted as a claim with [Management Language] qualification, not as fact.
- Conflicting signals from different sources are both retained and flagged; do not reconcile silently.
