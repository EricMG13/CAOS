# Adversarial Rewrite Tournament — Final Code

Production source was not changed. Each block is the verified winning replacement; G10 is the retained incumbent.

## G1 — Core CP engine · Speed

```python
async def execute_run(session: AsyncSession, run: Run) -> None:
    """Execute ``run`` in place; the caller owns the transaction commit."""
    run.status = "running"
    settings = get_settings()
    run_id = run.id
    issuer_id = run.issuer_id
    enabled_module_flags = frozenset(
        flag
        for flag in ("caos_cp_4d_enabled", "caos_cp_2g_enabled")
        if bool(getattr(settings, flag, False))
    )

    run_budget = budget.RunBudget(
        limit=settings.run_token_budget, used=run.tokens_used or 0
    )
    budget.set_budget(run_budget)
    budget.set_run_id(run_id)
    presets.set_mode(run.model_mode)

    synthesizer = get_synthesizer()
    live_synth = synthesizer.name == "live"
    run.model_id = presets.model_for(presets.HEAVY) if live_synth else "fixture"
    run.prompt_version = _stamp_prompt_version(synthesizer.name)

    issuer = await session.get(Issuer, issuer_id)
    issuer_name = issuer.name if issuer else issuer_id
    issuer_index = await build_issuer_index(session, issuer_id)

    async def retrieve(query: str, k: int = 5):
        return rank_with_index(issuer_index, query, k)

    upstream: Dict[str, ModulePayload] = {}
    module_status: Dict[str, str] = {}
    output_rows: Dict[str, ModuleOutput] = {}
    structural_findings: List[Finding] = []
    plan: Optional[RoutePlan] = None
    sem = asyncio.Semaphore(max(1, settings.synth_concurrency))

    def _block_reason(module_id: str) -> Optional[str]:
        if plan is not None and plan.verdict(module_id) == ROUTE_BLOCKED:
            return plan.blocking_reason(module_id) or "Blocked by CP-X route plan."
        spec = REGISTRY.get(module_id)
        deps = spec.depends_on if spec is not None else ()
        blocked_dep = next(
            (dep for dep in deps if module_status.get(dep) in (None, "Blocked")),
            None,
        )
        if blocked_dep is None:
            return None
        return f"Input gate: required upstream {blocked_dep} is missing or Blocked."

    async def _attempt_synth(module_id: str):
        async with sem:
            try:
                return await resolve_binding(
                    RunContext(
                        module_id=module_id,
                        session=session,
                        issuer=issuer,
                        issuer_name=issuer_name,
                        synthesizer=synthesizer,
                        upstream=upstream,
                        retrieve=retrieve,
                        portfolio_id=run.portfolio_id,
                    )
                )
            except SynthesisError as exc:
                return exc
            except Exception as exc:  # noqa: BLE001
                logger.exception("unexpected synth error for %s", module_id)
                return SynthesisError(f"unexpected synth error: {exc}")

    async def _persist_synth_result(module_id: str, result) -> None:
        severity = "CRITICAL" if REGISTRY[module_id].run_blocking else "MATERIAL"
        if isinstance(result, SynthesisError):
            logger.warning("synthesis failed for %s: %s", module_id, result)
            output_rows[module_id], gate_finding = _persist_blocked(
                session,
                run_id,
                module_id,
                f"Synthesis failed: {result}",
                severity=severity,
            )
            structural_findings.append(gate_finding)
            module_status[module_id] = "Blocked"
            return

        payload = result
        errors = validate_payload(payload)
        if errors:
            logger.warning("payload validation failed for %s: %s", module_id, errors)
            output_rows[module_id], gate_finding = _persist_blocked(
                session,
                run_id,
                module_id,
                "Payload failed schema validation: " + "; ".join(errors),
                validation_status="Blocked",
                severity=severity,
            )
            structural_findings.append(gate_finding)
            module_status[module_id] = "Blocked"
            return

        if plan is not None:
            for flag in plan.propagated_flags(module_id):
                if flag not in payload.limitation_flags:
                    payload.limitation_flags.append(flag)

        await _resolve_evidence(payload, retrieve, suppress_sourced=live_synth)
        row = await _persist_output(
            session, run_id, payload, validation_status="Passed"
        )
        output_rows[module_id] = row
        upstream[module_id] = payload

        runtime = payload.runtime_output
        if runtime.get("module_status") != "Blocked":
            module_status[module_id] = "Pending"
            return

        row.qa_status = "Blocked"
        row.committee_status = "Blocked"
        reason = str(
            runtime.get("status_basis") or f"{module_id} source gate blocked"
        )
        gate_finding = _gate_finding(module_id, reason, severity=severity)
        structural_findings.append(gate_finding)
        session.add(
            QAFinding(
                run_id=run_id,
                module_id=gate_finding.module_id,
                finding_id=gate_finding.finding_id,
                severity=gate_finding.severity,
                lane=gate_finding.lane,
                description=gate_finding.description,
                required_remediation=gate_finding.required_remediation,
            )
        )
        module_status[module_id] = "Blocked"

    async def _run_layer(layer: List[str]) -> None:
        session_bound: List[str] = []
        parallel: List[str] = []

        # One partition pass preserves the incumbent ordering: blocked writes first,
        # then session-bound results, then pure results, each in layer order.
        for module_id in layer:
            reason = _block_reason(module_id)
            if reason is not None:
                severity = (
                    "CRITICAL" if REGISTRY[module_id].run_blocking else "MATERIAL"
                )
                output_rows[module_id], gate_finding = _persist_blocked(
                    session, run_id, module_id, reason, severity=severity
                )
                structural_findings.append(gate_finding)
                module_status[module_id] = "Blocked"
            elif module_id in _SESSION_SYNTH:
                session_bound.append(module_id)
            else:
                parallel.append(module_id)

        results: List[Tuple[str, object]] = []
        for module_id in session_bound:
            results.append((module_id, await _attempt_synth(module_id)))
        if parallel:
            gathered = await asyncio.gather(
                *(_attempt_synth(module_id) for module_id in parallel)
            )
            results.extend(zip(parallel, gathered))
        for module_id, result in results:
            await _persist_synth_result(module_id, result)

    try:
        await _run_layer(["CP-0"])

        cp0_payload = upstream.get("CP-0") or ModulePayload(
            module_id="CP-0",
            module_name="SourceReadiness",
            owned_object="source_readiness_assessment",
            runtime_output={},
            confidence="Insufficient Information",
        )
        plan = build_route_plan(cp0_payload, all_specs(enabled_module_flags))
        await _persist_cpx(session, run_id, plan)

        routed = [
            readiness.module_id
            for readiness in plan.readiness
            if readiness.module_id != "CP-0"
            and REGISTRY[readiness.module_id].implemented
            and readiness.readiness != ROUTE_EXCLUDED
        ]
        for layer in _dependency_layers(routed):
            await _run_layer(layer)

        analytical_ids = ["CP-0", *routed]
        produced = [upstream[module_id] for module_id in analytical_ids if module_id in upstream]

        # CP-5B: deterministic lineage and module-specific checks.
        findings = validate_lineage(produced)
        for provider, module_id in (
            (reconciliation_finding, "CP-1"),
            (covlite_finding, "CP-4C"),
            (addback_cap_finding, "CP-4C"),
            (monitoring_finding, "CP-1B"),
            (peer_outlier_finding, "CP-1C"),
            (leverage_plausibility_finding, "CP-1"),
            (leverage_magnitude_finding, "CP-1"),
            (cp1_grounding_finding, "CP-1"),
            (cp1_completeness_finding, "CP-1"),
        ):
            finding = provider(upstream.get(module_id))
            if finding is not None:
                findings.append(finding)

        demo_fix = demo_fixture_finding(issuer_id, upstream.get("CP-1"))
        if demo_fix is not None:
            findings.append(demo_fix)
            cp1_row = output_rows.get("CP-1")
            if (
                cp1_row is not None
                and DEMO_FIXTURE_LIMITATION
                not in (cp1_row.limitation_flags or [])
            ):
                cp1_row.limitation_flags = list(cp1_row.limitation_flags or []) + [
                    DEMO_FIXTURE_LIMITATION
                ]

        if findings:
            session.add_all(
                [
                    QAFinding(
                        run_id=run_id,
                        module_id=finding.module_id,
                        finding_id=finding.finding_id,
                        severity=finding.severity,
                        lane=finding.lane,
                        description=finding.description,
                        affected_claim_id=finding.affected_claim_id,
                        required_remediation=finding.required_remediation,
                    )
                    for finding in findings
                ]
            )
        await _persist_cp5b(session, run_id, produced, findings)

        # CP-5C remains after CP-5B: starting it early would change budget/call order.
        reviewer = get_reviewer()
        council = await reviewer.review(produced)
        if council:
            session.add_all(
                [
                    QAFinding(
                        run_id=run_id,
                        module_id=finding.module_id,
                        finding_id=finding.finding_id,
                        severity=finding.severity,
                        lane=finding.lane,
                        description=finding.description,
                        affected_claim_id=finding.affected_claim_id,
                        required_remediation=finding.required_remediation,
                    )
                    for finding in council
                ]
            )
        findings.extend(council)
        await _persist_cp5c(
            session,
            run_id,
            produced,
            council,
            review_meta=getattr(reviewer, "last_review_meta", None),
        )

        # One index replaces the incumbent O(modules * findings) repeated scan.
        findings_by_module: Dict[str, List[Finding]] = {}
        for finding in findings:
            findings_by_module.setdefault(finding.module_id, []).append(finding)

        no_findings: Tuple[Finding, ...] = ()
        for module_id in analytical_ids:
            if module_status.get(module_id) == "Blocked":
                continue
            status = qa_status_from(
                findings_by_module.get(module_id, no_findings)
            )
            row = output_rows[module_id]
            row.qa_status = status
            row.committee_status = committee_status_from(status, row.confidence)
            module_status[module_id] = status

        _apply_blocked_upstream_cascade(
            analytical_ids, module_status, output_rows
        )
        await _persist_cp5(
            session, run_id, findings + structural_findings, module_status
        )

        # Project only QA-eligible facts. Staging order remains CP-1 then CP-2.
        cp1_facts: List[dict] = []
        cp1 = upstream.get("CP-1")
        if cp1 is not None and output_rows["CP-1"].qa_status != "Blocked":
            cp1_facts = extract_facts(
                run_id,
                cp1,
                output_rows["CP-1"].qa_status,
                is_reference_issuer=issuer_id == REFERENCE_ISSUER_ID,
            )
            if cp1_facts:
                session.add_all(
                    [MetricFact(issuer_id=issuer_id, **fact) for fact in cp1_facts]
                )

        cp2_facts: List[dict] = []
        cp2 = upstream.get("CP-2")
        if cp2 is not None and output_rows["CP-2"].qa_status != "Blocked":
            cp2_facts = extract_cost_facts(
                run_id, cp2, output_rows["CP-2"].qa_status
            )
            if cp2_facts:
                session.add_all(
                    [MetricFact(issuer_id=issuer_id, **fact) for fact in cp2_facts]
                )

        # One database round-trip, still gated independently per module on an
        # actual replacement write. Seed facts and untouched module facts survive.
        superseded_modules = []
        if cp1_facts:
            superseded_modules.append("CP-1")
        if cp2_facts:
            superseded_modules.append("CP-2")
        if superseded_modules:
            await session.execute(
                delete(MetricFact).where(
                    MetricFact.issuer_id == issuer_id,
                    MetricFact.module_id.in_(superseded_modules),
                    MetricFact.provenance.in_(
                        ("run", "fixture", "demo_fixture")
                    ),
                    MetricFact.run_id != run_id,
                )
            )

        rollup_ids = [
            module_id
            for module_id in analytical_ids
            if module_id in module_status and REGISTRY[module_id].run_blocking
        ]
        run.qa_status = roll_up_qa_status(
            [module_status[module_id] for module_id in rollup_ids]
        )
        run.committee_status = committee_status_from(
            run.qa_status,
            worst_confidence(
                [
                    upstream[module_id].confidence
                    for module_id in rollup_ids
                    if module_id in upstream
                ]
            ),
        )
        run.tokens_used = run_budget.used
        if run_budget.budget_exhausted:
            run.error = (
                "Degraded: Ran out of LLM token budget. "
                "Some analytical modules were skipped."
            )
        elif run_budget.degraded:
            run.error = (
                "Degraded: LLM rate limits/overloads forced fallback to cheaper models."
            )
        else:
            run.error = None
        run.status = "complete"
        run.completed_at = _now()
    except Exception:
        logger.exception("run %s failed", run_id)
        run.status = "failed"
        run.tokens_used = run_budget.used
        raise
```

