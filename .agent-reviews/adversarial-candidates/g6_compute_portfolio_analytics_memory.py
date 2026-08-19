def compute_portfolio_analytics(
    positions: List[Dict[str, Any]],
    constraints: List[Dict[str, Any]],
    *,
    as_of: Optional[str],
    portfolio_id: str,
) -> Dict[str, Any]:
    """Bounded deterministic portfolio aggregates for the Portfolio Lab."""
    exposure = compute_exposure(positions)
    compliance = check_constraints(constraints, exposure)
    missing: List[str] = list(exposure.get("missing_dependencies") or [])
    normalized_as_of = normalize_portfolio_as_of(as_of)
    if as_of and normalized_as_of is None:
        missing.append("valid portfolio as_of snapshot")

    rating_mv: Dict[str, Optional[float]] = {}
    maturity_mv: Dict[str, Optional[float]] = {}
    priced_nav: Optional[float] = 0.0
    finite_nav: Optional[float] = 0.0
    unpriced_positions = 0

    for position in positions:
        position_id = str(position.get("id") or position.get("borrower_name") or "unknown")
        price_is_positive = _is_positive_number(position.get("price"))
        if not price_is_positive:
            unpriced_positions += 1

        market_value = position_market_value(position)
        if market_value is None:
            missing.append(f"overflow market value:{position_id}")
            finite_nav = None
            if price_is_positive:
                priced_nav = None
            continue

        next_nav = checked_add(finite_nav, market_value)
        if next_nav is None:
            missing.append("overflow analytics NAV")
        finite_nav = next_nav
        if price_is_positive:
            next_priced = checked_add(priced_nav, market_value)
            if next_priced is None:
                missing.append("overflow priced NAV")
            priced_nav = next_priced
        else:
            missing.append(f"price:{position_id}")

        rating = str(
            position.get("rating_moody")
            or position.get("rating_sp")
            or "Unrated"
        )
        next_rating = checked_add(rating_mv.get(rating, 0.0), market_value)
        if next_rating is None:
            missing.append(f"overflow rating exposure:{rating}")
        rating_mv[rating] = next_rating

        maturity = str(position.get("maturity") or "")
        match = re.search(r"\b(20\d{2})\b", maturity)
        if match:
            year = match.group(1)
            next_maturity = checked_add(maturity_mv.get(year, 0.0), market_value)
            if next_maturity is None:
                missing.append(f"overflow maturity exposure:{year}")
            maturity_mv[year] = next_maturity
        else:
            missing.append(f"maturity:{position_id}")

    rating_rows: List[tuple[str, Optional[float]]] = []
    for rating, value in rating_mv.items():
        percentage = checked_multiply(checked_divide(value, finite_nav), 100.0)
        rating_rows.append((rating, _rounded(percentage, 8)))
    rating_rows.sort(
        key=lambda item: item[1] if is_finite_number(item[1]) else float("-inf"),
        reverse=True,
    )
    if len(rating_rows) > _DISTRIBUTION_LIMIT:
        other: Optional[float] = 0.0
        for index in range(_DISTRIBUTION_LIMIT, len(rating_rows)):
            other = checked_add(other, rating_rows[index][1])
        del rating_rows[_DISTRIBUTION_LIMIT:]
        rating_rows.append(("Other", _rounded(other, 8)))
    rating_distribution = dict(rating_rows)

    if not is_finite_number(finite_nav) or finite_nav == 0:
        missing.append("non-zero portfolio NAV")

    statuses = {status: 0 for status in ("Breach", "Watch", "Pass", "Info")}
    for row in compliance:
        status = row.get("status", "Info")
        statuses[status] = statuses.get(status, 0) + 1

    headroom = []
    for index, row in enumerate(compliance):
        if index == 50:
            break
        headroom.append({
            "code": row.get("code"),
            "status": row.get("status"),
            "headroom": row.get("headroom"),
            "current": row.get("current"),
            "limit_value": row.get("limit_value"),
        })

    maturity_wall: Dict[str, Optional[float]] = {}
    for year in sorted(maturity_mv):
        if len(maturity_wall) == 20:
            break
        maturity_wall[year] = _rounded(maturity_mv[year])

    bounded_compliance = (
        compliance if len(compliance) <= 100 else compliance[:100]
    )
    return {
        "as_of": normalized_as_of.date().isoformat() if normalized_as_of is not None else None,
        "concentration": exposure,
        "rating_distribution": rating_distribution,
        "maturity_wall": maturity_wall,
        "risk_budget": {"status_counts": statuses, "headroom": headroom},
        "liquidity": {
            "priced_nav_pct": _rounded(
                checked_multiply(checked_divide(priced_nav, finite_nav), 100.0)
            ),
            "wa_price": exposure.get("wa_price"),
            "unpriced_positions": unpriced_positions,
        },
        "compliance": bounded_compliance,
        "authority": portfolio_authority(
            method="deterministic-portfolio-v1",
            as_of=as_of,
            portfolio_id=portfolio_id,
        ),
        "missing_dependencies": _bounded_missing(missing),
    }

