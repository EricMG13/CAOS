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

