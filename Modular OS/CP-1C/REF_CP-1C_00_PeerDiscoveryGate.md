<!-- REF_CP-1C_00 (T2) | 2026-06-02 -->
<step_reference module="CP-1C" step="00" name="Peer Discovery Gate">
<input>CP-1 borrower profile + input payload</input>
<gate>User peer list present?</gate>

## Instructions
IF NO user list → Execute web scrape: construct queries from CP-1 profile (sector/geography/revenue scale/business model/capital structure/public-private/key product), query 6 source types (regulatory filings, rating disclosures, industry DBs, LevFin databases, financial news, IR pages), promote if ≥3/16 dimensions assessable, tag all 'Web-Scraped — Unverified', produce CP-1C_PEER_DISCOVERY_SOURCE.json.
IF YES → Proceed to Step 1. Web scrape optional supplement.

## Output
CP-1C_PEER_DISCOVERY_SOURCE.json (if web scrape) or skip confirmation.
</step_reference>
