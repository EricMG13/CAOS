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
    or liabilities are zero/negative — the score would be meaningless).

    Factored into pure, independently-testable helpers: ``_z_double_prime_terms``
    returns the four X-ratios on plain numbers, ``_z_double_prime_score`` folds
    them into the weighted Z'' sum, and ``zone_for`` (module sibling) maps the
    score to a zone. The public signature and the (z, zone) contract are unchanged.
    """
    if total_assets <= 0 or total_liabilities <= 0:
        return None
    x1, x2, x3, x4 = _z_double_prime_terms(
        current_assets=current_assets,
        current_liabilities=current_liabilities,
        total_assets=total_assets,
        retained_earnings=retained_earnings,
        ebit=ebit,
        total_liabilities=total_liabilities,
        book_equity=book_equity,
    )
    z = _z_double_prime_score(x1, x2, x3, x4)
    return z, zone_for(z)


def _z_double_prime_terms(
    *,
    current_assets: float,
    current_liabilities: float,
    total_assets: float,
    retained_earnings: float,
    ebit: float,
    total_liabilities: float,
    book_equity: float,
) -> Tuple[float, float, float, float]:
    """The four Altman Z'' ratios (X1, X2, X3, X4) as a pure function of inputs.

    X1 = (current_assets - current_liabilities) / total_assets  [working capital / TA]
    X2 = retained_earnings / total_assets
    X3 = ebit / total_assets
    X4 = book_equity / total_liabilities  [note: divides by liabilities, not assets]

    Callers guarantee non-zero denominators; exercised directly in tests.
    """
    x1 = (current_assets - current_liabilities) / total_assets
    x2 = retained_earnings / total_assets
    x3 = ebit / total_assets
    x4 = book_equity / total_liabilities
    return x1, x2, x3, x4


def _z_double_prime_score(x1: float, x2: float, x3: float, x4: float) -> float:
    """The Z'' weighted sum on plain ratios, rounded to 2 dp (banker's rounding).

    Z'' = 3.25 + 6.56·X1 + 3.26·X2 + 6.72·X3 + 1.05·X4
    """
    return round(3.25 + 6.56 * x1 + 3.26 * x2 + 6.72 * x3 + 1.05 * x4, 2)
