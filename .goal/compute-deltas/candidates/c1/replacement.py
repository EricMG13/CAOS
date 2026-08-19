def compute_deltas(normalized_financials: dict) -> dict:
    """Period rows + the YoY delta summary + monitoring signals (pure)."""
    rev = normalized_financials.get("revenue") or {}
    eb = normalized_financials.get("adj_ebitda") or {}
    periods = sorted(set(rev) | set(eb), key=sort_key)

    rows: List[dict] = []
    for p in periods:
        r, e = rev.get(p), eb.get(p)
        margin = (round(100 * e / r, 1)
                  if isinstance(r, (int, float)) and r and isinstance(e, (int, float)) else None)
        rows.append({"period": p, "revenue": r, "adj_ebitda": e, "ebitda_margin": margin})

    rev_yoy = _yoy(rows, "revenue")
    eb_yoy = _yoy(rows, "adj_ebitda")
    margins = [r["ebitda_margin"] for r in rows if isinstance(r.get("ebitda_margin"), (int, float))]
    margin_change = round(margins[-1] - margins[-2], 1) if len(margins) >= 2 else None

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