## G2 — Model debt roll-forward · Readability

```python
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
```

## G3 — Identity · Readability

```python
async def get_identity(
    request: Request, db: AsyncSession = Depends(get_db, scope="function")
) -> CallerIdentity:
    """Resolve a verified profile, proxy principal, or development identity."""
    settings = get_settings()
    deployed = is_deployed(settings)

    # Every deployed request proves edge transit before any identity is trusted.
    if deployed and settings.edge_proxy_secret:
        presented = request.headers.get("x-edge-authorization", "")
        if not hmac.compare_digest(
            presented.encode("utf-8", "ignore"),
            settings.edge_proxy_secret.encode("utf-8"),
        ):
            raise HTTPException(401, "Request did not carry a valid edge credential.")

    token = request.cookies.get(COOKIE_NAME)
    if token:
        data = read_session_token(token, settings.session_secret)
        if data and data.get("id") and data.get("name"):
            analyst_id = sanitize_field(data["id"])
            analyst = await db.get(Analyst, analyst_id)
            if analyst is not None and analyst.token_version == data.get("v", 0):
                cookie_email = sanitize_field(data.get("email", ""))
                forwarded_email = request.headers.get("x-forwarded-email")
                same_principal = (
                    not deployed
                    or not forwarded_email
                    or cookie_email.lower() == forwarded_email.strip().lower()
                )
                if same_principal:
                    return CallerIdentity(
                        id=analyst_id,
                        email=cookie_email,
                        full_name=sanitize_field(data["name"]),
                        role=getattr(analyst, "role", None) or "analyst",
                        source="profile",
                        team_id=analyst.team_id,
                    )

    email = request.headers.get("x-forwarded-email")
    user = request.headers.get("x-forwarded-user")
    if not email and not user:
        if deployed:
            raise HTTPException(
                401,
                "No forwarded identity — request did not pass the auth proxy / edge.",
            )
        return _LOCAL_DEV

    persisted_analyst = None
    if email and hasattr(db, "execute"):
        persisted_analyst = (
            await db.execute(
                select(Analyst).where(func.lower(Analyst.email) == email.strip().lower())
            )
        ).scalar_one_or_none()

    username = request.headers.get("x-forwarded-preferred-username") or email or user
    return CallerIdentity(
        id=sanitize_field(user or email or "unknown"),
        email=sanitize_field(email or user or "unknown"),
        full_name=sanitize_field(username or "Authenticated User"),
        role=getattr(persisted_analyst, "role", None) or "analyst",
        source="proxy",
        team_id=persisted_analyst.team_id if persisted_analyst is not None else None,
    )
```

## G4 — Lineage reconciliation · Speed

