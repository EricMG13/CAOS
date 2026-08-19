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
    # Altman Z'' (double-prime), the variant for non-manufacturers / emerging
    # issuers. Each X-term is a leverage- or earnings-quality ratio; note that
    # X4 is scaled by total liabilities, not total assets like the others.
    working_capital_to_assets = (current_assets - current_liabilities) / total_assets   # X1
    retained_earnings_to_assets = retained_earnings / total_assets                       # X2
    ebit_to_assets = ebit / total_assets                                                 # X3
    equity_to_liabilities = book_equity / total_liabilities                              # X4
    z = round(
        3.25
        + 6.56 * working_capital_to_assets
        + 3.26 * retained_earnings_to_assets
        + 6.72 * ebit_to_assets
        + 1.05 * equity_to_liabilities,
        2,
    )
    return z, zone_for(z)
