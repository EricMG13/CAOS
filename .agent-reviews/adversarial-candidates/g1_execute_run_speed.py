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
