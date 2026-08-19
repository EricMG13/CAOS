# Merge notes — winner c6, cherry-picks

**Winner:** c6 (domain-legible). `winner.diff` applies cleanly to
`caos/server/engine/liquidity.py:38-52`. It is a docstring-and-comments rewrite
over the **identical arithmetic and control flow** as the original — zero
behavioral change, proven by the 19 hard golden cases + 4 existing liquidity
tests + full overlays (23).

### From c4 (defensive) — RECOMMENDED graft (real latent-bug fix)
- **NaN/inf rejection via `_finite_number`** (`c4/replacement.py:4-10`, applied
  in guards a & b). This is not belt-and-suspenders — it closes a genuine hole:
  a NaN `interest_coverage_ltm` **passes** the original `isinstance(cov,(int,
  float))` test, and `bool(NaN)` is `True`, so the truthiness guard lets it
  through; the code then computes `EBITDA / NaN = NaN` and emits a NaN cash
  interest + NaN months into the CP-2E payload. `interest_coverage_ltm` is a
  derived ratio upstream (EBITDA/interest); a degenerate filing with zero or
  missing interest can produce NaN/inf. Routing it to `(None,None)` is the
  correct degrade. **Recommend grafting** the `_finite_number` guard onto the
  winner. (Trade-off: adds a mid-file `import math` + a small helper — the only
  reason it's a graft decision and not already in the winner is c6 optimised for
  legibility, not hardening.)
- `getattr(cp1, "runtime_output", None)` (`c4:30`): tolerates a payload lacking
  the attribute. Lower value — the one caller always passes a real ModulePayload.
  Optional.

### From c5 (maximally-testable) — optional, later
- **Pure `_runway(liquidity, ebitda, coverage)`** (`c5/replacement.py:1-26`):
  isolates the math + divide-by-zero guards so they're unit-testable on plain
  numbers without constructing a CP-1 ModulePayload. Worth grafting **if** you
  add the NaN guard above and want to test the hardening in isolation, or if the
  formula later grows (e.g. blended cash + PIK interest). Not now — the winner's
  characterization suite already covers the math end-to-end (YAGNI).

### Combined option
Winner c6 + c4's `_finite_number` guard = best legibility *and* best safety. If
you pick "graft a cherry-pick", that's the combination I'd apply: keep c6's
docstring/structure, route NaN/inf coverage·ebitda·liquidity to `(None,None)`.

### Not recommended
- c1 (minimal-diff): one-line split, no analyst value.
- c2 (readability-first): strong, but c6 dominates on the highest-weighted axis
  (analyst legibility) at equal blast radius; both carry the rounding-order note.
- c3 (performance-first): guard reorder for negligible gain; adds a "still
  equivalent?" question for no measurable speed.
