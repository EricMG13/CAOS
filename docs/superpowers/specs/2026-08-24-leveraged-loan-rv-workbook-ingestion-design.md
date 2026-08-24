---
meta:
  title: Screen leveraged loans from the CP-3 workbook
  navLabel: Screening leveraged loans
  category: Architecture decisions
  contentType: Conceptual
---

# Screen leveraged loans from the CP-3 workbook

This design replaces manual generic relative-value (RV) rows with a read-only leveraged-loan screener sourced from the fixed CP-3 sector workbook. CAOS stores the original XLSX, validates every visible sector table, normalizes the loan rows once, and activates the complete universe atomically. The screen displays source-reported loan metrics immediately without presenting them as CP-3 conclusions.

## Content plan

- **Goal**: ingest one fixed CP-3 workbook and display its leveraged-loan universe with the correct loan metrics
- **Audience**: buy-side credit analysts, methodology owners, CAOS engineers, and QA reviewers
- **Outcome**: an analyst can upload the workbook and screen every valid sector row without manual re-entry
- **Scope**: source upload, workbook validation, normalization, versioning, the loan-only RV screen, failure behavior, deployment, and verification
- **Open questions**: none; the approved decisions appear in this design

## Approved product contract

The minimum viable product supports leveraged loans only. It does not switch between loan and bond metrics, compare loans with bonds, or retain the generic manual-entry workflow as the active screen.

An analyst uploads the same workbook template used by CP-3. CAOS imports all visible worksheets that contain the fixed issuer-table header, combines their rows into one case-scoped universe, and displays that universe as soon as validation and persistence succeed. The screen labels the data `SOURCE DATA · UNANALYZED` until CP-3 produces a separately governed conclusion.

The workbook remains the source artifact. The normalized universe is an immutable, reproducible representation bound to the source ID, source SHA-256, template version, importer version, and canonical universe digest. CP-3 consumes that same universe identity and normalized interpretation instead of reparsing the workbook under a second set of rules.

## Excluded work

The minimum viable product excludes:

- Bond fields, bond calculations, and product-adaptive columns
- Flexible spreadsheet mapping or support for workbook variants
- Manual row creation or editing in the RV screen
- Recalculation of yield, discount margin, or price changes
- Index Statistics and Sector Ratings Average summary blocks
- Attractive, fair, or unattractive signals before CP-3 acceptance
- A new queue, worker, service, parser dependency, or market-data feed

## Analyst flow

The RV screen reuses the existing governed source workflow:

1. The analyst selects **Upload CP-3 workbook** from the RV screen
2. The client uploads the XLSX through `POST /api/cases/{case_id}/sources`
3. The existing source boundary checks access, size, archive safety, malware status, hash, and vault persistence
4. The client submits the resulting `source_id` to `POST /api/cases/{case_id}/rv/loan-universes`
5. The server validates and normalizes the workbook synchronously
6. One database transaction writes the universe and rows, supersedes the prior active version, and activates the candidate
7. The client reads `GET /api/cases/{case_id}/rv/loan-universes/active` and renders the complete universe

The upload action shows `Uploading and scanning…`, then `Validating…`, followed by `Active` or `Rejected`. A rejected RV import does not delete the uploaded source. It leaves the prior active universe unchanged and displays bounded validation findings.

## Workbook boundary

The importer accepts only an active `.xlsx` source that belongs to the case. It reads bytes from the vault path resolved by the server. A request cannot supply a filesystem path, workbook URL, sheet name, or column mapping.

The existing upload limits and ZIP checks remain mandatory. The RV importer additionally rejects packages containing macros, external links, embedded objects, or malformed Open XML parts. It caps processing at 64 worksheets, 25,000 issuer rows, 64 columns per worksheet, and 32 KB of text per cell.

The importer uses the installed `openpyxl` package in read-only mode. It never executes formulas or follows external references. A formula cell may contribute only its cached workbook value. A formula without a cached result is missing data and passes through the normal required-field checks.

## Template recognition

The importer recognizes a sector worksheet by the exact issuer-table header sequence after trimming surrounding whitespace. It finds the table by headers rather than worksheet name or row number. This follows the CP-3 workbook contract while avoiding dependence on sector-tab labels.

The required columns are:

1. Company
2. Borrower Name
3. Core Business Description
4. Sub-Sector
5. Sub-Group
6. Public/Private
7. Bloomberg
8. FIGI
9. Loan Type
10. Ranking
11. Ratings
12. Size ($Mn)
13. Margin
14. Maturity
15. Bid
16. Ask
17. Δ 1D
18. Δ 1W
19. Δ 1M
20. Δ 3M
21. Δ 6M
22. Δ 1YR
23. Δ YTD
24. Mid YTM
25. Mid 3Y DM

