def _is_sized(amount: object) -> bool:
    """True iff ``amount`` is a usable claim (numeric and strictly positive).

    Owns the break decision in isolation: ``None``, ``0``, negatives and
    non-numeric values are all unsized and trigger the sticky waterfall break.
    (``bool`` is a subclass of ``int``; that quirk is inherited from the
    original ``isinstance(amt, (int, float))`` test and preserved deliberately.)
    """
    return isinstance(amount, (int, float)) and amount > 0


def _settle_tranche(amount: float, remaining: float) -> Tuple[float, float, float]:
    """Settle ONE sized tranche against the cascading ``remaining`` value.

    Pure function — no I/O, no shared state. Returns
    ``(recovery_musd, recovery_pct, new_remaining)``:

    * ``recovery_musd``  — ``min(claim, remaining)`` (0.0 when nothing is left),
      rounded ``round(x, 1)`` (banker's rounding over the float repr).
    * ``recovery_pct``   — ``100 * recovery / amount`` against the tranche's OWN
      claim, rounded the same way. Caller guarantees ``amount > 0`` (see
      ``_is_sized``), so the denominator is safe.
    * ``new_remaining``  — ``remaining`` reduced by the FULL claim, floored at 0.

    The recovery is computed from the *unrounded* ``recov`` so the percentage
    matches the live function exactly (e.g. 250/800 -> 31.2, not 31.3).
    """
    recov = min(amount, remaining) if remaining > 0 else 0.0
    new_remaining = max(0.0, remaining - amount)
    return round(recov, 1), round(100 * recov / amount, 1), new_remaining


def recovery_waterfall(tranches: List[dict], distressed_ev: float) -> List[dict]:
    """Absolute-priority distribution of ``distressed_ev`` senior→junior.

    Each sized tranche recovers ``min(claim, remaining value)``; the remainder
    cascades down. An unsized tranche (no stated amount) BREAKS the waterfall: its
    own recovery is null and — because an unknown senior claim makes the value
    cascading past it indeterminate — every tranche junior to it is null too.
    Scoring juniors against the full remaining EV as if the unsized senior claimed
    nothing would over-credit them (the prior behaviour, fixed here).

    Thin orchestrator: the per-tranche math lives in the pure helper
    ``_settle_tranche`` and the break decision in ``_is_sized``; this body only
    walks the list in order, threads ``remaining`` forward, and latches the
    sticky break. List order is authoritative — ``seniority_rank`` is ignored.
    """
    remaining = float(distressed_ev)
    out: List[dict] = []
    broken = False  # an unsized claim makes everything junior to it indeterminate
    for t in tranches:
        if not _is_sized(t["amount_musd"]):
            broken = True
        if broken:
            out.append({**t, "recovery_musd": None, "recovery_pct": None})
            continue
        recovery_musd, recovery_pct, remaining = _settle_tranche(t["amount_musd"], remaining)
        out.append({**t, "recovery_musd": recovery_musd, "recovery_pct": recovery_pct})
    return out
