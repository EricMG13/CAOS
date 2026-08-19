<!-- SCHEMA_CP-MON_IssuerResolver | v1.0 | 2026-06-08 -->
# SCHEMA_CP-MON_IssuerResolver — Issuer Resolver Engine Specification

## 1.1 Purpose

The Issuer Resolver is the Step A engine. It accepts a raw user input (free-text name, LEI, CUSIP, ISIN, ticker, deal code, or CP-0 issuer_id), queries resolution sources in priority order, scores match confidence, constructs the alias table and parent-subsidiary chain, and outputs a canonical IssuerRecord. This schema defines the resolver's input, processing logic, intermediate objects, and output — not just the final record (which is covered by SCHEMA_CP-MON_IssuerRegistry).

---

## 1.2 Resolver Input Object

```json
{
  "$id": "CP-MON-ResolverInput-v1.0",
  "type": "object",
  "required": ["raw_identifier"],
  "properties": {
    "raw_identifier": {
      "type": "string",
      "description": "User-supplied issuer reference. Free-text name, LEI, CUSIP, ISIN, ticker, deal/project code, or CP-0 issuer_id."
    },
    "identifier_hint": {
      "type": "string",
      "enum": ["name", "lei", "cusip", "isin", "ticker", "deal_code", "cp0_id", "auto"],
      "default": "auto",
      "description": "Optional hint to guide first-pass matching. If auto, resolver infers type from pattern."
    },
    "sector_hint": {
      "type": "string",
      "description": "Optional GICS/SIC code to narrow disambiguation."
    },
    "geography_hint": {
      "type": "string",
      "description": "Optional geography to narrow disambiguation (e.g., US, UK, EMEA)."
    },
    "context_signals": {
      "type": "array",
      "items": { "type": "string" },
      "description": "Optional co-occurring identifiers or keywords from the triggering context (e.g., instrument names, sponsor names) to assist disambiguation."
    }
  }
}
```

---

## 1.3 Identifier Pattern Detection

When `identifier_hint = auto`, the resolver applies pattern matching before querying sources:

| Pattern | Detected Type | Example | First Source |
|---|---|---|---|
| `^CPMON-[A-Z0-9]+-\d{3}$` | cp0_id | CPMON-VEEAM-001 | CP-0 Registry |
| `^[A-Z0-9]{20}$` | lei | 549300XXXXXXXXXXXXXXXX | GLEIF |
| `^[A-Z0-9]{9}$` | cusip | 91831AAB2 | CGS |
| `^[A-Z]{2}[A-Z0-9]{10}$` | isin | US91831AAB26 | CGS |
| `^[A-Z]{1,5}$` (no spaces) | ticker | VEEAM | Bloomberg FIGI |
| Contains "Project" or known deal prefix | deal_code | Project Tuple | LCD/PitchBook |
| All other strings | name | Veeam Software | CP-0 -> GLEIF -> EDGAR |

If pattern is ambiguous (e.g., 9-char alphanumeric that could be CUSIP or short name), resolver queries both CUSIP and name paths in parallel and selects highest-confidence result.

---

## 1.4 Resolution Source Cascade

```
                     +-----------------------------+
                     |   raw_identifier received    |
                     +-------------+---------------+
                                   |
                     +-------------v---------------+
                     |  Pattern detection / hint    |
                     +-------------+---------------+
                                   |
              +--------------------+---------------------+
              |                    |                      |
     +--------v------+   +--------v-------+   +----------v---------+
     |  CP-0 Registry |   | GLEIF / CGS    |   | EDGAR / CH / LCD   |
     |  (Priority 1)  |   | (Priority 2-3) |   | (Priority 5-7)     |
     +--------+------+   +--------+-------+   +----------+---------+
              |                    |                      |
              +--------------------+----------------------+
                                   |
                     +-------------v---------------+
                     |  CandidateMatch[] collected  |
                     +-------------+---------------+
                                   |
                     +-------------v---------------+
                     |  Confidence scoring & rank   |
                     +-------------+---------------+
                                   |
                   +---------------+----------------+
                   |               |                 |
          +--------v---+   +------v------+   +------v--------+
          | conf >=0.90 |   | 0.80-0.89  |   |  conf <0.80   |
          |  -> accept  |   | -> enrich  |   |  -> HALT      |
          +--------+---+   |   via next  |   |  disambiguate |
                   |       |   source    |   +---------------+
                   |       +------+------+
                   |              |
                   +------+-------+
                          |
              +-----------v-----------+
              |  Build IssuerRecord   |
              |  (alias table,        |
              |   parent-sub chain,   |
              |   sector, ratings,    |
              |   CP-0 link)          |
              +-----------------------+
```

