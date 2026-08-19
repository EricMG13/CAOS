def score_vulnerability(leverage: Optional[float], fragility: Optional[str]) -> Tuple[int, str, List[str]]:
    score = 0
    drivers: List[str] = []
    if isinstance(leverage, (int, float)):
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
    if score > _MAX_SCORE:
        score = _MAX_SCORE
    band = "HIGH" if score >= 6 else "MODERATE" if score >= 3 else "LOW"
    return score, band, drivers
