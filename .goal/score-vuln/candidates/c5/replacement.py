def _leverage_points(leverage: Optional[float]) -> Tuple[int, Optional[str]]:
    """Score the leverage driver in isolation.

    Returns (points, driver_or_None). Non-numeric leverage scores nothing.
    The thresholds are an EXCLUSIVE ladder: >=6.0 dominates >=5.0.
    """
    if isinstance(leverage, (int, float)):
        if leverage >= 6.0:
            return 4, f"high leverage {leverage:g}x"
        if leverage >= 5.0:
            return 2, f"elevated leverage {leverage:g}x"
    return 0, None


def _fragility_points(fragility: Optional[str]) -> Tuple[int, Optional[str]]:
    """Score the fragility driver in isolation.

    Returns (points, driver_or_None). Match is exact and case-sensitive.
    """
    if fragility == "HIGH":
        return 4, "high downside fragility"
    if fragility == "MODERATE":
        return 2, "moderate downside fragility"
    return 0, None


def _band(score: int) -> str:
    """Map a (capped) score onto its risk band in isolation."""
    return "HIGH" if score >= 6 else "MODERATE" if score >= 3 else "LOW"


def score_vulnerability(leverage: Optional[float], fragility: Optional[str]) -> Tuple[int, str, List[str]]:
    lev_points, lev_driver = _leverage_points(leverage)
    frag_points, frag_driver = _fragility_points(fragility)
    drivers: List[str] = [d for d in (lev_driver, frag_driver) if d is not None]
    score = min(_MAX_SCORE, lev_points + frag_points)
    return score, _band(score), drivers
