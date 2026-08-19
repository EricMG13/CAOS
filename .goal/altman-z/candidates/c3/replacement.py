def altman_z_double_prime(
    *,
    current_assets: float,
    current_liabilities: float,
    total_assets: float,
    retained_earnings: float,
    ebit: float,
    total_liabilities: float,
    book_equity: float,
) -> Optional[Tuple[float, str]]:
    """Z'' and its zone, or None when the denominators are unusable (total assets
    or liabilities are zero/negative — the score would be meaningless)."""
    if total_assets <= 0 or total_liabilities <= 0:
        return None
    x1 = (current_assets - current_liabilities) / total_assets
    x2 = retained_earnings / total_assets
    x3 = ebit / total_assets
    x4 = book_equity / total_liabilities
    z = round(3.25 + 6.56 * x1 + 3.26 * x2 + 6.72 * x3 + 1.05 * x4, 2)
    return z, zone_for(z)
