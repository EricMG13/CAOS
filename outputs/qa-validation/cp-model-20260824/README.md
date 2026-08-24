# CP-MODEL browser-first validation — 2026-08-24

This record supersedes the former current-product signed-authority blocker. It
does not rewrite the historical workbooks or inventory JSON that recorded that
earlier state.

- An accepted canonical Full Credit fixture produced the persisted Python
  worksheet model without LibreOffice: 3 visible tabs, 701 cells, 338 formulas,
  and 20 semantic checks.
- The production API target ran as UID 10001 with no `soffice` executable.
- The production worker target ran as UID 10001 with LibreOffice 25.2.3.2 from
  the current Debian repository and produced a recalculated XLSX with 338
  validated formulas and 20 semantic checks. The apt repository is not claimed
  to be version-pinned.
- The real-PostgreSQL regression suite passed 322 tests, including model
  idempotency, leases, fencing, case authorization, downloads, and report
  identity.
- The combined browser journey passed all Model Builder states and controls;
  the axe sweep passed 29 route/viewport combinations with zero violations.
- A disposable production Compose stack applied migrations 001 and 002. Its
  backup/restore drill recovered a persisted model payload, both model job rows,
  and the exact optional XLSX bytes verified by size and SHA-256.
- Trivy 0.72.0 found zero fixable HIGH/CRITICAL vulnerabilities in both the API
  and LibreOffice worker targets against the 2026-08-24 vulnerability database.

LibreOffice remains an optional XLSX-publication dependency in the worker. It
is not a dependency of model readiness, calculation, persistence, worksheet
display, report binding, or the API image.
