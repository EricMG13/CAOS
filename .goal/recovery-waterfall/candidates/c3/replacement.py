def recovery_waterfall(tranches: List[dict], distressed_ev: float) -> List[dict]:
    """Absolute-priority distribution of ``distressed_ev`` senior→junior.

    Each sized tranche recovers ``min(claim, remaining value)``; the remainder
    cascades down. An unsized tranche (no stated amount) BREAKS the waterfall: its
    own recovery is null and — because an unknown senior claim makes the value
    cascading past it indeterminate — every tranche junior to it is null too.
    Scoring juniors against the full remaining EV as if the unsized senior claimed
    nothing would over-credit them (the prior behaviour, fixed here)."""
    remaining = float(distressed_ev)
    out: List[dict] = []
    append = out.append  # hoist bound method out of the loop
    for i, t in enumerate(tranches):
        amt = t["amount_musd"]  # KeyError on missing key preserved
        if not (isinstance(amt, (int, float)) and amt > 0):
            # Sticky break: this tranche and every junior tranche are null.
            # Emit the rest in one tight pass and return — no further math.
            append({**t, "recovery_musd": None, "recovery_pct": None})
            for t in tranches[i + 1:]:
                append({**t, "recovery_musd": None, "recovery_pct": None})
            return out
        recov = min(amt, remaining) if remaining > 0.0 else 0.0
        remaining = remaining - amt
        if remaining < 0.0:
            remaining = 0.0
        append({**t, "recovery_musd": round(recov, 1),
                "recovery_pct": round(100 * recov / amt, 1)})
    return out