---

## 1.5 CandidateMatch Object

Each source query returns zero or more CandidateMatch objects:

```json
{
  "$id": "CP-MON-CandidateMatch-v1.0",
  "type": "object",
  "required": ["candidate_id", "source", "matched_field", "matched_value", "raw_confidence"],
  "properties": {
    "candidate_id":    { "type": "string", "description": "Unique candidate identifier within this resolver run." },
    "source":          { "type": "string", "enum": ["CP-0", "GLEIF", "CGS", "FIGI", "EDGAR", "CH", "LCD", "PITCHBOOK"] },
    "matched_field":   { "type": "string", "description": "Which field matched: legal_name, lei, cusip, isin, ticker, deal_name, cik, company_number." },
    "matched_value":   { "type": "string", "description": "The value that matched in the source." },
    "raw_confidence":  { "type": "number", "minimum": 0, "maximum": 1, "description": "Source-level match confidence." },
    "legal_name":      { "type": "string" },
    "lei":             { "type": ["string", "null"] },
    "jurisdiction":    { "type": "string" },
    "sector":          { "type": "string" },
    "parent_entity":   { "type": ["string", "null"] },
    "identifiers": {
      "type": "object",
      "properties": {
        "cusips": { "type": "array", "items": { "type": "string" } },
        "isins":  { "type": "array", "items": { "type": "string" } },
        "tickers":{ "type": "array", "items": { "type": "string" } },
        "cik":    { "type": ["string", "null"] },
        "company_number": { "type": ["string", "null"] }
      }
    },
    "source_timestamp": { "type": "string", "format": "date-time" }
  }
}
```

---

## 1.6 Confidence Scoring Model

The resolver scores each candidate across four dimensions:

| Dimension | Weight | Scoring Logic |
|---|---:|---|
| **Lexical match** | 0.35 | Exact = 1.0; fuzzy Levenshtein >=0.90 = 0.85; >=0.80 = 0.70; below = 0.40 |
| **Identifier corroboration** | 0.30 | CUSIP/ISIN/LEI confirmed by >=2 sources = 1.0; 1 source = 0.80; none = 0.30 |
| **Sector / geography alignment** | 0.20 | Matches sector_hint/geography_hint = 1.0; partial = 0.60; no hint = 0.80 (neutral) |
| **Context signal overlap** | 0.15 | >=2 context_signals match candidate data = 1.0; 1 = 0.70; none = 0.40 |

```
composite_confidence = SUM(dimension_weight x dimension_score)
```

**Thresholds:**

| Composite | Action |
|---:|---|
| >= 0.90 | **Accept** — proceed to IssuerRecord construction. Lower-priority sources used for enrichment only. |
| 0.80 - 0.89 | **Enrich** — query next-priority source for corroboration. If corroborated, accept. If contradicted, flag ambiguity. |
| 0.60 - 0.79 | **Ambiguous** — collect all candidates, rank, present disambiguation prompt. |
| < 0.60 | **Reject** — discard candidate. If all candidates rejected, HALT with "No Match Found". |

---

## 1.7 Disambiguation Prompt Schema

When the resolver cannot auto-resolve, it returns a DisambiguationPrompt:

```json
{
  "$id": "CP-MON-DisambiguationPrompt-v1.0",
  "type": "object",
  "required": ["resolver_run_id", "raw_identifier", "candidates", "prompt_text"],
  "properties": {
    "resolver_run_id": { "type": "string" },
    "raw_identifier":  { "type": "string" },
    "candidates": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "option_label":  { "type": "string", "description": "(a), (b), (c)..." },
          "display_name":  { "type": "string" },
          "legal_name":    { "type": "string" },
          "lei":           { "type": ["string", "null"] },
          "sector":        { "type": "string" },
          "geography":     { "type": "string" },
          "confidence":    { "type": "number" },
          "source":        { "type": "string" },
          "disqualifiers": { "type": "array", "items": { "type": "string" }, "description": "Reasons confidence is below threshold." }
        }
      }
    },
    "prompt_text": { "type": "string", "description": "Pre-formatted analyst-facing disambiguation message." },
    "no_match_option": { "type": "boolean", "default": true, "description": "Include None of the above option." }
  }
}
```

---

## 1.8 Parent-Subsidiary Chain Resolution

After the primary entity is resolved, the resolver builds the corporate chain:

| Step | Source | Output |
|---|---|---|
| 1. Ultimate parent | GLEIF relationship data / deal docs | UBO / fund entity |
| 2. Intermediate holdcos | GLEIF / EDGAR / deal docs | HoldCo chain |
| 3. Borrower identification | LCD / deal docs / CP-0 | Credit entity designation |
| 4. Operating entities | GLEIF / EDGAR / Companies House | OpCo list |
| 5. Acquired entities | LCD / PitchBook / news | Subsidiary list with acquisition dates |

