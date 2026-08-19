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
