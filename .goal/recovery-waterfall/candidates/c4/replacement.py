def recovery_waterfall(tranches: List[dict], distressed_ev: float) -> List[dict]:
    """Absolute-priority distribution of ``distressed_ev`` senior→junior.

    Each sized tranche recovers ``min(claim, remaining value)``; the remainder
    cascades down. An unsized tranche (no stated amount) BREAKS the waterfall: its
    own recovery is null and — because an unknown senior claim makes the value
    cascading past it indeterminate — every tranche junior to it is null too.
    Scoring juniors against the full remaining EV as if the unsized senior claimed
    nothing would over-credit them (the prior behaviour, fixed here).

    Defensive hardening (behaviour on valid inputs is unchanged):
      * ``distressed_ev`` is validated as a finite number before coercion. A
        non-numeric or NaN/inf EV would otherwise silently poison every
        comparison (``NaN > 0`` is False, ``x - NaN`` is NaN), so we raise a
        clear ``TypeError``/``ValueError`` instead of emitting garbage. Valid
        ints/floats coerce via ``float()`` exactly as before.
      * A MISSING ``amount_musd`` key is treated as an unsized tranche (sticky
        break) rather than raising ``KeyError``. This is a deliberate, documented
        divergence from the live function — see rationale.md. It is strictly more
        tolerant: a malformed row degrades to null/null exactly like an explicit
        ``None`` amount, which is the safest read for an analyst.
      * The amount guard also rejects NaN/inf amounts (``not isfinite``) and
        ``bool`` (a tranche size is never ``True``/``False``); both trigger the
        same sticky break. A real positive number passes untouched, so the
        golden cases are unaffected.
    """
    import math

    # Validate the EV up front: it must be a real, finite number. We exclude
    # bool (an int subclass) because an EV is never True/False, and reject
    # NaN/inf which would silently break every downstream comparison.
    if isinstance(distressed_ev, bool) or not isinstance(distressed_ev, (int, float)):
        raise TypeError(
            f"distressed_ev must be a number, got {type(distressed_ev).__name__}"
        )
    if not math.isfinite(distressed_ev):
        raise ValueError(f"distressed_ev must be finite, got {distressed_ev!r}")

    remaining = float(distressed_ev)
    out = []
    broken = False  # an unsized claim makes everything junior to it indeterminate
    for t in tranches:
        # Tolerate a missing key by treating the tranche as unsized (deliberate,
        # safe divergence from the live KeyError); for any present value we keep
        # the original semantics.
        amt = t.get("amount_musd")
        if not _is_valid_amount(amt):
            broken = True
        if broken:
            out.append({**t, "recovery_musd": None, "recovery_pct": None})
            continue
        recov = min(amt, remaining) if remaining > 0 else 0.0
        remaining = max(0.0, remaining - amt)
        out.append({**t, "recovery_musd": round(recov, 1),
                    "recovery_pct": round(100 * recov / amt, 1)})
    return out


def _is_valid_amount(amt) -> bool:
    """A tranche amount is "sized" iff it is a finite, strictly-positive number.

    Mirrors the live guard ``isinstance(amt, (int, float)) and amt > 0`` exactly
    for all values the live function ever sees (real positives pass; None/0/
    negative fail → sticky break). It additionally rejects NaN/inf amounts, which
    the live ``amt > 0`` test would silently mishandle (``NaN > 0`` is False so a
    NaN already broke, but inf would have leaked through as a sized claim). bool
    is excluded because a tranche size is never True/False — note the live code
    treated ``True`` as >0; flipping that to a break is the conservative read and
    no golden case carries a bool amount."""
    import math
    if isinstance(amt, bool):
        return False
    if not isinstance(amt, (int, float)):
        return False
    if not math.isfinite(amt):
        return False
    return amt > 0
