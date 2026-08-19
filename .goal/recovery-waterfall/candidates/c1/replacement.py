def recovery_waterfall(tranches: List[dict], distressed_ev: float) -> List[dict]:
    """Absolute-priority distribution of ``distressed_ev`` senior→junior.

    Each sized tranche recovers ``min(claim, remaining value)``; the remainder
    cascades down. An unsized tranche (no stated amount) BREAKS the waterfall: its
    own recovery is null and — because an unknown senior claim makes the value
    cascading past it indeterminate — every tranche junior to it is null too.
    Scoring juniors against the full remaining EV as if the unsized senior claimed
    nothing would over-credit them (the prior behaviour, fixed here)."""
    remaining = float(distressed_ev)
    out = []
    broken = False  # an unsized claim makes everything junior to it indeterminate
    for t in tranches:
        amt = t["amount_musd"]
        if not (isinstance(amt, (int, float)) and amt > 0):
            broken = True
        if broken:
            out.append({**t, "recovery_musd": None, "recovery_pct": None})
            continue
        recov = min(amt, remaining) if remaining > 0 else 0.0
        remaining = max(0.0, remaining - amt)
        out.append({
            **t,
            "recovery_musd": round(recov, 1),
            "recovery_pct": round(100 * recov / amt, 1),
        })
    return out