```python
async def reconcile_lineage(
    db: AsyncSession,
    *,
    mode: ReconciliationMode,
    limit: int = 100,
    cursor: Optional[str] = None,
) -> ReconciliationResult:
    """Reconcile a stable page of contexts; apply commits once per context."""
    if mode not in {"dry-run", "apply", "verify"}:
        raise ValueError("mode must be dry-run, apply, or verify")
    if limit < 1 or limit > 1000:
        raise ValueError("limit must be between 1 and 1000")
    result = ReconciliationResult(mode=mode)
    stmt = (
        select(AnalysisContextRecord)
        .order_by(AnalysisContextRecord.id)
        .limit(limit + 1)
    )
    if cursor:
        stmt = stmt.where(AnalysisContextRecord.id > cursor)
    rows = list((await db.execute(stmt)).scalars().all())
    page = rows[:limit]
    if len(rows) > limit and page:
        result.next_cursor = page[-1].id

    for context in page:
        result.scanned_contexts += 1
        analyst = await db.get(Analyst, context.analyst_id)
        missing_owner = analyst is None
        caller = (
            _owner_identity(analyst)
            if analyst is not None
            else _fallback_owner_identity(context.analyst_id)
        )
        context_authorized = True
        if missing_owner and tenancy_enabled():
            result.unauthorized_refs += 1
            result.integrity_failures += 1
            context_authorized = False
        for issuer_id in dict.fromkeys(context.issuer_ids or []):
            if not issuer_visible(caller, await db.get(Issuer, issuer_id)):
                result.unauthorized_refs += 1
                context_authorized = False
        if context.portfolio_scope and not portfolio_visible(
            caller, await db.get(Portfolio, context.portfolio_scope)
        ):
            result.unauthorized_refs += 1
            context_authorized = False

        artifacts = context.artifacts or {}
        refs: dict[tuple[str, str, str], ArtifactRef] = {}
        ref_base_keys: set[tuple[str, str]] = set()
        edges: dict[tuple, tuple[ArtifactRef, ArtifactRef, str]] = {}

        def ref_key(ref: ArtifactRef) -> tuple[str, str, str]:
            return ref.kind, ref.id, ref.version or ""

        def add_ref(ref: ArtifactRef) -> None:
            refs[ref_key(ref)] = ref
            ref_base_keys.add((ref.kind, ref.id))

        def add_edge(artifact: ArtifactRef, parent: ArtifactRef, transform: str) -> None:
            add_ref(artifact)
            add_ref(parent)
            edges[(
                artifact.kind, artifact.id, artifact.version,
                parent.kind, parent.id, parent.version, transform,
            )] = (artifact, parent, transform)

        # Verify every persisted v2 row in scope, including manually inserted or
        # partially migrated rows that are not reconstructable as a proposal.
        persisted_edges = (await db.execute(select(LineageEdge).where(
            LineageEdge.context_id == context.id,
            LineageEdge.v2_idempotency_key.is_not(None),
        ))).scalars().all()
        for edge in persisted_edges:
            if edge.analyst_id != context.analyst_id:
                result.unauthorized_refs += 1
            try:
                artifact_prefix, artifact_separator, artifact_suffix = edge.artifact_id.partition(":")
                parent_prefix, parent_separator, parent_suffix = edge.parent_id.partition(":")
                if (
                    artifact_separator != ":"
                    or parent_separator != ":"
                    or artifact_prefix != edge.artifact_kind
                    or parent_prefix != edge.parent_kind
                ):
                    raise ValueError("canonical prefix mismatch")
                artifact_ref = ArtifactRef(
                    kind=edge.artifact_kind,
                    id=artifact_suffix,
                    version=edge.artifact_version,
                )
                parent_ref = ArtifactRef(
                    kind=edge.parent_kind,
                    id=parent_suffix,
                    version=edge.parent_version,
                )
                if (
                    edge.artifact_id != canonical_artifact_id(artifact_ref)
                    or edge.parent_id != canonical_artifact_id(parent_ref)
                    or edge.v2_idempotency_key != lineage_idempotency_key(
                        context_id=context.id,
                        analyst_id=edge.analyst_id or "",
                        artifact=artifact_ref,
                        parent=parent_ref,
                        transform=edge.transform,
                        transform_version=edge.transform_version,
                    )
                ):
                    raise ValueError("v2 edge integrity mismatch")
            except (IndexError, ValueError):
                result.malformed_edges += 1
                result.integrity_failures += 1
                continue
            for edge_ref in (artifact_ref, parent_ref):
                edge_status = await _ref_status(db, context, caller, edge_ref)
                if edge_status == "dangling":
                    result.dangling_refs += 1
                elif edge_status == "unauthorized":
                    result.unauthorized_refs += 1

        # Parse exact typed refs once. Reusing this stable list below avoids a
        # second Pydantic validation/sort pass without changing precedence.
        bound_refs = typed_refs_from_artifacts(artifacts)
        for ref in bound_refs:
            add_ref(ref)

        manifest_ids = {
            ref.id for ref in refs.values() if ref.kind == "source_manifest"
        }
        scalar_manifest_id = artifacts.get("source_manifest_id")
        if isinstance(scalar_manifest_id, str) and scalar_manifest_id:
            manifest_ids.add(scalar_manifest_id)
        for manifest_id in sorted(manifest_ids):
            manifest = await db.get(SourceManifest, manifest_id)
            if manifest is None:
                continue
            manifest_ref = ArtifactRef(kind="source_manifest", id=manifest.id)
            for entry in manifest.files or []:
                document_id = entry.get("document_id") if isinstance(entry, dict) else None
                if not isinstance(document_id, str) or not document_id:
                    result.unresolved_historical_relationships += 1
                    continue
                add_edge(
                    manifest_ref,
                    ArtifactRef(kind="document", id=document_id),
                    "ingestion",
                )

        checkpoints = (await db.execute(select(ModelCheckpoint).where(
            ModelCheckpoint.context_id == context.id
        ).order_by(ModelCheckpoint.id))).scalars().all()
        for checkpoint in checkpoints:
            checkpoint_ref = ArtifactRef(
                kind="model_checkpoint", id=checkpoint.id, version=checkpoint.payload_hash
            )
            add_ref(checkpoint_ref)
            if checkpoint.issuer_run_id:
                add_edge(
                    checkpoint_ref,
                    ArtifactRef(kind="issuer_run", id=checkpoint.issuer_run_id),
                    "model-checkpoint",
                )
            if checkpoint.parent_checkpoint_id:
                parent = await db.get(ModelCheckpoint, checkpoint.parent_checkpoint_id)
                parent_ref = ArtifactRef(
                    kind="model_checkpoint",
                    id=checkpoint.parent_checkpoint_id,
                    version=parent.payload_hash if parent is not None else None,
                )
                add_edge(checkpoint_ref, parent_ref, "model-checkpoint")

        reports = (await db.execute(select(ReportVersion).where(
            ReportVersion.context_id == context.id
        ).order_by(ReportVersion.id))).scalars().all()
        for report in reports:
            report_ref = ArtifactRef(
                kind="report_version", id=report.id, version=report.document_sha256
            )
            add_edge(
                report_ref,
                ArtifactRef(kind="issuer_run", id=report.run_id),
                "report-publication",
            )
            checkpoint = await db.get(ModelCheckpoint, report.model_checkpoint_id)
            add_edge(report_ref, ArtifactRef(
                kind="model_checkpoint",
                id=report.model_checkpoint_id,
                version=checkpoint.payload_hash if checkpoint is not None else None,
            ), "report-publication")
            manifest_id = (report.payload or {}).get("source_manifest_id")
            if isinstance(manifest_id, str) and manifest_id:
                add_edge(
                    report_ref,
                    ArtifactRef(kind="source_manifest", id=manifest_id),
                    "report-publication",
                )
            else:
                result.unresolved_historical_relationships += 1

        insights = (await db.execute(select(AnalysisInsight).where(
            AnalysisInsight.context_id == context.id
        ).order_by(AnalysisInsight.id))).scalars().all()
        for insight in insights:
            insight_ref = ArtifactRef(
                kind="insight", id=insight.id, version=str(insight.version)
            )
            subjects = typed_refs_from_artifacts(insight.subject_refs, convert_legacy=True)
            if not subjects:
                result.unresolved_historical_relationships += 1
            for subject in subjects:
                add_edge(insight_ref, subject, "insight-generation")

        # Base-key membership makes legacy precedence O(1) while retaining every
        # exact version and the original LEGACY_REF_FIELDS iteration order.
        for legacy_ref in typed_refs_from_artifacts(artifacts, convert_legacy=True):
            if (legacy_ref.kind, legacy_ref.id) not in ref_base_keys:
                add_ref(legacy_ref)

        # Stream run refs in dict insertion order; no list is needed because this
        # loop never mutates refs.
        for run_ref in (ref for ref in refs.values() if ref.kind == "issuer_run"):
            captured = (await db.execute(select(LineageEdge.id).where(
                LineageEdge.context_id == context.id,
                LineageEdge.artifact_id == canonical_artifact_id(run_ref),
                LineageEdge.transform == "run-creation",
                LineageEdge.v2_idempotency_key.is_not(None),
            ).limit(1))).scalar_one_or_none()
            if captured is None:
                result.unresolved_historical_relationships += 1

        existing_ref_keys = {ref_key(ref) for ref in bound_refs}
        valid_refs: list[ArtifactRef] = []
        valid_ref_keys: set[tuple[str, str, str]] = set()
        for key, ref in sorted(refs.items()):
            ref_status = await _ref_status(db, context, caller, ref)
            if ref_status == "dangling":
                result.dangling_refs += 1
                continue
            if ref_status == "unauthorized" or not context_authorized:
                result.unauthorized_refs += 1
                continue
            valid_refs.append(ref)
            valid_ref_keys.add(key)
            result.typed_refs += 1
            if key in existing_ref_keys:
                result.existing_typed_refs += 1
            else:
                result.proposed_typed_refs += 1

        for artifact, parent, transform in edges.values():
            # Key lookup replaces two linear Pydantic-model membership scans while
            # preserving proposal/insertion order and version-sensitive identity.
            if ref_key(artifact) not in valid_ref_keys or ref_key(parent) not in valid_ref_keys:
                continue
            if await _edge_exists(
                db, context=context, artifact=artifact, parent=parent, transform=transform
            ):
                result.existing_edges += 1
                continue
            result.proposed_edges += 1
            if mode == "apply":
                await write_lineage_edge(
                    db,
                    context_id=context.id,
                    analyst_id=context.analyst_id,
                    artifact=artifact,
                    parent=parent,
                    transform=transform,
                    transform_version="2",
                    enabled=True,
                )
                result.applied_edges += 1

        if mode == "apply" and valid_refs:
            await bind_context_artifacts(
                db,
                context_id=context.id,
                analyst_id=context.analyst_id,
                refs=valid_refs,
            )
            result.applied_typed_refs += len(valid_ref_keys - existing_ref_keys)
            await db.commit()

    if mode != "apply":
        await db.rollback()
    return result
```

