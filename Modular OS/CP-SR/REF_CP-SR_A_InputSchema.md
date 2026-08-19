# REF_CP-SR_A | Input Schema & Runtime Configuration
# Version: 1.0 | Date: 2026-06-08

## INPUT PARAMETERS

### Required Parameters
| Parameter | Type | Description | Example |
|---|---|---|---|
| sector | string | Primary sector classification | European HY Telecoms |
| sub_segments | list[string] | Sub-sector breakdown | Incumbent, Cable, TowerCo, AltNet/FibreCo |
| geography | list[string] | Geographic scope | UK, France, Germany, Italy, Spain, Nordics |
| timeframe | string | Analysis period | LTM to Q1 2026 + 12-month forward |
| exclusions | list[string] | Explicit exclusions | IG-only operators, Equipment vendors |
| audience | string | Target consumer | Credit analysts, risk committees, PMs |
| expertise_level | enum | junior / mid / senior / committee | senior |
| downstream_decisions | list[string] | Decisions informed | Sector allocation, risk rating, relative value |
| refresh_trigger | enum | scheduled / event-driven / ad-hoc | scheduled |

### Optional Parameters
| Parameter | Type | Description |
|---|---|---|
| source_package | list[string] | Pre-loaded source files, links, or IDs |
| issuer_universe | list[string] | Specific issuers to include |
| benchmark_indices | list[string] | Reference indices for spread context |
| prior_review_id | string | Prior CP-SR output for delta analysis |

## SOURCE HIERARCHY
| Tier | Source Type | Reliability | Examples |
|---|---|---|---|
| Tier 1 | Primary / Direct Disclosure | High | Company filings, offering memoranda, credit agreements |
| Tier 1.5 | Internal Research & Institutional Intelligence | High | Analyst's own write-ups, internal credit memos, forwarded rating actions, sell-side alerts with direct data |
| Tier 2 | Institutional Research | Medium-High | Fitch, Moody's, S&P, CreditSights, bank research, CLO trustee reports |
| Tier 2.5 | Sell-Side Trading Commentary | Medium | Desk color, pricing axes, flow commentary, market rundowns |
| Tier 3 | Secondary / Interpretive | Medium | Industry associations, consulting research, media, market commentary |
| Tier 4 | Unverified / Estimate | Low | Social media, unattributed data, single-source estimates |

### Source Validation Rules
1. Minimum 3 Tier 1/2 sources required for High confidence.
2. Tier 3 sources are acceptable only with Tier 1/2 corroboration.
3. Tier 4 sources must be flagged as Unverified and cannot support High confidence conclusions.
4. Data >90 days from execution date is POTENTIALLY_STALE.
5. Data >180 days is STALE and requires explicit analyst override.

## REFRESH CADENCE
| Trigger Type | Frequency | Condition |
|---|---|---|
| Scheduled | Quarterly | Standard refresh aligned to earnings cycle |
| Event-driven | Ad-hoc | Major regulatory change, wave of downgrades, default, LME, M&A event |
| Staleness | Auto-flag | Output >90 days old |
| CP-MON trigger | Auto | CreditPulse alert matching sector classification |
