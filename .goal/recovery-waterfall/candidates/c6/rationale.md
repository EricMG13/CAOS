# Candidate c6 — domain-legible

**How an analyst can now verify the math by reading:** the docstring names every
financial concept the code embodies — recovery enterprise value (the pie),
absolute priority (senior paid in full before any junior), claim
(`amount_musd` = principal outstanding), recovery rate (cents on *that*
tranche's dollar), and the indeterminate cascade (an unknown senior claim makes
all juniors unprovable). A worked example (RCF/1L/2L @ 1000) is spelled out so
the reader can hand-check the 2L wipe. Variables read as finance, not plumbing:
`remaining_ev`, `claim`, `claim_is_sized`, `indeterminate`. Each inline comment
states *why* a line is defensible (full claim removed even on partial recovery;
remaining floored at 0; refusing to guess over-credits juniors).

**Why behavior is preserved (byte-for-byte on outputs):** the control flow is
unchanged from the original — `float(distressed_ev)`, list-order iteration with
no sort, sticky break latch, `min(claim, remaining)` with the same
`remaining > 0` guard, `max(0.0, remaining - claim)` floor, and `round(x, 1)`
half-even on the same float expressions. Renaming locals and a comment-only
rewrite cannot change results. All six golden cases reproduce exactly, including
the half-even killer 250/800 → **31.2**, the 0.0001 tranche → (0.0, 100.0), the
unsized-senior null cascade, fresh non-mutating `{**t}` rows, and the preserved
`KeyError` on a missing `amount_musd`.
