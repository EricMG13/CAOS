def compute_deltas(normalized_financials: dict) -> dict:
    """Period rows + the YoY delta summary + monitoring signals (pure)."""
    rev = normalized_financials.get("revenue") or {}
    eb = normalized_financials.get("adj_ebitda") or {}
    periods = sorted(rev.keys() | eb.keys(), key=sort_key)

    rows: List[dict] = []
    # Track the last two numeric margins in O(1) state instead of re-scanning
    # `rows` for them afterward — single pass while the rows are built.
    prev_margin: Optional[float] = None
    last_margin: Optional[float] = None
    for p in periods:
        r, e = rev.get(p), eb.get(p)
        if isinstance(r, (int, float)) and r and isinstance(e, (int, float)):
            margin = round(100 * e / r, 1)
            prev_margin, last_margin = last_margin, margin
        else:
            margin = None
        rows.append({"period": p, "revenue": r, "adj_ebitda": e, "ebitda_margin": margin})

    rev_yoy = _yoy(rows, "revenue")
    eb_yoy = _yoy(rows, "adj_ebitda")
    margin_change = (round(last_margin - prev_margin, 1)
                     if last_margin is not None and prev_margin is not None else None)

    summary = {
        "revenue_growth_pct": rev_yoy[0] if rev_yoy else None,
        "ebitda_growth_pct": eb_yoy[0] if eb_yoy else None,
        "margin_change_pp": margin_change,
        "latest_period": rows[-1]["period"] if rows else None,
        "prior_period": rows[-2]["period"] if len(rows) >= 2 else None,
    }

    signals: List[str] = []
    if rev_yoy and rev_yoy[0] < 0:
        signals.append(f"Revenue declined {abs(rev_yoy[0]):g}% YoY ({rev_yoy[1]}→{rev_yoy[2]}).")
    if eb_yoy and eb_yoy[0] < 0:
        signals.append(f"Adjusted EBITDA declined {abs(eb_yoy[0]):g}% YoY ({eb_yoy[1]}→{eb_yoy[2]}).")
    if margin_change is not None and margin_change <= -_MARGIN_COMPRESSION_PP:
        signals.append(f"EBITDA margin compressed {abs(margin_change):g}pp YoY.")

    return {"periods": rows, "summary": summary, "monitoring_signals": signals}
