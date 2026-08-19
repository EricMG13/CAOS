# CP-SR | Sector Review Module — Contract Schema
# Version: 1.0

## IDENTITY
| Field | Value |
|---|---|
| module_id | CP-SR |
| module_name | SectorReview |
| module_type | Analytical — Sector Level |
| version | 1.0 |
| created | 2026-06-08 |

## INPUT CONTRACT
| Input | Source | Required |
|---|---|---|
| Runtime Config | Operator / Orchestrator | Yes |
| Source Package | Analyst / External / Email | Yes |
| Prior CP-SR output | Master Index | No |
| CP-MON alert payload | CP-MON | No |

## OUTPUT CONTRACT
| Output | Format | Consumer |
|---|---|---|
| 7-Section Sector Review | Markdown / JSON | Analyst, CP-1, CP-2, CP-5, CP-6A, CP-6E |
| Sector Credit Posture | Enum | CP-6E, Portfolio Dashboard |
| Dimension Scores | Array | CP-2, CP-6A |
| Risk Register | Array | CP-6A, CP-MON |
| Early Warning Dashboard | Array | CP-MON |
| Comparative Table | Structured table | CP-5 |
| Master Index State | JSON object | Master Index |

## UPSTREAM DEPENDENCIES
| Module / Source | Relationship |
|---|---|
| CP-MON | Event-driven trigger |
| CP-1 | Issuer profile context |
| Email Intelligence | Real-time rating/news/research/trading intelligence |
| External Sources | Filings, ratings, industry reports, market data |

## DOWNSTREAM CONSUMERS
| Module | What It Consumes |
|---|---|
| CP-1 | Sector context and sub-segment classification |
| CP-2 | Sector risk score and dimension scores |
| CP-5 | Comparative table and spread context |
| CP-6A | Risk register and adversarial vectors |
| CP-6E | Sector posture and allocation implications |
| CP-MON | EW indicators and alert thresholds |

## EXECUTION MODES
| Mode | Trigger | Scope |
|---|---|---|
| Full | First run or major structural change | All 7 sections |
| Refresh | Scheduled quarterly or CP-MON alert | Update Sections 3–6, validate Sections 1 and 7 |
| Delta | Ad-hoc event | Update affected sections only |

## STALENESS RULES
| Age | Status | Action |
|---|---|---|
| 0–90 days | Current | No action |
| 91–180 days | POTENTIALLY_STALE | Flag in Master Index, queue for refresh |
| >180 days | STALE | Block downstream consumption until refreshed or overridden |
