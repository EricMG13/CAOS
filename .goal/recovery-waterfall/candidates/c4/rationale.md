# Candidate c4 — defensive / error-handling

Objective: harden `recovery_waterfall` against malformed inputs without changing
any valid-input result. Guards added, each shown to be golden-preserving:

1. **EV type guard** — `distressed_ev` must be a number; raises `TypeError`
   otherwise. Previously `float()` on a non-numeric raised a less-specific error
   mid-computation. All golden EVs (1000, 500, 250, 1, 0, negatives) are ints/
   floats → pass through identically.
2. **EV finiteness guard** — rejects `NaN`/`inf` with a clear `ValueError`. A NaN
   EV silently makes every `remaining > 0` False and every subtraction NaN,
   producing garbage rows; we fail loud instead. No golden case has a non-finite
   EV, so behaviour is unchanged.
3. **Amount validation (`_is_valid_amount`)** — mirrors the live guard
   `isinstance(amt,(int,float)) and amt>0` exactly for every value the live code
   sees: real positives stay sized; `None`/`0`/negative still trigger the sticky
   break (golden None/0.0/-100 cases identical). It additionally rejects NaN/inf
   amounts (a NaN already broke; inf would have leaked as a sized claim — now a
   clean break). `0.0001 @ 1` still recovers `(0.0, 100.0)`; `250/800=31.2`
   (round half-even, unchanged) and all other arithmetic is byte-for-byte the
   same — no Decimal, no half-up.
4. **No mutation / fresh dicts** — output still `{**t, ...}`; inputs untouched.
   Empty list → `[]`. List order preserved; `seniority_rank` ignored.

## Deliberate divergences (documented)

- **Missing `amount_musd` key** — `t.get("amount_musd")` returns `None` instead
  of raising `KeyError`, so a malformed row degrades to null/null (sticky break)
  exactly like an explicit `None` amount. This is the ONE divergence the spec
  permits (incidental, not hard-gated); it is strictly safer for an analyst.
- **`bool` amount** — the live code treats `True` as `>0` (sized). c4 excludes
  `bool` from valid amounts (a tranche size is never True/False), turning it into
  a break. No golden case carries a bool amount, so all gated outputs are
  identical; this only changes a nonsensical input toward the conservative null.
