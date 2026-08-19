# Example Pathways

## Pathway 1 — Full Credit Assessment

**Use case:** New issuer / new investment opportunity.

```text
CP-0 -> CP-X -> CP-1 + CP-1A
              -> CP-1B + CP-1C
              -> CP-2
              -> CP-2B + CP-2C + CP-2D + CP-2E + CP-2F
              -> CP-3 + CP-3D
              -> CP-3B + CP-3C
              -> CP-4 -> CP-4C
              -> CP-5B -> CP-5
              -> CP-6A -> CP-6E
              -> CP-RENDER
```

**Outputs:** Full credit synthesis, IC Action Bias, Portfolio Posture, committee reports.

## Pathway 2 — Covenant-Focused Review

**Use case:** New credit agreement, amendment, or covenant capacity question.

```text
CP-0 -> CP-1 -> CP-3D -> CP-4 -> CP-4C -> CP-5B -> CP-5
```

**Outputs:** Covenant interpretation, aggressiveness rubric, capacity calculations, headroom analysis.

## Pathway 3 — Earnings Update

**Use case:** Issuer reports quarterly or annual results.

```text
CP-0 -> CP-1 -> CP-1B -> CP-2 -> CP-5B -> CP-5
```

**Outputs:** Updated canonical data, earnings delta analysis, refreshed fundamental synthesis, QA status.

## Pathway 4 — Portfolio Allocation Decision

**Use case:** Credit view exists; portfolio team needs allocation decision.

```text
CP-3 -> CP-3C -> CP-4C -> CP-6A -> CP-6E
```

**Outputs:** Portfolio fit, sizing evidence gate, covenant capacity consideration, IC action bias, final Portfolio Posture.

## Pathway 5 — Relative Value and Security Selection

**Use case:** Compare instruments and determine security preference.

```text
CP-1 -> CP-1C -> CP-2 -> CP-2E -> CP-3 -> CP-3B
```

**Outputs:** Peer benchmark, RV analysis, spread comparison, recovery waterfall, LGD by instrument.

## Pathway 6 — Distressed / LME Risk Review

**Use case:** Issuer facing maturity wall, exchange offer, or creditor-on-creditor risk.

```text
CP-1 -> CP-2B -> CP-2E -> CP-3D -> CP-4 -> CP-4C -> CP-6A
```

**Outputs:** Refinancing path risk, LME risk register, covenant vulnerability, capacity analysis, IC debate.


## Pathway 7 — Sector Credit Review

**Use case:** Quarterly sector review, sector-wide event, or ad-hoc sector deep-dive.

```text
CP-SR (standalone)
  or
CP-MON (email intake) -> CP-SR -> CP-1 (issuer deep-dives) -> CP-5 -> CP-6A
```

**Outputs:** 7-section sector review, sector credit posture, comparative peer table, early warning dashboard, dimension scores, credit implication mappings, strategic implications.

## Pathway 8 — Monitoring-Driven Refresh

**Use case:** CP-MON detects a material event (rating action, price stress, LME alert) via email or market data.

```text
CP-MON (alert trigger)
    -> CP-X (routing)
    -> Relevant module refresh:
         Rating action     -> CP-1 + CP-6A
         New issue         -> CP-3 + CP-5
         LME / distressed  -> CP-3D + CP-6A + CP-4
         Sector stress     -> CP-SR
         Price move        -> CP-5 + CP-MON
```

**Outputs:** Updated alert log, refreshed issuer profiles, updated watchlist state, routing signals for downstream modules.

## Pathway 9 — Email-Enriched Full Credit Analysis

**Use case:** Full new credit analysis where email intelligence (rating actions, sell-side research, trading desk color, internal notes) is available and should enrich the analytical pipeline.

```text
CP-MON (email classification + intake)
    -> CP-0 -> CP-X -> CP-1 + CP-1A
                        -> CP-1B + CP-1C
                        -> CP-2
                        -> CP-2B + CP-2C + CP-2D + CP-2E + CP-2F
                        -> CP-3 + CP-3D
                        -> CP-3B + CP-3C
                        -> CP-4 -> CP-4C
                        -> CP-5B -> CP-5
                        -> CP-6A -> CP-6E
                        -> CP-RENDER

Email intelligence feeds throughout:
  CP-SR  (sector context)
  CP-1   (issuer event updates)
  CP-5   (market pricing color)
  CP-6A  (bull/bear arguments)
  CP-6E  (allocation context)
```

**Outputs:** Full credit synthesis, IC Action Bias, Portfolio Posture, committee reports — all enriched with real-time email-derived intelligence.

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-05-18 | Initial 6 pathways |
| 2.0 | 2026-06-08 | Added Pathway 7 (Sector Review), Pathway 8 (Monitoring Refresh), Pathway 9 (Email-Enriched Full Analysis) |