## G5 — Query synthesis · Memory

```python
async def execute_synthesis(session: AsyncSession, spec: SynthesisSpec) -> dict:  # noqa: C901
    """Search agent outputs, claims, and QA findings; return ranked matches."""
    from database import ModuleOutput, Claim, QAFinding, Run, Issuer
    from retrieval import bm25_rank
    import json

    # Cap each scan so the in-request BM25 corpus cannot grow without bound.
    _SYNTH_SCAN_CAP = 2000

    issuer_ids = None
    if spec.issuer_filter:
        col = getattr(Issuer, spec.issuer_filter.field)
        ids = (await session.execute(
            select(Issuer.id).where(col.ilike(f"%{spec.issuer_filter.value}%"))
        )).scalars().all()
        issuer_ids = ids or ["__none__"]

    corpus = []
    meta = {}

    # Build each corpus segment immediately after its capped query. This preserves
    # module -> claim -> finding order without retaining all three ORM row sets at
    # the same time as their text/meta projections.
    stmt = (
        select(ModuleOutput, Run, Issuer)
        .join(Run, ModuleOutput.run_id == Run.id)
        .join(Issuer, Run.issuer_id == Issuer.id)
    )
    if issuer_ids:
        stmt = stmt.where(Issuer.id.in_(issuer_ids))
    if spec.module_filter:
        stmt = stmt.where(ModuleOutput.module_id == spec.module_filter)
    stmt = stmt.order_by(Run.created_at.desc()).limit(_SYNTH_SCAN_CAP)
    for m_out, run, issuer in (await session.execute(stmt)):
        key = f"m:{m_out.id}"
        # Preserve the exact json.dumps head used by the ranking contract.
        payload = json.dumps(m_out.runtime_output, ensure_ascii=False)[:2000]
        text = (
            f"Module: {m_out.module_name} ({m_out.module_id}). "
            f"Confidence: {m_out.confidence}. QA Status: {m_out.qa_status}. "
            f"Output payload: {payload}"
        )
        corpus.append((key, text))
        meta[key] = {
            "issuer": {"id": issuer.id, "name": issuer.name, "ticker": issuer.ticker, "industry": issuer.industry, "country": issuer.country},
            "kind": "module",
            "title": f"{m_out.module_name} ({m_out.module_id})",
            "sub": f"Confidence: {m_out.confidence} · QA: {m_out.qa_status}",
            "text": text,
        }

    stmt = (
        select(Claim, ModuleOutput, Run, Issuer)
        .join(ModuleOutput, Claim.module_output_id == ModuleOutput.id)
        .join(Run, ModuleOutput.run_id == Run.id)
        .join(Issuer, Run.issuer_id == Issuer.id)
    )
    if issuer_ids:
        stmt = stmt.where(Issuer.id.in_(issuer_ids))
    if spec.module_filter:
        stmt = stmt.where(ModuleOutput.module_id == spec.module_filter)
    stmt = stmt.order_by(Run.created_at.desc()).limit(_SYNTH_SCAN_CAP)
    for claim, m_out, run, issuer in (await session.execute(stmt)):
        key = f"c:{claim.id}"
        text = f"Claim {claim.claim_id} from {m_out.module_name}: {claim.claim_text}"
        corpus.append((key, text))
        meta[key] = {
            "issuer": {"id": issuer.id, "name": issuer.name, "ticker": issuer.ticker, "industry": issuer.industry, "country": issuer.country},
            "kind": "claim",
            "title": f"Claim {claim.claim_id} ({m_out.module_id})",
            "sub": m_out.module_name,
            "text": claim.claim_text,
        }

    stmt = (
        select(QAFinding, Run, Issuer)
        .join(Run, QAFinding.run_id == Run.id)
        .join(Issuer, Run.issuer_id == Issuer.id)
    )
    if issuer_ids:
        stmt = stmt.where(Issuer.id.in_(issuer_ids))
    if spec.module_filter:
        stmt = stmt.where(QAFinding.module_id == spec.module_filter)
    stmt = stmt.order_by(Run.created_at.desc()).limit(_SYNTH_SCAN_CAP)
    for finding, run, issuer in (await session.execute(stmt)):
        key = f"f:{finding.id}"
        text = (
            f"QA Finding {finding.finding_id} ({finding.severity}) "
            f"on module {finding.module_id or 'run'}. Lane {finding.lane}. "
            f"Description: {finding.description}. "
            f"Required remediation: {finding.required_remediation or 'none'}."
        )
        corpus.append((key, text))
        meta[key] = {
            "issuer": {"id": issuer.id, "name": issuer.name, "ticker": issuer.ticker, "industry": issuer.industry, "country": issuer.country},
            "kind": f"finding-{finding.severity.lower()[:3]}",
            "title": f"QA Finding {finding.finding_id} ({finding.severity})",
            "sub": f"Lane {finding.lane} · Module: {finding.module_id or 'Run'}",
            "text": f"{finding.description}" + (f" (Remediation: {finding.required_remediation})" if finding.required_remediation else ""),
        }

    hits = bm25_rank(spec.search, corpus, k=spec.limit)
    del corpus

    groups = {}
    for h in hits:
        info = meta[h.chunk_id]
        iid = info["issuer"]["id"]
        g = groups.get(iid)
        if g is None:
            g = {"score": 0.0, "excerpts": []}
            groups[iid] = g
        g["score"] = max(g["score"], h.score)
        if len(g["excerpts"]) < 2:
            g["excerpts"].append({
                "chunk_id": h.chunk_id,
                "doc": info["title"],
                "doc_type": info["kind"],
                "text": f"{info['sub']}: {info['text']}" if info['sub'] else info['text']
            })
    del meta, hits

    issuers = {}
    if groups:
        for iss in (await session.execute(
            select(Issuer).where(Issuer.id.in_(list(groups)))
        )).scalars():
            issuers[iss.id] = iss

    rows = []
    for iid, g in groups.items():
        iss = issuers.get(iid)
        if iss is None:
            continue
        rows.append({
            "issuer": {"id": iss.id, "name": iss.name, "ticker": iss.ticker,
                       "industry": iss.industry, "country": iss.country},
            "score": round(g["score"], 3),
            "excerpts": g["excerpts"],
        })
    rows.sort(key=lambda r: r["score"], reverse=True)
    del rows[spec.limit:]

    caveats = (
        ["Ranked by wiki and agent-synthesis match (BM25) — qualitative relevance, not a quantitative score."]
        if rows
        else ["No matching agent outputs, claims, or QA findings found — try different terms."]
    )
    return {
        "mode": "synthesis",
        "interpretation": spec.interpretation,
        "rank_by": None,
        "rows": rows,
        "caveats": caveats,
    }

```