Rows begin immediately below the header and end at the first fully blank row after the first instrument. The importer includes filtered or hidden rows inside that region so Excel display state cannot silently remove instruments. It ignores hidden worksheets and all content after the issuer table, including workbook summary blocks.

The workbook must contain at least one recognized sector worksheet. Each recognized worksheet must contain the template's `Date` label and date cell, and every worksheet date must match. The date may be an Excel date value or `DD/MM/YYYY`; CAOS stores it as an ISO calendar date. A visible worksheet containing `Borrower Name` and at least four other canonical headers is a partial sector table unless the complete ordered header is present. A partial sector table rejects the candidate instead of disappearing from the import.

## Normalized loan contract

Each normalized row preserves the workbook's loan terminology and units:

| Group | Field | Normalized meaning |
|---|---|---|
| Identity | `company` | Source-reported company name |
| Identity | `borrower_name` | Required borrower name |
| Identity | `bloomberg_loan_id` | Bloomberg loan identifier |
| Identity | `figi` | Financial Instrument Global Identifier |
| Provenance | `source_locators` | Every original worksheet title and one-based row number |
| Classification | `business_description` | Core business description |
| Classification | `sector` | Sector derived from the source worksheet |
| Classification | `sub_sector` | Source-reported sub-sector |
| Classification | `sub_group` | Source-reported subgroup |
| Classification | `public_private` | Public or private classification |
| Structure | `loan_type` | Source-reported loan type |
| Structure | `ranking` | Ranking or seniority label |
| Structure | `ratings` | Source-reported rating text |
| Terms | `size_mn` | Size in millions of US dollars |
| Terms | `margin_bps` | Margin in basis points |
| Terms | `maturity_date` | Contractual maturity date |
| Market | `bid_points` | Bid in points of par |
| Market | `ask_points` | Ask in points of par |
| Market | `change_1d_points` through `change_ytd_points` | Signed price changes in points |
| Market | `mid_ytm_pct` | Source-reported mid yield to maturity in percent |
| Market | `mid_3y_dm_bps` | Source-reported three-year discount margin in basis points |

Every numeric value must be finite or null. Blank cells, `#N/A`, Excel errors, and missing formula caches normalize to null, never zero. The importer parses source values into their declared units without scaling or deriving new metrics.

A row requires `borrower_name` and at least one of `figi` or `bloomberg_loan_id`. A rejected row rejects the complete candidate, preventing a partial active universe.

## Instrument identity and duplicate handling

The canonical instrument key uses FIGI when present and Bloomberg loan ID otherwise. When both identifiers exist, CAOS records both and requires their mapping to remain consistent across the workbook.

Rows with the same key and identical normalized values collapse into one instrument while preserving every source-sheet and source-row locator. Rows with the same key but different values create conflict findings and reject the candidate. A FIGI mapped to multiple Bloomberg IDs, or one Bloomberg ID mapped to multiple FIGIs, also rejects the candidate.

## Versioning and authority

Each import creates a candidate universe with these identities:

- Case ID and source ID
- Source SHA-256
- Workbook date
- Fixed template version
- Importer version
- Canonical row count and universe digest
- Actor and created timestamp

The canonical digest covers normalized metadata, rows, units, identifiers, and provenance in stable order. It does not cover UI sort or filter state.

Activation runs in one database transaction. The transaction stores the candidate and its rows, marks the prior active version as superseded, and marks the candidate active. A unique case-level database constraint prevents two active loan universes. Any exception rolls back the transaction and preserves the prior active version.

Withdrawing the source bound to the active universe removes that universe from active use. CAOS does not silently fall back to an older workbook. The screen requires an analyst to import and activate another source explicitly.

## API and persistence

The server adds two case-scoped routes:

- `POST /api/cases/{case_id}/rv/loan-universes`: validate and import one existing `source_id`; requires case write authority
- `GET /api/cases/{case_id}/rv/loan-universes/active`: return active universe metadata and normalized rows; requires case read authority

The import response returns `ACTIVE` with the universe identity, or `REJECTED` with stable finding codes and sheet, row, column, and safe detail. Responses never include vault paths, raw formulas, source text outside the affected cell, stack traces, or package internals.

The import is idempotent for the same case, source SHA-256, template version, and importer version. A repeated or concurrent request returns the existing result instead of creating another universe. A new active universe returns HTTP `201`; an invalid workbook returns HTTP `422` with findings; case, source, and authority errors use the existing governed HTTP semantics.

