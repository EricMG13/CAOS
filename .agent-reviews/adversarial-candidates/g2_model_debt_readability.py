"""Review artifact — winning G2 readability candidate.

Replaces caos/server/model_engine_v2.py:774-1229 inside
ModelEngineV2.calculate(); see .agent-reviews/adversarial-codebase-tournament.md.
The wrapper below exists only so this excerpt parses as standalone Python; it
reproduces the enclosing block nesting (class -> calculate -> for period ->
for instrument, point), not production logic. Candidate content is unchanged
below the wrapper.
"""


class ModelEngineV2:
    def calculate(self, payload, *, evaluated_at=None):
        for period in payload.periods:
            for instrument, point in schedule_rows:
                def calculated(
                    field: str,
                    original: Optional[Decimal],
                    formula: Optional[str] = None,
                    *,
                    non_negative: bool = False,
                    negative_message: str = "debt value cannot be negative",
                ) -> Optional[Decimal]:
                    return apply_node(
                        f"{prefix}:{field}",
                        original,
                        nodes,
                        formula,
                        non_negative=non_negative,
                        negative_message=negative_message,
                    )

                instrument_id = instrument.instrument_id
                is_forecast = period.kind in {"forecast", "pro_forma"}
                supplied_opening = _decimal(point.opening_balance)
                opening_formula: Optional[str] = None
                current_effective = _period_order_key(key)[0]
                has_prior_contiguous_period = (
                    instrument_id in prior_closing_by_instrument
                    and prior_effective_by_instrument[instrument_id] < current_effective
                    and prior_effective_by_instrument[instrument_id]
                    == _shift_months(current_effective, -period.months)
                )
                if has_prior_contiguous_period:
                    prior_closing = prior_closing_by_instrument[instrument_id]
                    prior_period = prior_period_by_instrument[instrument_id]
                    opening_discontinuity = (
                        prior_closing is not None
                        and supplied_opening is not None
                        and abs(prior_closing - supplied_opening) > _TOLERANCE
                    )
                    if is_forecast:
                        opening_original = prior_closing
                        opening_formula = f"{prior_period}.closing_balance"
                    else:
                        opening_original = supplied_opening
                    if opening_discontinuity:
                        warnings.append(
                            f"{context}: supplied opening balance does not tie to prior closing balance"
                        )
                        if not is_forecast:
                            gaps.append(
                                f"{context}: sourced opening balance does not tie to "
                                f"{prior_period} closing balance"
                            )
                else:
                    opening_original = supplied_opening
                opening = calculated(
                    "opening_balance",
                    opening_original,
                    opening_formula,
                    non_negative=True,
                )

                draws = debt_value("draws")
                repayments = debt_value("repayments")
                amortization = debt_value("scheduled_amortization")
                commitment = debt_value("commitment")
                benchmark = debt_value("benchmark_rate")
                floor = debt_value(
                    "floor_rate",
                    default=_ZERO,
                    formula="0 when no contractual floor is supplied",
                )
                spread = debt_value("spread_rate")
                coupon = debt_value("coupon_rate")
                commitment_fee = debt_value("commitment_fee_rate")
                pik_rate = debt_value("pik_rate")
                cash_fees = debt_value("cash_fees")
                hedge_effect = debt_value("hedge_effect")
                same_currency = instrument.currency == payload.reporting_currency
                fx_default = Decimal(1) if same_currency else None
                fx_rate = debt_value(
                    "fx_rate",
                    default=fx_default,
                    formula=(
                        "1 when instrument currency equals reporting currency"
                        if same_currency
                        else None
                    ),
                )

                add_missing("opening_balance", opening)
                for field_name, value in (
                    ("draws", draws),
                    ("repayments", repayments),
                    ("scheduled_amortization", amortization),
                    ("commitment_fee_rate", commitment_fee),
                    ("pik_rate", pik_rate),
                    ("cash_fees", cash_fees),
                    ("hedge_effect", hedge_effect),
                ):
                    add_missing(field_name, value)

                rate_type = instrument.rate_type
                if rate_type is None:
                    gaps.append(f"{context}: missing debt input rate_type")
                if rate_type in {"floating", "hybrid"}:
                    add_missing("benchmark_rate", benchmark)
                    add_missing("floor_rate", floor)
                    add_missing("spread_rate", spread)
                if rate_type in {"fixed", "hybrid"}:
                    add_missing("coupon_rate", coupon)
                if fx_rate is None:
                    if same_currency:
                        gaps.append(f"{context}: same-currency FX override cannot be null")
                    else:
                        gaps.append(
                            f"{context}: missing debt input fx_rate for "
                            f"{instrument.currency}/{payload.reporting_currency} conversion"
                        )
                if commitment_fee is not None and commitment_fee != 0:
                    add_missing("commitment", commitment)

                annualization = Decimal(period.months) / Decimal(12)
                supplied_closing = _decimal(point.closing_balance)
                if is_forecast:
                    core_values = (opening, draws, repayments, amortization, pik_rate)
                    if all(value is not None for value in core_values):
                        assert opening is not None
                        assert draws is not None
                        assert repayments is not None
                        assert amortization is not None
                        assert pik_rate is not None
                        base_closing = opening + draws - repayments - amortization
                        pik_factor = pik_rate * annualization
                        denominator = Decimal(1) - pik_factor / Decimal(2)
                        if base_closing < 0:
                            formula_closing = None
                            gaps.append(
                                f"{context}: forecast debt roll-forward produces a negative "
                                "base closing balance"
                            )
                            base_closing = None
                        elif denominator <= 0:
                            formula_closing = None
                            gaps.append(
                                f"{context}: forecast closing balance is undefined because "
                                "the PIK roll-forward denominator is not positive"
                            )
                        else:
                            formula_closing = (
                                base_closing + pik_factor * opening / Decimal(2)
                            ) / denominator
                    else:
                        base_closing = None
                        formula_closing = None

                    if (
                        supplied_closing is not None
                        and formula_closing is not None
                        and abs(supplied_closing - formula_closing) > _TOLERANCE
                    ):
                        warnings.append(
                            f"{context}: supplied closing balance does not tie to derived forecast close"
                        )

                    def override_value(field: str) -> tuple[bool, Optional[Decimal]]:
                        override = active_overrides.get(f"{prefix}:{field}")
                        if override is None:
                            return False, None
                        if override.value_type == "null":
                            return True, None
                        return True, _decimal(override.value)

                    closing_overridden, closing_override = override_value("closing_balance")
                    expected_overridden, expected_override = override_value(
                        "expected_closing_balance"
                    )
                    pik_overridden, pik_override = override_value("pik_interest")
                    average_overridden, average_override = override_value("average_balance")
                    if closing_overridden:
                        closing_candidate = closing_override
                    elif expected_overridden:
                        closing_candidate = expected_override
                    elif pik_overridden:
                        closing_candidate = (
                            None
                            if base_closing is None or pik_override is None
                            else base_closing + pik_override
                        )
                    elif average_overridden:
                        closing_candidate = (
                            None
                            if base_closing is None
                            or average_override is None
                            or pik_rate is None
                            else base_closing + average_override * pik_rate * annualization
                        )
                    else:
                        closing_candidate = formula_closing
                else:
                    closing = calculated(
                        "closing_balance",
                        supplied_closing,
                        non_negative=True,
                    )
                    add_missing("closing_balance", closing)
                    closing_candidate = closing

                average_original = (
                    None
                    if opening is None or closing_candidate is None
                    else (opening + closing_candidate) / Decimal(2)
                )
                average = calculated(
                    "average_balance",
                    average_original,
                    "(opening_balance + closing_balance) / 2",
                    non_negative=True,
                )
                pik_original = (
                    None
                    if average is None or pik_rate is None
                    else average * pik_rate * annualization
                )
                pik_interest = calculated(
                    "pik_interest",
                    pik_original,
                    "average_balance * pik_rate * months / 12",
                )
                if is_forecast:
                    expected_original = (
                        None
                        if base_closing is None or pik_interest is None
                        else base_closing + pik_interest
                    )
                else:
                    expected_components = (
                        opening,
                        draws,
                        pik_interest,
                        repayments,
                        amortization,
                    )
                    expected_original = (
                        None
                        if any(value is None for value in expected_components)
                        else opening + draws + pik_interest - repayments - amortization
                    )
                expected = calculated(
                    "expected_closing_balance",
                    expected_original,
                    "opening_balance + draws + pik_interest - repayments - scheduled_amortization",
                    non_negative=True,
                )
                if is_forecast:
                    closing = calculated(
                        "closing_balance",
                        expected,
                        "expected_closing_balance",
                        non_negative=True,
                    )

                residual_original = (
                    None if closing is None or expected is None else closing - expected
                )
                residual = calculated(
                    "rollforward_residual",
                    residual_original,
                    "closing_balance - expected_closing_balance",
                )
                if residual_original is not None and abs(residual_original) > _TOLERANCE:
                    warnings.append(
                        f"{context}: debt roll-forward residual {_number(residual_original)}"
                    )
                    gaps.append(
                        f"{context}: debt roll-forward does not tie; residual "
                        f"{_number(residual_original)} exceeds tolerance {_number(_TOLERANCE)}"
                    )

                if rate_type == "fixed":
                    benchmark_interest_original = _ZERO
                    margin_interest_original = _ZERO
                elif rate_type in {"floating", "hybrid"}:
                    benchmark_interest_original = (
                        None
                        if average is None or benchmark is None or floor is None
                        else average * max(benchmark, floor) * annualization
                    )
                    margin_interest_original = (
                        None
                        if average is None or spread is None
                        else average * spread * annualization
                    )
                else:
                    benchmark_interest_original = None
                    margin_interest_original = None
                benchmark_interest = calculated(
                    "benchmark_interest",
                    benchmark_interest_original,
                    "average_balance * max(benchmark_rate, floor_rate) * months / 12",
                )
                margin_interest = calculated(
                    "margin_interest",
                    margin_interest_original,
                    "average_balance * spread_rate * months / 12",
                )

                if rate_type == "floating":
                    coupon_interest_original = _ZERO
                elif rate_type in {"fixed", "hybrid"}:
                    coupon_interest_original = (
                        None
                        if average is None or coupon is None
                        else average * coupon * annualization
                    )
                else:
                    coupon_interest_original = None
                coupon_interest = calculated(
                    "coupon_interest",
                    coupon_interest_original,
                    "average_balance * coupon_rate * months / 12",
                )

                if average is None or commitment_fee is None or cash_fees is None:
                    fees_original = None
                elif commitment_fee == 0:
                    fees_original = cash_fees
                elif commitment is None:
                    fees_original = None
                else:
                    undrawn = max(_ZERO, commitment - average)
                    fees_original = undrawn * commitment_fee * annualization + cash_fees
                fees = calculated(
                    "fees",
                    fees_original,
                    "max(0, commitment - average_balance) * commitment_fee_rate * months / 12 + cash_fees",
                )

                cash_components = (
                    benchmark_interest,
                    margin_interest,
                    coupon_interest,
                    fees,
                    hedge_effect,
                )
                local_cash_interest = (
                    None
                    if any(value is None for value in cash_components)
                    else sum(cash_components, _ZERO)
                )
                fx_effect_original = (
                    None
                    if local_cash_interest is None or fx_rate is None
                    else local_cash_interest * (fx_rate - Decimal(1))
                )
                fx_effect = calculated(
                    "fx_effect",
                    fx_effect_original,
                    "local_cash_interest * (fx_rate - 1)",
                )
                cash_interest_original = (
                    None
                    if local_cash_interest is None or fx_effect is None
                    else local_cash_interest + fx_effect
                )
                cash_interest = calculated(
                    "cash_interest",
                    cash_interest_original,
                    "benchmark_interest + margin_interest + coupon_interest + fees + hedge_effect + fx_effect",
                    non_negative=True,
                    negative_message="cash interest must be a non-negative expense",
                )
                debt_reporting_original = (
                    None if closing is None or fx_rate is None else closing * fx_rate
                )
                debt_reporting = calculated(
                    "debt_reporting_currency",
                    debt_reporting_original,
                    "closing_balance * fx_rate",
                    non_negative=True,
                )

                derived_values = (
                    ("closing_balance", closing),
                    ("average_balance", average),
                    ("expected_closing_balance", expected),
                    ("rollforward_residual", residual),
                    ("benchmark_interest", benchmark_interest),
                    ("margin_interest", margin_interest),
                    ("coupon_interest", coupon_interest),
                    ("fees", fees),
                    ("pik_interest", pik_interest),
                    ("fx_effect", fx_effect),
                    ("cash_interest", cash_interest),
                    ("debt_reporting_currency", debt_reporting),
                )
                for field_name, value in derived_values:
                    if value is None:
                        gaps.append(f"{context}: calculated debt field {field_name} is unavailable")

                if debt_reporting is None or cash_interest is None:
                    complete_debt = False
                else:
                    reporting_debt_values.append(debt_reporting)
                    debt_cash_interest_values.append(cash_interest)
                prior_closing_by_instrument[instrument_id] = closing
                prior_period_by_instrument[instrument_id] = key
                prior_effective_by_instrument[instrument_id] = current_effective
                instrument_results.append(DebtInstrumentCalculation(
                    instrument_id=instrument_id,
                    period_key=key,
                    opening_balance=_number(opening),
                    closing_balance=_number(closing),
                    average_balance=_number(average),
                    expected_closing_balance=_number(expected),
                    rollforward_residual=_number(residual),
                    benchmark_interest=_number(benchmark_interest),
                    margin_interest=_number(margin_interest),
                    coupon_interest=_number(coupon_interest),
                    fees=_number(fees),
                    pik_interest=_number(pik_interest),
                    hedge_effect=(
                        _number(hedge_effect)
                        if opening is not None and closing is not None
                        else None
                    ),
                    fx_effect=_number(fx_effect),
                    cash_interest=_number(cash_interest),
                    debt_reporting_currency=_number(debt_reporting),
                ))