## G6 — Portfolio analytics · Memory

```python
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

```

## G7 — Issuer profile · Memory

```python
async def get_issuer_profile(
    issuer_id: str,
    db: AsyncSession = Depends(get_db, scope="function"),
    caller: CallerIdentity = Depends(get_identity),
):
    issuer = require_issuer(caller, await db.get(Issuer, issuer_id))

    # Keep the bounded rows because complete-run selection and response projection
    # both consume them, but avoid copying ScalarResult.all() a second time.
    runs = (await db.execute(
        select(Run).where(Run.issuer_id == issuer_id)
        .order_by(Run.created_at.desc()).limit(20)
    )).scalars().all()
    latest_run = runs[0] if runs else None
    latest_complete = next((run for run in runs if run.status == "complete"), None)

    facts = (await db.execute(
        select(MetricFact).where(MetricFact.issuer_id == issuer_id)
        .order_by(MetricFact.metric_key, MetricFact.period).limit(500)
    )).scalars().all()
    fact_run_ids = {fact.run_id for fact in facts if fact.run_id}
    fact_run_as_of = (
        {
            run_id: run_as_of
            for run_id, run_as_of in (await db.execute(
                select(Run.id, Run.as_of_date).where(Run.id.in_(fact_run_ids))
            ))
        }
        if fact_run_ids
        else {}
    )

    doc_count = (await db.execute(
        select(func.count()).select_from(Document).where(Document.issuer_id == issuer_id)
    )).scalar() or 0

    signals: Dict[str, Any] = {}
    coverage: Dict[str, Any] = {"documents": doc_count}
    findings = {"CRITICAL": 0, "MATERIAL": 0, "MINOR": 0}
    business: List[Dict[str, Any]] = []
    sponsor: Dict[str, Any] = {}
    earnings: Dict[str, Any] = {}
    if latest_complete is not None:
        module_rows = (await db.execute(
            select(ModuleOutput).where(ModuleOutput.run_id == latest_complete.id)
        )).scalars()
        run_blocked = (
            latest_complete.qa_status == "Blocked"
            or latest_complete.committee_status == "Blocked"
        )
        mods = {} if run_blocked else {
            module.module_id: module
            for module in module_rows
            if module.qa_status != "Blocked" and module.committee_status != "Blocked"
        }
        del module_rows
        signals = _profile_signals(mods)

        cp1a = mods.get("CP-1A")
        business = (
            ((cp1a.runtime_output or {}).get("facts") or [])
            if cp1a is not None
            else []
        )
        cp2d = mods.get("CP-2D")
        sponsor = (cp2d.runtime_output or {}) if cp2d is not None else {}
        cp1b_module = mods.get("CP-1B")
        cp1b = (
            (cp1b_module.runtime_output or {})
            if cp1b_module is not None
            else {}
        )
        summary = cp1b.get("summary") or {}
        earnings = {
            "latest_period": summary.get("latest_period"),
            "prior_period": summary.get("prior_period"),
            "revenue_growth_pct": summary.get("revenue_growth_pct"),
            "ebitda_growth_pct": summary.get("ebitda_growth_pct"),
            "margin_change_pp": summary.get("margin_change_pp"),
            "monitoring_signals": cp1b.get("monitoring_signals") or [],
        }
        cp0_module = mods.get("CP-0")
        cp0 = (cp0_module.runtime_output or {}) if cp0_module is not None else {}
        coverage.update({
            "readiness_score": cp0.get("readiness_score"),
            "categories_present": cp0.get("categories_present"),
            "categories_missing": cp0.get("categories_missing"),
            "edgar_available": cp0.get("edgar_available"),
        })
        del mods, cp1a, cp2d, cp1b_module, cp1b, summary, cp0_module, cp0
        for finding in (await db.execute(
            select(QAFinding).where(QAFinding.run_id == latest_complete.id)
        )).scalars():
            findings[finding.severity] = findings.get(finding.severity, 0) + 1

    best_fact_by_key: Dict[str, MetricFact] = {}
    for fact in facts:
        if fact.headline and better_fact(best_fact_by_key.get(fact.metric_key), fact):
            best_fact_by_key[fact.metric_key] = fact
    headline_vals = {
        metric_key: fact.value for metric_key, fact in best_fact_by_key.items()
    }
    strengths, weaknesses = _strengths_weaknesses(signals, headline_vals)

    issuer_response = IssuerResponse.model_validate(issuer)
    latest_run_brief = RunBrief.model_validate(latest_run) if latest_run else None
    run_briefs = [RunBrief.model_validate(run) for run in runs]
    metric_rows = [
        MetricFactOut.model_validate(fact).model_copy(update={
            "source_run_as_of": fact_run_as_of.get(fact.run_id),
        })
        for fact in facts
    ]
    signal_run_id = latest_complete.id if latest_complete else None
    del (
        runs,
        facts,
        fact_run_ids,
        fact_run_as_of,
        best_fact_by_key,
        headline_vals,
        issuer,
        latest_run,
        latest_complete,
    )

    return IssuerProfileResponse(
        issuer=issuer_response,
        latest_run=latest_run_brief,
        signal_run_id=signal_run_id,
        runs=run_briefs,
        metrics=metric_rows,
        signals=signals,
        coverage=coverage,
        findings=findings,
        business=business,
        sponsor=sponsor,
        strengths=strengths,
        weaknesses=weaknesses,
        earnings=earnings,
    )

```

## G8 — XLSX report export · Memory

