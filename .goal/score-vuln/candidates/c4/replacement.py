def score_vulnerability(leverage: Optional[float], fragility: Optional[str]) -> Tuple[int, str, List[str]]:
    score = 0
    drivers: List[str] = []
    # Leverage contributes only for genuine numeric magnitudes. The isinstance
    # guard already excludes None/str. Two further cases pass isinstance but
    # intentionally contribute nothing, so we exclude them explicitly to make
    # that intent legible (behaviour is unchanged — both already failed >= 6.0
    # and >= 5.0 below):
    #   * bool: True/False are int subclasses; a flag is not a leverage ratio.
    #   * NaN: NaN >= 6.0 and NaN >= 5.0 are both False, so it never scored.
    # `n != n` is the stdlib-free NaN test (true only for NaN), avoiding a
    # `math` import for this single guard.
    if isinstance(leverage, (int, float)) and not isinstance(leverage, bool) and leverage == leverage:
        if leverage >= 6.0:
            score += 4
            drivers.append(f"high leverage {leverage:g}x")
        elif leverage >= 5.0:
            score += 2
            drivers.append(f"elevated leverage {leverage:g}x")
    if fragility == "HIGH":
        score += 4
        drivers.append("high downside fragility")
    elif fragility == "MODERATE":
        score += 2
        drivers.append("moderate downside fragility")
    score = min(_MAX_SCORE, score)
    band = "HIGH" if score >= 6 else "MODERATE" if score >= 3 else "LOW"
    return score, band, drivers
