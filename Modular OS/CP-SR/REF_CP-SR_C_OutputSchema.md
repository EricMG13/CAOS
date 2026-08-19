# REF_CP-SR_C | Output Schema — Canonical Structure
# Version: 1.0

## SECTION 1: EXECUTIVE SUMMARY
| Field | Type | Requirement |
|---|---|---|
| summary_text | string, 3–4 sentences | Required |
| sector_credit_posture | enum | Required |
| posture_justification | string | Required |
| confidence_level | enum High/Medium/Low | Required |
| key_change_vs_prior | string | Conditional |

### Sector Credit Posture Enum
`STRONG_BUY | CONSTRUCTIVE | NEUTRAL | CAUTIOUS | DEFENSIVE | AVOID`

## SECTION 2: SECTOR OVERVIEW
| Field | Type | Requirement |
|---|---|---|
| market_size | string | Required |
| growth_dynamics | string | Required |
| structural_characteristics | list[string] | Required |
| sub_segment_breakdown | list[object] | Required |
| confidence_level | enum | Required |

## SECTION 3: KEY CREDIT DRIVERS
| Field | Type | Requirement |
|---|---|---|
| dimension_scores | list[DimensionScore] | Required |
| driver_narratives | list[string] | Required |
| confidence_level | enum | Required |

### DimensionScore Object
```json
{
  "dimension_id": "int",
  "dimension_name": "string",
  "score": "int 1-5",
  "confidence": "High|Medium|Low",
  "narrative": "string",
  "sources": ["source_id"]
}
```

## SECTION 4: RISK ASSESSMENT
| Field | Type | Requirement |
|---|---|---|
| risks | list[RiskItem], 3–5 items | Required |
| confidence_level | enum | Required |

### RiskItem Object
```json
{
  "risk_id": "string",
  "risk_name": "string",
  "description": "string",
  "severity": "Critical|High|Medium|Low",
  "likelihood": "High|Medium|Low",
  "credit_implications": ["canonical_implication"],
  "mitigation_factors": "string",
  "sources": ["source_id"]
}
```

## SECTION 5: COMPARATIVE TABLE
| Field | Type | Requirement |
|---|---|---|
| table_data | list[PeerRow] | Required |
| data_gaps | list[string] | Required |
| as_of_date | date | Required |
| confidence_level | enum | Required |

## SECTION 6: EARLY WARNING DASHBOARD
| Field | Type | Requirement |
|---|---|---|
| indicators | list[EWIndicator] | Required |
| trend_summary | string | Required |
| confidence_level | enum | Required |

## SECTION 7: STRATEGIC IMPLICATIONS
| Field | Type | Requirement |
|---|---|---|
| recommendations | list[Recommendation], 2–3 items | Required |
| confidence_level | enum | Required |

### Recommendation Object
```json
{
  "rec_id": "string",
  "recommendation": "string",
  "rationale": "string",
  "target_audience": "string",
  "time_horizon": "string",
  "downstream_module_refs": ["CP-1", "CP-2", "CP-5", "CP-6A", "CP-6E", "CP-MON"]
}
```

## MASTER INDEX STATE
| Field | Type |
|---|---|
| master_index_id | string |
| issuer_id_name | string, sector name |
| module_id | CP-SR |
| module_name | SectorReview |
| module_status | Complete / Draft / Stale |
| output_date | date |
| execution_mode | Full / Refresh / Delta |
| sector_credit_posture | enum |
| refresh_trigger | enum |
| next_scheduled_refresh | date |
| staleness_flag | boolean |
| downstream_consumers | list[string] |