```python
def render_report_xlsx(*, version_id: str, document_sha256: str, payload: dict, authority: dict) -> bytes:
    document = payload.get("document") if isinstance(payload.get("document"), dict) else {}
    reviewed = _reviewed_report(payload)
    modules = (
        [] if reviewed
        else document.get("sections") if isinstance(document.get("sections"), list) else []
    )
    model = payload.get("model") if isinstance(payload.get("model"), dict) else {}
    calculation = model.get("calculation") if isinstance(model.get("calculation"), dict) else {}
    reporting_currency, reporting_unit, reporting_scale = _model_reporting_metadata(
        model
    )
    override_rows, omitted_override_count = _model_override_rows(
        model,
        report_event_at=authority.get("as_of"),
    )
    freshness = authority.get("freshness_evaluation") if isinstance(authority.get("freshness_evaluation"), dict) else {}
    freshness_state = _display(freshness.get("state") or authority.get("freshness") or "unknown").upper()
    wb = Workbook()
    header_font = Font(name="Arial", bold=True, color="FFFFFF")
    navy_fill = PatternFill("solid", fgColor=_NAVY)
    blue_fill = PatternFill("solid", fgColor=_BLUE)
    header_alignment = Alignment(wrap_text=True)
    body_font = Font(name="Arial", size=9, color=_INK)
    metadata_font = Font(name="Arial", bold=True, color=_MUTED)
    module_title_font = Font(name="Arial", size=15, bold=True, color="FFFFFF")
    module_title_alignment = Alignment(vertical="center", indent=1)
    top_wrap_alignment = Alignment(vertical="top", wrap_text=True)
    thin = Side(style="thin", color="D8DCE5")
    row_border = Border(bottom=thin)

    cover = wb.active
    cover.title = "Cover"
    cover.sheet_view.showGridLines = False
    cover.freeze_panes = "A8"
    cover["A1"] = "CAOS - IMMUTABLE COMMITTEE REPORT"
    cover["A1"].font = Font(name="Arial", size=18, bold=True, color="FFFFFF")
    cover["A1"].fill = navy_fill
    cover.merge_cells("A1:D2")
    cover["A1"].alignment = Alignment(vertical="center")
    metadata = (
        ("Report version", version_id),
        ("Document SHA-256", document_sha256),
        ("Issuer", document.get("issuer_id")),
        ("Run", document.get("run_id")),
        ("As of", document.get("as_of_date")),
        ("QA status", document.get("qa_status")),
        ("Committee status", document.get("committee_status")),
        ("Prepared by", document.get("prepared_by")),
        ("Authority origin", authority.get("origin")),
        ("Authority state", authority.get("approval_state")),
        ("Freshness", freshness_state),
        ("Freshness source", freshness.get("source_kind")),
        ("Freshness reason", freshness.get("reason")),
        ("Freshness policy", freshness.get("policy_version")),
        ("Freshness observed", freshness.get("observed_at")),
        ("Freshness effective period", freshness.get("effective_period_end")),
        ("Freshness due", freshness.get("due_at")),
        ("Model engine", model.get("engine_version")),
        ("Model source fingerprint", model.get("source_fingerprint")),
        ("Model input fingerprint", model.get("input_fingerprint")),
        ("Model calculation hash", model.get("calculation_hash")),
        ("Model draft revision", model.get("draft_revision")),
        ("Model origin", (model.get("authority") or {}).get("origin") if isinstance(model.get("authority"), dict) else None),
        ("Model input origins", ", ".join((model.get("authority") or {}).get("model_input_origins") or []) if isinstance(model.get("authority"), dict) else None),
        ("Model analyst override", (model.get("authority") or {}).get("analyst_override") if isinstance(model.get("authority"), dict) else None),
        ("Model availability", calculation.get("status")),
        ("Model reporting currency", reporting_currency),
        ("Model reporting unit", reporting_unit),
        ("Model override count", len(override_rows) + omitted_override_count),
    )
    for row_index, (label, value) in enumerate(metadata, start=4):
        cover.cell(row_index, 1, label).font = metadata_font
        cover.cell(row_index, 2, _xlsx_text(value))
    cover.column_dimensions["A"].width = 24
    cover.column_dimensions["B"].width = 72
    cover.column_dimensions["C"].width = 18
    cover.column_dimensions["D"].width = 18
    cover.sheet_properties.pageSetUpPr.fitToPage = True
    cover.page_setup.fitToWidth = 1
    cover.page_setup.fitToHeight = 0

    if reviewed:
        reviewed_sheet = wb.create_sheet("Reviewed Report")
        reviewed_sheet.sheet_view.showGridLines = False
        reviewed_sheet.freeze_panes = "A2"
        reviewed_sheet.append(["Section", "Field", "Reviewed value"])
        for cell in reviewed_sheet[1]:
            cell.font = header_font
            cell.fill = navy_fill
            cell.alignment = header_alignment
        for section, field, value in _reviewed_rows(reviewed):
            reviewed_sheet.append([
                _xlsx_text(section), _xlsx_text(field), _xlsx_scalar(value),
            ])
        reviewed_sheet.column_dimensions["A"].width = 42
        reviewed_sheet.column_dimensions["B"].width = 38
        reviewed_sheet.column_dimensions["C"].width = 110
        for row in reviewed_sheet.iter_rows(min_row=2):
            for cell in row:
                cell.alignment = top_wrap_alignment
                cell.font = body_font

    summary = wb.create_sheet("Module Summary")
    summary.sheet_view.showGridLines = False
    summary.freeze_panes = "A2"
    summary.append(["Module", "Name", "Confidence", "QA status"])
    for module in modules:
        if not isinstance(module, dict):
            continue
        summary.append([
            _xlsx_text(module.get("module_id")),
            _xlsx_text(module.get("module_name")),
            _xlsx_scalar(module.get("confidence")),
            _xlsx_text(module.get("qa_status")),
        ])
    for cell in summary[1]:
        cell.font = header_font
        cell.fill = navy_fill
    summary.column_dimensions["A"].width = 16
    summary.column_dimensions["B"].width = 42
    summary.column_dimensions["C"].width = 16
    summary.column_dimensions["D"].width = 18
    if summary.max_row > 1:
        table = Table(displayName="ModuleSummary", ref=f"A1:D{summary.max_row}")
        table.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2", showRowStripes=True, showFirstColumn=False, showLastColumn=False)
        summary.add_table(table)

    used = {sheet.title for sheet in wb.worksheets}
    for module_index, module in enumerate(modules, start=1):
        if not isinstance(module, dict):
            continue
        module_id = _display(module.get("module_id")) or f"Module {module_index}"
        sheet = wb.create_sheet(_safe_sheet_name(module_id, used))
        sheet.sheet_view.showGridLines = False
        sheet.freeze_panes = "A5"
        sheet["A1"] = _xlsx_text(f"{module_id} - {_display(module.get('module_name'))}")
        sheet["A1"].font = module_title_font
        sheet["A1"].fill = navy_fill
        sheet["A1"].alignment = module_title_alignment
        sheet.merge_cells("A1:B2")
        sheet["A3"] = "Path"
        sheet["B3"] = "Frozen value"
        for cell in sheet[3]:
            cell.font = header_font
            cell.fill = blue_fill
        rendered_summary_row = False
        for path, value in _rows(module.get("summary") or {}):
            rendered_summary_row = True
            sheet.append([_xlsx_text(path), _xlsx_scalar(value)])
        if not rendered_summary_row:
            sheet.append(["summary", ""])
        for row in sheet.iter_rows(min_row=4, max_row=sheet.max_row, min_col=1, max_col=2):
            for cell in row:
                cell.border = row_border
                cell.alignment = top_wrap_alignment
                cell.font = body_font
        sheet.column_dimensions["A"].width = 46
        sheet.column_dimensions["B"].width = 90
        sheet.sheet_properties.pageSetUpPr.fitToPage = True
        sheet.page_setup.fitToWidth = 1
        sheet.page_setup.fitToHeight = 0

    model_periods = calculation.get("periods") if isinstance(calculation.get("periods"), list) else []
    if model_periods:
        model_sheet = wb.create_sheet(_safe_sheet_name("Model", used))
        model_sheet.sheet_view.showGridLines = False
        model_sheet.freeze_panes = "A2"
        model_headers = (
            "Period key", "Label", "Kind", f"Revenue ({reporting_scale})",
            f"Adjusted EBITDA ({reporting_scale})",
            f"Cash interest ({reporting_scale})",
            f"Total debt ({reporting_scale})", f"Cash ({reporting_scale})",
            f"Net debt ({reporting_scale})", "Gross leverage",
            "Net leverage", "Interest coverage",
            f"Free cash flow ({reporting_scale})",
        )
        model_sheet.append(model_headers)
        for period in model_periods:
            if not isinstance(period, dict):
                continue
            model_sheet.append([
                _xlsx_scalar(period.get("period_key")),
                _xlsx_scalar(period.get("label")),
                _xlsx_scalar(period.get("kind")),
                period.get("revenue"), period.get("adjusted_ebitda"),
                period.get("cash_interest"), period.get("total_debt"), period.get("cash"),
                period.get("net_debt"), period.get("gross_leverage"),
                period.get("net_leverage"), period.get("interest_coverage"),
                period.get("free_cash_flow"),
            ])
        for cell in model_sheet[1]:
            cell.font = header_font
            cell.fill = navy_fill
            cell.alignment = header_alignment
        for column in range(1, len(model_headers) + 1):
            model_sheet.column_dimensions[model_sheet.cell(1, column).column_letter].width = (
                18 if column <= 3 else 16
            )
        for row in model_sheet.iter_rows(min_row=2):
            for cell in row:
                cell.border = row_border
                cell.font = body_font
            for cell in row[3:]:
                cell.number_format = "#,##0.00;[Red](#,##0.00);-"

    if override_rows or omitted_override_count:
        override_sheet = wb.create_sheet(_safe_sheet_name("Model Overrides", used))
        override_sheet.sheet_view.showGridLines = False
        override_sheet.freeze_panes = "A2"
        override_headers = (
            "Status at report event", "Node", "Override value", "Reason", "Scope",
            "Source", "Expires at", "Displaced formula", "Displaced value",
        )
        override_sheet.append(override_headers)
        for cell in override_sheet[1]:
            cell.font = header_font
            cell.fill = navy_fill
            cell.alignment = header_alignment
        for override in override_rows:
            override_sheet.append([
                _xlsx_text(override["status"]),
                _xlsx_text(override["node_id"]),
                _xlsx_scalar(override["value"]),
                _xlsx_text(override["reason"]),
                _xlsx_text(override["scope"]),
                _xlsx_text(override["source"]),
                _xlsx_text(override["expires_at"]),
                _xlsx_text(override["original_formula"]),
                _xlsx_scalar(override["original_value"]),
            ])
        if omitted_override_count:
            override_sheet.append([
                "TRUNCATED",
                f"{omitted_override_count} additional overrides remain in the frozen payload",
            ])
        for row in override_sheet.iter_rows(min_row=2):
            for cell in row:
                cell.border = row_border
                cell.alignment = top_wrap_alignment
                cell.font = body_font
        for column, width in enumerate((24, 42, 18, 48, 16, 32, 26, 52, 18), start=1):
            override_sheet.column_dimensions[
                override_sheet.cell(1, column).column_letter
            ].width = width
    del override_rows

    if model_periods:
        instrument_currencies = _instrument_currencies(model)
        debt_sheet = wb.create_sheet(_safe_sheet_name("Debt Schedule", used))
        debt_sheet.sheet_view.showGridLines = False
        debt_sheet.freeze_panes = "A2"
        debt_headers = (
            "Period key", "Instrument ID", "Instrument currency",
            f"Opening ({reporting_unit})", f"Closing ({reporting_unit})",
            f"Average ({reporting_unit})",
            f"Benchmark interest ({reporting_unit})",
            f"Margin interest ({reporting_unit})",
            f"Coupon interest ({reporting_unit})", f"Fees ({reporting_unit})",
            f"PIK interest ({reporting_unit})", f"Hedge effect ({reporting_unit})",
            f"FX effect ({reporting_unit})", f"Cash interest ({reporting_unit})",
            f"Debt in reporting currency ({reporting_scale})",
            f"Roll-forward residual ({reporting_unit})",
        )
        debt_sheet.append(debt_headers)
        for period in model_periods:
            if not isinstance(period, dict):
                continue
            instruments = period.get("instruments") if isinstance(period.get("instruments"), list) else []
            for instrument in instruments:
                if not isinstance(instrument, dict):
                    continue
                debt_sheet.append([
                    _xlsx_scalar(period.get("period_key")),
                    _xlsx_scalar(instrument.get("instrument_id")),
                    _xlsx_text(instrument_currencies.get(
                        str(instrument.get("instrument_id")), "Unavailable"
                    )),
                    instrument.get("opening_balance"), instrument.get("closing_balance"),
                    instrument.get("average_balance"), instrument.get("benchmark_interest"),
                    instrument.get("margin_interest"), instrument.get("coupon_interest"),
                    instrument.get("fees"), instrument.get("pik_interest"),
                    instrument.get("hedge_effect"), instrument.get("fx_effect"),
                    instrument.get("cash_interest"), instrument.get("debt_reporting_currency"),
                    instrument.get("rollforward_residual"),
                ])
        for cell in debt_sheet[1]:
            cell.font = header_font
            cell.fill = navy_fill
            cell.alignment = header_alignment
        for column in range(1, len(debt_headers) + 1):
            debt_sheet.column_dimensions[debt_sheet.cell(1, column).column_letter].width = (
                20 if column <= 2 else 16
            )
        for row in debt_sheet.iter_rows(min_row=2):
            for cell in row:
                cell.border = row_border
                cell.font = body_font
            for cell in row[3:]:
                cell.number_format = "#,##0.00;[Red](#,##0.00);-"

    if model:
        ledger = wb.create_sheet(_safe_sheet_name("Model Gaps - Warnings", used))
        ledger.append(["Type", "Detail"])
        for cell in ledger[1]:
            cell.font = header_font
            cell.fill = navy_fill
            cell.alignment = header_alignment
        ledger.append(["Availability", _xlsx_text(calculation.get("status") or "unknown")])
        for item in calculation.get("gaps") or []:
            ledger.append(["Gap", _xlsx_text(item)])
        for item in calculation.get("warnings") or []:
            ledger.append(["Warning", _xlsx_text(item)])
        ledger.column_dimensions["A"].width = 18
        ledger.column_dimensions["B"].width = 110

    sources = wb.create_sheet("Sources - Audit")
    sources.sheet_view.showGridLines = False
    sources.freeze_panes = "A2"
    sources.append(["Source ID", "Authority origin", "As of", "Approval state", "Freshness", "Freshness policy"])
    source_ids = authority.get("source_ids") if isinstance(authority.get("source_ids"), list) else []
    for source_id in source_ids:
        sources.append([
            _xlsx_text(source_id),
            _xlsx_text(authority.get("origin")),
            _xlsx_text(authority.get("as_of")),
            _xlsx_text(authority.get("approval_state")),
            _xlsx_text(freshness_state),
            _xlsx_text(freshness.get("policy_version")),
        ])
    if model:
        sources.append([
            _xlsx_text(f"model:{_display(model.get('calculation_hash'))}"),
            "model-engine-v2",
            _xlsx_text(authority.get("as_of")),
            _xlsx_text(authority.get("approval_state")),
            _xlsx_text(freshness_state),
            _xlsx_text(model.get("engine_version")),
        ])
    for cell in sources[1]:
        cell.font = header_font
        cell.fill = navy_fill
    for column, width in zip("ABCDEF", (54, 18, 28, 18, 14, 24)):
        sources.column_dimensions[column].width = width

    wb.properties.title = "CAOS Immutable Committee Report"
    wb.properties.subject = document_sha256
    wb.properties.creator = "CAOS Report Studio"
    wb.properties.description = f"Immutable report version {version_id}"
    output = BytesIO()
    wb.save(output)
    # Production-side structural sanity check: fail before returning malformed bytes.
    output.seek(0)
    reopened = load_workbook(output, read_only=True, data_only=False)
    if "Cover" not in reopened.sheetnames or "Module Summary" not in reopened.sheetnames:
        raise ValueError("Generated workbook failed structural verification.")
    if any(
        cell.data_type == "f"
        for sheet in reopened.worksheets
        for row in sheet.iter_rows()
        for cell in row
    ):
        raise ValueError("Generated report workbook contains executable formulas.")
    reopened.close()
    return output.getvalue()

```

