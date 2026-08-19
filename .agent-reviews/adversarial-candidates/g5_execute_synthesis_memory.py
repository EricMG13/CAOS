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