**Chain object:**

```json
{
  "chain_id": "CHAIN-VEEAM-001",
  "credit_entity": "VS Buyer, LLC",
  "chain": [
    { "entity": "Insight Partners", "role": "ultimate_parent", "type": "sponsor_fund" },
    { "entity": "VS Holdings, Inc.", "role": "holdco", "type": "intermediate" },
    { "entity": "VS Buyer, LLC", "role": "borrower", "type": "credit_entity" },
    { "entity": "Veeam Software Group GmbH", "role": "opco", "type": "operating" },
    { "entity": "Securiti, Inc.", "role": "subsidiary", "type": "acquired", "date": "2025-12-10" },
    { "entity": "ObjectFirst, Inc.", "role": "subsidiary", "type": "acquired", "date": "2025-12-15" }
  ],
  "signal_attribution_rules": {
    "credit_entity_match": "attribute directly",
    "opco_match": "attribute to credit entity with sub-entity qualifier",
    "subsidiary_match": "attribute to credit entity with subsidiary qualifier",
    "sponsor_match": "attribute with Governance/sponsor theme; relevance capped 0.70",
    "holdco_match": "attribute to credit entity"
  }
}
```

---

## 1.9 Alias Table Construction Rules

| Rule | Logic |
|---|---|
| **Seed** | legal_name (exact, 1.00) from resolution source |
| **Display** | display_name (fuzzy >=0.85, 0.95) — most common public reference |
| **Short** | first word / acronym (exact_boundary, 0.90) |
| **Deal** | project/deal code from LCD (exact, 0.85) |
| **Former** | pre-rename / pre-M&A names (exact, 0.80) |
| **Ticker** | exchange ticker if public (exact, 0.90) |
| **CUSIP prefix** | 6-char issuer CUSIP (exact_prefix, 0.85) |
| **Subsidiary** | subsidiary display names (exact, 0.80) |
| **Sponsor** | sponsor name (exact, 0.50 — flagged, capped) |
| **Colloquial** | common informal reference (case_insensitive, 0.85) |
| **Collision check** | if alias matches >=2 issuers in registry, require co-occurrence with issuer-specific alias in same document |

---

## 1.10 Resolver Audit Record

Every resolution attempt is logged:

```json
{
  "resolver_run_id": "RESOLVE-20260608-001",
  "raw_identifier": "Veeam",
  "identifier_hint": "auto",
  "detected_type": "name",
  "sources_queried": ["CP-0", "GLEIF", "CGS", "EDGAR", "LCD"],
  "candidates_found": 3,
  "candidates": [ "...CandidateMatch objects..." ],
  "selected_candidate": "CPMON-VEEAM-001",
  "composite_confidence": 0.97,
  "resolution_method": "accept",
  "disambiguation_required": false,
  "chain_built": true,
  "aliases_constructed": 10,
  "duration_ms": 1240,
  "timestamp": "2026-06-08T06:00:01Z"
}
```

---

## 1.11 Edge Case Handling

| Scenario | Resolver Behaviour |
|---|---|
| **Input is a URL** | Extract CUSIP/CIK/filing ID from URL path; resolve entity from extracted identifier |
| **Input is a natural-language phrase** | Extract NER entities; attempt resolution on each ORG entity |
| **Input matches a liquidated/dissolved entity** | Return candidate with [Dissolved - {date}] flag; analyst must confirm |
| **Input matches entity undergoing restructuring** | Include both pre-petition and DIP entities; flag [Restructuring Active] |
| **Input matches co-borrower** | Resolve to primary borrower; co-borrower retained as alias with [Co-Borrower] qualifier |
| **Multiple instruments, same issuer** | Single IssuerRecord; instruments tracked in cusips[] / isins[] |
| **Issuer has changed name** | Both old and new names in alias table; historical signals attributed to current entity |
| **Watchlist contains issuer_id** | Skip resolution; load IssuerRecord directly from registry |

---

## 1.12 Resolver Configuration

```json
{
  "resolver_config": {
    "max_sources_per_run": 7,
    "parallel_queries": true,
    "timeout_per_source_ms": 5000,
    "accept_threshold": 0.90,
    "enrich_threshold": 0.80,
    "ambiguity_threshold": 0.60,
    "max_candidates_displayed": 5,
    "auto_enrich_on_accept": true,
    "cache_ttl_hours": 24,
    "stale_record_refresh_days": 30
  }
}
```

<!-- END SCHEMA_CP-MON_IssuerResolver -->
