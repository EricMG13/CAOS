# Merge notes — winner c6, cherry-picks

**Winner:** c6 (domain-legible). `winner.diff` applies cleanly to
`caos/server/engine/macro.py:37-60`. Docstring-and-comments rewrite over the
**identical arithmetic and control flow** — zero behavioral change, proven by
18 contract cases + 3 existing macro tests + full overlays (23).

### From c4 (defensive) — RECOMMENDED graft (real latent-bug fix)
- **NaN/inf rejection via `_finite`** (`c4/replacement.py:10-11`, applied to
  net_debt, EBITDA, coverage). Same bug class already fixed in
  `_interest_runway_months`: a NaN `interest_coverage_ltm` passes
  `isinstance(cov,(int,float))` and `bool(NaN)` is True, so the original divides
  `EBITDA / NaN` → NaN base interest, then NaN stressed coverage, straight into
  the CP-2F payload. `interest_coverage_ltm` is a derived ratio upstream; a
  degenerate filing can yield NaN/inf. Routing it to None is the correct degrade.
  **Recommend grafting** (add `import math` to macro.py's import block, not
  mid-file). One behavioural note to fold into the contract: a NaN coverage would
  then make `base_interest_coverage` None (not 0) — consistent, since NaN is not
  a usable ratio. The cov=0 asymmetry is unaffected (0 is finite).

### From c5 (maximally-testable) — optional, later
- **Pure `_shock_scenario(net_debt, base_interest, eb, bps)`**
  (`c5/replacement.py:1-17`): isolates the per-shock row math so it's unit-testable
  on plain numbers without building an `nf` dict. Worth grafting if the scenario
  set grows (e.g. add −100bps, or a hedged-notional input per the `ponytail:` note
  at macro.py:11-13). Not now — the characterization suite covers it end-to-end.

### Combined option
Winner c6 + c4's `_finite` guard = best legibility *and* closes the NaN hole
(matching what we did for the runway unit). If you pick "graft a cherry-pick",
that's the combination to apply.

### Not recommended
- c1 (minimal-diff): byte-identical no-op — no analyst value.
- c2 (readability-first): strong (good asymmetry comment), but c6 dominates on
  analyst legibility at smaller blast radius.
- c3 (performance-first): negligible hoist for a once-per-synth/2-scenario call;
  adds a float-assoc caveat for no measurable speed.
