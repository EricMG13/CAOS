# c3 — performance-first

**Honest verdict: there is no meaningful performance win here.** `assess_fit` is a
single dict lookup plus one numeric comparison, called exactly once per issuer
inside `synthesize_portfolio_fit`. It is not a hot path — no loop, no per-row
fan-out, no I/O. Any "optimization" would be measuring noise (sub-microsecond),
so I refuse to trade legibility for a fake micro-op.

The only change is to fold the membership test and the lookup into one
`_FIT.get(rec)` instead of `rec not in _FIT` followed by `_FIT[rec]` — one hash
of `rec` instead of two. `rec` is still bound once (so `rv_recommendation` reuses
it, no second `.get`), and the original `not in` / indexing pair is collapsed
into the standard `.get(...) is None` idiom. This is equivalent because no `_FIT`
value is `None` (all are tuples). All five contract points, the NaN-safe `>= 6.0`
gate, the `{leverage:g}` format, and the byte-for-byte flag/note strings are
unchanged. Net: a near-identical rewrite, marginally tidier, same behavior.