## G9 — Navigation guard · Speed

```tsx
export function NavigationGuardProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const registrations = useRef(new Map<symbol, GuardRegistration>());
  const pendingRef = useRef<PendingNavigation | null>(null);
  const [pending, setPending] = useState<PendingNavigation | null>(null);
  const [activeGuardCount, setActiveGuardCount] = useState(0);

  // Collect in one pass rather than Array.from(...).filter(...). Guard order is
  // still Map insertion order, which is the discard-callback contract.
  const activeGuards = useCallback(() => {
    const guards: GuardRegistration[] = [];
    for (const guard of registrations.current.values()) {
      if (guard.enabled && guard.dirty) guards.push(guard);
    }
    return guards;
  }, []);

  // Counting registrations does not need to allocate a guard snapshot.
  const syncActiveCount = useCallback(() => {
    let count = 0;
    for (const guard of registrations.current.values()) {
      if (guard.enabled && guard.dirty) count += 1;
    }
    setActiveGuardCount(count);
  }, []);

  const registerGuard = useCallback(
    (id: symbol, registration: GuardRegistration) => {
      registrations.current.set(id, registration);
      syncActiveCount();
      return () => {
        const current = registrations.current;
        if (current.get(id) === registration) current.delete(id);
        syncActiveCount();
      };
    },
    [syncActiveCount],
  );

  // The optional internal snapshot lets click interception collect active guards
  // once. The context still exposes the exact one-argument attemptNavigation type.
  const queueAttempt = useCallback(
    (proceed: () => void, guards: GuardRegistration[] = activeGuards()): boolean => {
      if (guards.length === 0) {
        proceed();
        return true;
      }
      if (pendingRef.current) return false;
      const request = { proceed, guards };
      pendingRef.current = request;
      setPending(request);
      return false;
    },
    [activeGuards],
  );

  const stay = useCallback(() => {
    pendingRef.current = null;
    setPending(null);
  }, []);

  const discardAndLeave = useCallback(() => {
    const request = pendingRef.current;
    if (!request) return;
    pendingRef.current = null;
    setPending(null);
    for (const guard of request.guards) {
      try {
        guard.onDiscard();
      } catch {
        // A faulty synchronous discard cannot trap a user who chose to leave.
      }
    }
    request.proceed();
  }, []);

  useEffect(() => {
    if (activeGuardCount === 0) return;
    const onBeforeUnload = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", onBeforeUnload);
    return () => window.removeEventListener("beforeunload", onBeforeUnload);
  }, [activeGuardCount]);

  useEffect(() => {
    const onClick = (event: MouseEvent) => {
      if (
        event.defaultPrevented ||
        event.button !== 0 ||
        event.metaKey ||
        event.ctrlKey ||
        event.shiftKey ||
        event.altKey
      ) {
        return;
      }
      const guards = activeGuards();
      if (guards.length === 0) return;
      const element =
        event.target instanceof Element
          ? event.target.closest<HTMLAnchorElement>("a[href]")
          : null;
      if (!element || element.hasAttribute("download")) return;
      if (element.target && element.target.toLowerCase() !== "_self") return;
      const url = new URL(element.href, window.location.href);
      if (url.origin !== window.location.origin) return;
      if (
        url.pathname === window.location.pathname &&
        url.search === window.location.search
      ) {
        return;
      }

      event.preventDefault();
      event.stopPropagation();
      queueAttempt(
        () => router.push(`${url.pathname}${url.search}${url.hash}`),
        guards,
      );
    };
    document.addEventListener("click", onClick, true);
    return () => document.removeEventListener("click", onClick, true);
  }, [activeGuards, queueAttempt, router]);

  useEffect(() => {
    const history = window.history;
    const originalPushState = history.pushState;
    const originalReplaceState = history.replaceState;
    const initialState = history.state;
    const originalIndex = historyIndex(initialState) ?? 0;
    const currentIndex = { value: originalIndex };
    originalReplaceState.call(
      history,
      withHistoryIndex(initialState, originalIndex),
      "",
      window.location.href,
    );

    const wrappedPushState: History["pushState"] = (data, unused, url) => {
      const next = currentIndex.value + 1;
      currentIndex.value = next;
      return originalPushState.call(
        history,
        withHistoryIndex(data, next),
        unused,
        url,
      );
    };
    const wrappedReplaceState: History["replaceState"] = (data, unused, url) =>
      originalReplaceState.call(
        history,
        withHistoryIndex(data, currentIndex.value),
        unused,
        url,
      );
    history.pushState = wrappedPushState;
    history.replaceState = wrappedReplaceState;

    let allowNextPop = false;
    let bounce: {
      origin: number;
      delta: number;
      guards: GuardRegistration[];
    } | null = null;
    const onPopState = (event: PopStateEvent) => {
      const destination = historyIndex(event.state);
      if (allowNextPop) {
        allowNextPop = false;
        if (destination != null) currentIndex.value = destination;
        return;
      }
      if (bounce) {
        const resumed = bounce;
        bounce = null;
        currentIndex.value = resumed.origin;
        if (!pendingRef.current) {
          const request: PendingNavigation = {
            guards: resumed.guards,
            proceed: () => {
              allowNextPop = true;
              history.go(resumed.delta);
            },
          };
          pendingRef.current = request;
          setPending(request);
        }
        return;
      }

      const delta = destination == null ? -1 : destination - currentIndex.value;
      if (delta === 0) return;
      const guards = activeGuards();
      if (guards.length === 0) {
        if (destination != null) currentIndex.value = destination;
        return;
      }
      bounce = { origin: currentIndex.value, delta, guards };
      history.go(-delta);
    };
    window.addEventListener("popstate", onPopState);
    return () => {
      window.removeEventListener("popstate", onPopState);
      if (history.pushState === wrappedPushState) history.pushState = originalPushState;
      if (history.replaceState === wrappedReplaceState) {
        history.replaceState = originalReplaceState;
      }
    };
  }, [activeGuards]);

  const value = useMemo<NavigationGuardContextValue>(
    () => ({ registerGuard, attemptNavigation: queueAttempt }),
    [queueAttempt, registerGuard],
  );

  return (
    <NavigationGuardContext.Provider value={value}>
      {children}
      {pending ? (
        <NavigationConfirmDialog onStay={stay} onDiscard={discardAndLeave} />
      ) : null}
    </NavigationGuardContext.Provider>
  );
}
```

## G10 — Complexity delta gate · Incumbent

```python
def main() -> int:
    args = _arguments()
    baseline_path = args.baseline if args.baseline.is_absolute() else REPO_ROOT / args.baseline
    try:
        changed_paths = _changed_python_paths(args.base_ref)
        baseline = _load_baseline(baseline_path)
        findings = _run_ruff(changed_paths, args.ruff)
        problems = _assess_findings(findings, baseline, changed_paths)
    except (GateError, OSError) as exc:
        print(f"complexity gate error: {exc}", file=sys.stderr)
        return 2
    if problems:
        print("Complexity delta gate failed:")
        for problem in problems:
            print(f"  - {problem}")
        return 1
    print(
        "Complexity delta gate passed: "
        f"{len(findings)} bounded finding(s) across {len(changed_paths)} changed Python path(s)."
    )
    return 0
```
