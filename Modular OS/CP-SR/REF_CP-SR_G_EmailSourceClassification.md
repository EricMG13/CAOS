# REF_CP-SR_G | Email Source Classification & Intake Rules
# Version: 1.0 | Date: 2026-06-08

## EMAIL CATEGORIES
| Category | Description | Tier | Auto-Ingest | Examples |
|---|---|---|---|---|
| RATING_ACTION | Rating agency alerts | 1.5 | Yes | S&P / Fitch / Moody's rating alerts |
| INTERNAL_RESEARCH | Analyst's own write-ups, internal credit memos | 1.5 | Yes | Internal notes sent to team DLs |
| SELL_SIDE_RESEARCH | CreditSights, BNP, Barclays, DB, GS research | 2 | Yes | Outlooks, recommendations, sector packs |
| SELL_SIDE_NEWS | LevFinInsights, Bixby, news/new issue alerts | 2 | Yes | M&A, ratings, issuance, restructuring alerts |
| TRADING_DESK | MS/UBS/RBC/GS desk commentary, axes, pricing | 2.5 | Conditional | Morning Bullet, axes, distressed pricing |
| MARKET_DATA | Bloomberg alerts and price/headline feeds | 2.5 | Conditional | Bloomberg First Word / Intelligence alerts |
| EVENT_INVITE | Webinars/conference invitations | 3 | Flag only | Fitch webinar, analyst access invites |
| INTERNAL_COMMS | Scheduling/team coordination | 3 | Context only | Sector review meeting threads |

## INTAKE RULES
1. RATING_ACTION emails: extract issuer, action, prior rating, new rating, outlook, rationale, date.
2. INTERNAL_RESEARCH: prioritize analyst's own views as Tier 1.5 internal intelligence.
3. SELL_SIDE_RESEARCH: extract recommendations, thesis, key metrics, catalysts.
4. SELL_SIDE_NEWS: extract event facts, dates, amounts, parties, and expected close timing.
5. TRADING_DESK: extract pricing, axes, flows, bid/offer levels, but apply short staleness.
6. MARKET_DATA: extract headline, tickers, price moves, and timestamp.
7. EVENT_INVITE and INTERNAL_COMMS: use for context and calendar awareness, not analytical conclusions unless content includes substantive data.

## DEDUPLICATION RULES
- Same rating action from multiple emails: prefer direct rating agency alert.
- Same news event from Bloomberg and sell-side: retain earliest and most detailed source.
- Weekly digests: skip if underlying individual alert is already captured.
- Duplicated webinar invitations: retain latest only, unless agenda text differs.

## EMAIL-SPECIFIC STALENESS RULES
| Source Type | Staleness Rule |
|---|---|
| Rating actions | Permanent record; never stale for historical rating path |
| Internal research | Review after 90 days unless reaffirmed |
| Sell-side research | Stale after 90 days unless updated |
| Trading desk pricing | Stale after 5 business days |
| Market color / flow commentary | Stale after 10 business days |
| Event invites | Stale after event date |

## EXTRACTION SCHEMA
```json
{
  "email_id": "string",
  "category": "RATING_ACTION|INTERNAL_RESEARCH|SELL_SIDE_RESEARCH|SELL_SIDE_NEWS|TRADING_DESK|MARKET_DATA|EVENT_INVITE|INTERNAL_COMMS",
  "tier": "number",
  "date": "date",
  "sender": "string",
  "subject": "string",
  "issuer_refs": ["string"],
  "sector_refs": ["string"],
  "key_data_points": [
    {
      "metric": "string",
      "value": "string",
      "source_confidence": "High|Medium|Low"
    }
  ],
  "credit_implications": ["LEVERAGE_PRESSURE|MARGIN_EROSION|CASH_FLOW_STRESS|REFINANCING_RISK|REGULATORY_OVERHANG|STRUCTURAL_SUBORDINATION|EVENT_RISK|CREDIT_IMPROVEMENT"],
  "actionable": "boolean",
  "staleness_date": "date"
}
```