Additive PostgreSQL tables store universe metadata and normalized loan rows. Universe content and rows remain immutable after insertion. Lifecycle fields may record activation, supersession, rejection, and source withdrawal. `MemoryStore` mirrors the contract for local execution and API tests.

Historical generic RV records remain readable through their existing storage contract during migration. They cannot be returned by the loan-universe route or labeled as imported leveraged-loan data.

## RV screen

The RV destination becomes one read-only, case-scoped leveraged-loan table. It shows the active workbook date, source filename, source link, universe version, imported timestamp, row count, and `SOURCE DATA · UNANALYZED` authority label.

The table combines every imported sector worksheet and groups columns into:

- Borrower and identifiers
- Sector and classification
- Structure and terms
- Bid and ask
- Signed price changes
- Mid YTM and Mid 3Y DM

The screen supports borrower or company search plus filters for sector, rating, ranking, loan type, maturity, margin, and Mid 3Y DM. Every column remains sortable. The default order is sector, borrower name, then instrument key.

Numeric cells use aligned tabular figures and visible signs where applicable. Directional color reinforces positive or negative changes but never replaces the signed value. Nulls render as `N/A`. The table supports keyboard operation, visible focus, labeled horizontal scrolling, and reduced-motion preferences.

The screen does not calculate a relative-value score or recommendation. A future CP-3 overlay may appear only when its accepted output names the same universe ID and digest. The source table remains separately labeled when that overlay exists.

## Failure behavior

The importer fails closed for:

- Wrong file type, invalid package, unsafe package content, or processing-limit breach
- Missing or invalid workbook date
- No recognized sector worksheet
- Missing, reordered, renamed, or duplicated required columns
- A partial sector-table signature on a visible worksheet
- Invalid required identity or non-finite numeric data
- Conflicting instrument identifiers or duplicate values
- Persistence or activation failure
- Source withdrawal before activation completes

The UI groups findings by worksheet and row and shows a correction-oriented message. It never activates valid tabs from an otherwise invalid workbook. The previous active universe remains visible after an import failure.

## CP-3 boundary

The host-side importer owns the workbook interpretation for both the RV screen and CP-3. CP-3 receives the active universe ID, canonical digest, workbook date, normalized rows, and source locators. It cites the selected row and source workbook without reparsing or fuzzy-matching identifiers.

The immediate RV screen remains source-only. CP-3 owns peer selection, compensation assessment, structural interpretation, downside context, and any attractive, fair, or unattractive conclusion. A CP-3 output tied to another universe version cannot decorate the active table.

## Deployment

The change uses the existing FastAPI, PostgreSQL, vault, ClamAV, Caddy, and frontend containers. `openpyxl` already ships in the server requirements. The deployment adds one database migration, rebuilds the API image, and rebuilds the static frontend. It adds no service, queue, system package, environment variable, or exposed port.

The migration is additive and runs before the new images become active. The prior application version ignores the new tables, so rollback requires only the previous API and frontend images. Imported sources and universe versions remain available for a later retry; rollback does not delete them.

## Verification plan

Parser checks use an anonymized workbook fixture with multiple sector tabs and summary blocks. They verify every field, unit, null rule, table boundary, workbook date, source locator, digest, and duplicate rule. Focused rejection fixtures cover header drift, partial tables, formula cells without caches, non-finite values, identifier conflicts, hidden sheets, external links, macros, embedded objects, archive limits, and malformed packages.

API and persistence checks cover authorization, source ownership, source withdrawal, repeated imports, immutable versions, one active universe per case, atomic rollback, stable findings, and parity between `MemoryStore` and PostgreSQL. A failed candidate must leave the prior active universe byte-for-byte unchanged.

Frontend checks cover upload states, active and rejected results, all filters and sorts, exact unit labels, null rendering, signed changes, source provenance, keyboard operation, visible focus, horizontal overflow, reduced motion, and rendered axe-core validation.

One end-to-end deployment check uploads the anonymized XLSX through Caddy, passes ClamAV, activates the universe, reads every sector row in the RV screen, binds the same universe identity to a CP-3 input, and verifies that no pre-CP-3 recommendation appears.

## Acceptance criteria

The minimum viable product is complete when:

1. An authorized analyst can upload the fixed CP-3 XLSX and activate all valid sector rows without manual entry
2. The screen displays only the approved leveraged-loan fields with their declared units
3. Missing and erroneous cells never become zero or a non-finite JSON value
4. Invalid workbooks provide actionable findings and never replace the prior active universe
5. Every displayed row links to its source, worksheet, row, universe ID, and digest
6. CP-3 and the RV screen use the same normalized universe identity
7. The screen emits no recommendation before a matching accepted CP-3 output exists
8. The existing production stack deploys and rolls back the feature without a new runtime dependency
