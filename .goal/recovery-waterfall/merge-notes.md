# Merge notes — winner c6, optional cherry-picks

**Winner:** c6 (domain-legible). `winner.diff` applies cleanly to
`caos/server/engine/capstructure.py:53-76`. It is a comments-and-renames rewrite
over the **identical control flow** as the original — zero behavioral change,
proven by the 18 hard golden cases + 23 existing/overlay tests.

The winner deliberately keeps the original's behavior on every edge. Two losers
did one thing better; graft only if you want it, each is independent of the
winner's diff:

### From c4 (defensive) — best error handling
- **Finite/numeric EV guard** (`c4/replacement.py:34-40`): rejects a non-numeric
  or NaN/inf `distressed_ev` with a clear `TypeError`/`ValueError` instead of
  silently emitting garbage (`NaN > 0` is False, `x - NaN` is NaN, so a poisoned
  EV would currently produce all-null/all-zero rows with no signal). Upstream
  `_distressed_ev` (capstructure.py:79-82) already returns `None` or a real
  float and the caller only invokes the waterfall when `ev` is truthy
  (capstructure.py:111), so in production this guard never fires — it is
  belt-and-suspenders for direct callers and future refactors.
  **Worth grafting** if you expect the function to be reused outside the current
  single caller; otherwise low value.
- **Missing-`amount_musd`-key tolerance** (`c4/replacement.py:62`, `.get(...)`):
  treats an absent key as an unsized break instead of raising `KeyError`. This is
  the one behavior the gate does **not** lock (it is incidental — `scan_tranches`
  always sets the key). Grafting it is a judgment call: more forgiving, but it
  hides a malformed-row bug that a `KeyError` would surface loudly. **Recommend
  NOT grafting** unless you have a concrete non-`scan_tranches` caller.

### From c5 (maximally-testable) — best testability
- **Pure `_settle_tranche(amount, remaining) -> (musd, pct, new_remaining)`**
  (`c5/replacement.py:12-30`): isolates the one-tranche recovery math so it can
  be unit-tested without constructing tranche dicts or driving the cascade. If
  you later add per-tranche rounding/haircut rules (the `ponytail:` note at
  capstructure.py:14-16 anticipates super-priority / structural-subordination
  haircuts), this seam is where they belong. **Worth grafting later** when that
  complexity actually lands — not now (YAGNI; the winner stays a single legible
  function until there's a second reason to split it).

### Not recommended
- c1 (minimal-diff): pure whitespace reflow, no analyst value.
- c3 (performance-first): early-return tail-drain restructures control flow and
  shadows the loop variable for gains its own rationale calls negligible at the
  real <10-tranche scale. Strictly worse legibility for no measurable speed.
- c2 (readability-first): solid, but c6 dominates it on the highest-weighted
  axis (analyst legibility) at a smaller blast radius.
