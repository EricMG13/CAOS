# Candidate c1 — minimal-diff rewrite of `recovery_waterfall`

The original is already correct and idiomatic, so the minimal-diff objective is to
change essentially nothing semantically. The single edit is purely cosmetic: the
final `out.append({...})` — which was a two-line literal with a hanging continuation
indent — is reformatted into a one-key-per-line dict so the two recovery keys read
cleanly and the half-even-sensitive `round(100 * recov / amt, 1)` sits on its own
line. This is the smallest delta that nudges legibility without touching logic.

Why it stays equivalent:
- Signature, docstring, control flow, and every variable name are byte-identical.
- The dict passed to `append` is the same `{**t, "recovery_musd": ..., "recovery_pct": ...}`;
  only whitespace/line breaks changed, so key order, values, and `{**t}` copy semantics
  are unchanged (fresh dict, no input mutation).
- `round(x, 1)` (banker's rounding) is preserved verbatim — 250/800 → 31.2 still holds.
- Sticky `broken` flag, `float()` coercion, `remaining > 0` guard, `max(0.0, ...)` floor,
  and `t["amount_musd"]` indexing (KeyError on missing key) are all untouched.
