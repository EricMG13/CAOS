# c3 — performance-first

Folds the three iterations over `scored` (filter-comprehension, `sum`, `len`)
into a single `for` loop that filters, accumulates the percentile total, and
appends the scorecard row in one pass. `metrics_scored` becomes `len(scorecard)`;
`composite = round(total / n)` uses the same sum/len over the same filtered set,
so round-to-int (banker's) is byte-identical.

Honest verdict: **no meaningful gain.** This runs once per issuer over a handful
of peer metrics (typ. <15 rows) — not a hot path. 3 passes over ~10 items is
already microseconds; folding to 1 saves nothing measurable and the loop is
arguably slightly less readable than the comprehension. The result is identical
on every golden ({70,80,90}→80/OW/3; {58,59}→58 half-even; {True,False}→0;
{}→None; default scope "peers"). Pick c3 only if you specifically want the
single-pass form; otherwise the original is fine.
