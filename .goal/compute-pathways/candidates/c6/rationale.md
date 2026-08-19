# c6 — domain-legible rewrite of `compute_pathways`

Objective: make the downside-stress math provable to a credit analyst by reading.

- **Names the model:** net debt held FLAT under an EBITDA shock, so stressed
  leverage = `current / (1 - shock)` is a first-order sensitivity, NOT a
  cash-sweep / amortizing path. The docstring derives both directions
  (leverage up by `1/(1-s)`, coverage down by `(1-s)`) from `leverage = net debt / EBITDA`.
- **Names the breach threshold:** `_BREACH_X` = 7.0x = the conventional
  leveraged-loan distress marker, annotated inline where it is used and returned.
- **Names `shock_to_breach`:** the smallest EBITDA decline (10/20/30) whose
  stressed leverage first reaches 7.0x inclusive; None if a 30% decline still
  stays under 7.0x.
- **Names the fragility ladder:** breach-by-10% (or already lev>=7) → HIGH,
  by-20% → MODERATE, survives-30% → LOW. The lev>=7 / breach@10 redundancy is
  called out as intentional ("already distressed").
- **Behaviour preserved exactly:** signature, the `(1-s)` denominator/multiplier,
  `round(...)` calls, inclusive `>= 7.0` breach, ladder ordering, and the
  returned dict shape are byte-for-byte equivalent. Only comments/docstring added.
