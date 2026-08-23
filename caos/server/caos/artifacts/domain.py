from __future__ import annotations

import copy
import hashlib
import json
from typing import Any

from ..contracts import RecommendationMatrixRequest, ThesisRequest, digest
from ..methodology.cpdr import confidence_inputs, render_cpdr_markdown, validate_cpdr_payload
from ..store import MemoryStore, now_iso


def latest_version(store: MemoryStore, bucket: dict[str, list[dict[str, Any]]], case_id: str) -> dict[str, Any] | None:
    versions = store.versioned(bucket, case_id)
    return versions[-1] if versions else None


def _validate_case_refs(store: MemoryStore, case_id: str, refs: list[str], *, artifacts_only: bool = False) -> None:
    with store.lock:
        for ref in refs:
            artifact = store.artifacts.get(ref)
            if artifact and artifact.get("case_id") == case_id:
                continue
            if not artifacts_only:
                source = store.sources.get(ref)
                snapshot = store.snapshots.get(ref)
                if source and source.get("case_id") == case_id:
                    if source.get("withdrawn"):
                        raise ValueError("EVIDENCE_SOURCE_WITHDRAWN")
                    continue
                if snapshot and snapshot.get("case_id") == case_id:
                    continue
            raise ValueError("EVIDENCE_CASE_MISMATCH")


def save_thesis(store: MemoryStore, case_id: str, actor: str, request: ThesisRequest) -> dict[str, Any]:
    with store.lock:
        _validate_case_refs(store, case_id, request.evidence_ids)
        value = {
            "id": store._id("thesis"),
            "case_id": case_id,
            "author": actor,
            "core_thesis": request.core_thesis,
            "drivers": request.drivers,
            "risks": request.risks,
            "catalysts": request.catalysts,
            "unresolved_questions": request.unresolved_questions,
            "evidence_ids": request.evidence_ids,
        }
        audit_start = len(store.audit)
        result = store.append_version(store.theses, case_id, request.expected_version, value, persist=False)
        store.audit_event("thesis.versioned", actor, case_id=case_id, version=result["version"])
        try:
            store.persist()
        except Exception:
            store.theses[case_id].pop()
            if not store.theses[case_id]:
                store.theses.pop(case_id, None)
            del store.audit[audit_start:]
            raise
    return result


def save_recommendations(store: MemoryStore, case_id: str, actor: str, request: RecommendationMatrixRequest, accepted_snapshot_id: str | None = None) -> dict[str, Any]:
    _validate_case_refs(store, case_id, request.analytical_dependency_ids, artifacts_only=True)
    value = {
        "id": store._id("rec"),
        "case_id": case_id,
        "author": actor,
        "market_snapshot_id": request.market_snapshot_id,
        "rows": [row.model_dump(mode="json") for row in request.rows],
        "analytical_dependency_ids": request.analytical_dependency_ids,
        "accepted_snapshot_id": accepted_snapshot_id,
        "stale": False,
        "stale_reasons": [],
    }
    with store.lock:
        audit_start = len(store.audit)
        result = store.append_version(store.recommendations, case_id, request.expected_version, value, persist=False)
        store.audit_event("recommendation.versioned", actor, case_id=case_id, version=result["version"])
        try:
            store.persist()
        except Exception:
            store.recommendations[case_id].pop()
            if not store.recommendations[case_id]:
                store.recommendations.pop(case_id, None)
            del store.audit[audit_start:]
            raise
    return result


def save_report_inputs(store: MemoryStore, case_id: str, actor: str, thesis_request: ThesisRequest, recommendation_request: RecommendationMatrixRequest, accepted_snapshot_id: str | None = None) -> dict[str, Any]:
    with store.lock:
        _validate_case_refs(store, case_id, thesis_request.evidence_ids)
        _validate_case_refs(store, case_id, recommendation_request.analytical_dependency_ids, artifacts_only=True)
        theses = store.theses.get(case_id)
        recommendations = store.recommendations.get(case_id)
        thesis_version = theses[-1]["version"] if theses else 0
        recommendation_version = recommendations[-1]["version"] if recommendations else 0
        if thesis_version != thesis_request.expected_version or recommendation_version != recommendation_request.expected_version:
            raise ValueError("VERSION_CONFLICT")
        thesis = {
            "id": store._id("thesis"),
            "case_id": case_id,
            "author": actor,
            "core_thesis": thesis_request.core_thesis,
            "drivers": list(thesis_request.drivers),
            "risks": list(thesis_request.risks),
            "catalysts": list(thesis_request.catalysts),
            "unresolved_questions": list(thesis_request.unresolved_questions),
            "evidence_ids": list(thesis_request.evidence_ids),
            "version": thesis_version + 1,
            "created_at": now_iso(),
        }
        recommendation = {
            "id": store._id("rec"),
            "case_id": case_id,
            "author": actor,
            "market_snapshot_id": recommendation_request.market_snapshot_id,
            "rows": [row.model_dump(mode="json") for row in recommendation_request.rows],
            "analytical_dependency_ids": list(recommendation_request.analytical_dependency_ids),
            "accepted_snapshot_id": accepted_snapshot_id,
            "stale": False,
            "stale_reasons": [],
            "version": recommendation_version + 1,
            "created_at": now_iso(),
        }
        audit_start = len(store.audit)
        try:
            if theses is None:
                store.theses[case_id] = [thesis]
            else:
                theses.append(thesis)
            if recommendations is None:
                store.recommendations[case_id] = [recommendation]
            else:
                recommendations.append(recommendation)
            store.audit_event("thesis.versioned", actor, case_id=case_id, version=thesis["version"])
            store.audit_event("recommendation.versioned", actor, case_id=case_id, version=recommendation["version"])
            store.persist()
        except Exception:
            if theses is None:
                store.theses.pop(case_id, None)
            else:
                theses.pop()
            if recommendations is None:
                store.recommendations.pop(case_id, None)
            else:
                recommendations.pop()
            del store.audit[audit_start:]
            raise
    return {"thesis": copy.deepcopy(thesis), "recommendations": copy.deepcopy(recommendation)}


def recommendation_state(store: MemoryStore, case_id: str, value: dict[str, Any] | None) -> dict[str, Any] | None:
    if not value:
        return None
    result = copy.deepcopy(value)
    accepted = accepted_snapshot(store, case_id)
    if result.get("accepted_snapshot_id") and accepted and result["accepted_snapshot_id"] != accepted["id"]:
        result["stale"] = True
        result["stale_reasons"] = ["ACCEPTED_SNAPSHOT_CHANGED"]
    return result


def create_note(store: MemoryStore, case_id: str, actor: str, body: str) -> dict[str, Any]:
    note = {"id": store._id("note"), "case_id": case_id, "author": actor, "body": body, "promoted": False, "created_at": now_iso()}
    with store.lock:
        notes = store.notes.setdefault(case_id, [])
        audit_start = len(store.audit)
        notes.append(note)
        store.audit_event("note.created", actor, case_id=case_id, note_id=note["id"])
        try:
            store.persist()
        except Exception:
            notes.pop()
            if not notes:
                store.notes.pop(case_id, None)
            del store.audit[audit_start:]
            raise
    return copy.deepcopy(note)


def promote_note(store: MemoryStore, case_id: str, note_id: str, actor: str) -> dict[str, Any]:
    with store.lock:
        note = next((note for note in store.notes.get(case_id, []) if note["id"] == note_id), None)
        if not note:
            raise KeyError("NOTE_NOT_FOUND")
        if note["author"] != actor:
            raise PermissionError("only note author can promote")
        promoted_source = store.sources.get(note.get("promoted_source_id"))
        if note["promoted"] and promoted_source and not promoted_source["withdrawn"]:
            return copy.deepcopy(note)
        prior_note = copy.deepcopy(note)
        prior_source_set = store.source_sets.get(case_id)
        source_id = store._id("src-note")
        source = {
            "id": source_id,
            "case_id": case_id,
            "filename": f"analyst-note-{note_id}.md",
            "media_type": "text/markdown",
            "bytes": len(note["body"].encode()),
            "sha256": hashlib.sha256(note["body"].encode("utf-8")).hexdigest(),
            "vault_path": None,
            "blocks": [{"block_id": "b00001", "locator": {"note_id": note_id}, "text": note["body"], "extractor_version": "analyst-note-v1", "confidence": "HIGH", "untrusted_data": True}],
            "created_by": actor,
            "created_at": now_iso(),
            "withdrawn": False,
            "source_kind": "analyst_note",
        }
        current = store.source_sets.get(case_id)
        active_source_ids = [existing_id for existing_id in (current["source_ids"] if current else []) if (existing_source := store.sources.get(existing_id)) and not existing_source.get("withdrawn")]
        new_source_set = {
            "id": store._id("set"),
            "case_id": case_id,
            "version": (current["version"] + 1) if current else 1,
            "source_ids": [*active_source_ids, source_id],
            "created_by": actor,
            "created_at": now_iso(),
        }
        audit_start = len(store.audit)
        try:
            note["promoted"] = True
            note["promoted_source_id"] = source_id
            store.sources[source_id] = source
            store.register_source_set(new_source_set)
            store.audit_event("note.promoted", actor, case_id=case_id, note_id=note_id, source_id=source_id)
            store.persist()
        except Exception:
            note.clear()
            note.update(prior_note)
            store.sources.pop(source_id, None)
            if prior_source_set is None:
                store.source_sets.pop(case_id, None)
            else:
                store.source_sets[case_id] = prior_source_set
            store.source_set_history.pop(new_source_set["id"], None)
            del store.audit[audit_start:]
            raise
    return copy.deepcopy(note)


def create_assumption(store: MemoryStore, case_id: str, actor: str, statement: str, evidence_ids: list[str], affected_module_ids: list[str], supporting_claim: str = "", conflicting_claim: str = "") -> dict[str, Any]:
    with store.lock:
        _validate_case_refs(store, case_id, evidence_ids)
        assumption = {
            "id": store._id("assumption"),
            "case_id": case_id,
            "author": actor,
            "statement": statement,
            "supporting_claim": supporting_claim,
            "conflicting_claim": conflicting_claim,
            "evidence_ids": evidence_ids,
            "affected_module_ids": affected_module_ids,
            "status": "PROVISIONAL",
            "stale": False,
            "created_at": now_iso(),
        }
        assumptions = store.assumptions.setdefault(case_id, [])
        audit_start = len(store.audit)
        assumptions.append(assumption)
        store.audit_event("assumption.created", actor, case_id=case_id, assumption_id=assumption["id"])
        try:
            store.persist()
        except Exception:
            assumptions.pop()
            if not assumptions:
                store.assumptions.pop(case_id, None)
            del store.audit[audit_start:]
            raise
    return copy.deepcopy(assumption)


def mark_assumptions_stale(store: MemoryStore, case_id: str, changed_source_ids: set[str], *, persist: bool = True) -> None:
    with store.lock:
        prior_assumptions = copy.deepcopy(store.assumptions.get(case_id)) if persist else None
        changed = False
        for assumption in store.assumptions.get(case_id, []):
            if changed_source_ids.intersection(assumption["evidence_ids"]):
                assumption["stale"] = True
                assumption["status"] = "STALE"
                changed = True
        if changed and persist:
            try:
                store.persist()
            except Exception:
                if prior_assumptions is None:
                    store.assumptions.pop(case_id, None)
                else:
                    store.assumptions[case_id] = prior_assumptions
                raise


def build_snapshot_payload(store: MemoryStore, run: dict[str, Any], bundle: Any | None = None) -> dict[str, Any]:
    if run.get("status") != "succeeded" or len(run.get("nodes", [])) != len(run.get("node_ids", [])):
        raise ValueError("RUN_NOT_READY")
    artifacts = []
    for node in run["nodes"]:
        artifact = store.get_artifact(node.get("artifact_id")) if node.get("artifact_id") else None
        if (
            node.get("status") != "succeeded"
            or not artifact
            or artifact.get("run_id") != run.get("id")
            or artifact.get("case_id") not in {None, run.get("case_id")}
            or artifact.get("module_id") != node.get("module_id")
            or artifact.get("digest") != digest(artifact.get("payload"))
        ):
            raise ValueError("RUN_NOT_READY")
        if node.get("module_id") == "CP-DR" and not cpdr_artifact_is_valid(store, run, node, artifact, bundle):
            raise ValueError("RUN_NOT_READY")
        artifacts.append(artifact)
    source_set = store.source_set_by_id(run["plan"].get("source_set_id"))
    if not source_set:
        raise ValueError("SOURCE_SET_CHANGED")
    return {
        "case_id": run["case_id"],
        "run_id": run["id"],
        "source_set_id": source_set["id"] if source_set else None,
        "source_set_version": source_set["version"] if source_set else None,
        "artifacts": [{"id": artifact["id"], "module_id": artifact["module_id"], "digest": artifact["digest"]} for artifact in artifacts],
        "accepted_at": now_iso(),
    }


def cpdr_artifact_is_valid(
    store: MemoryStore,
    run: dict[str, Any],
    node: dict[str, Any],
    artifact: dict[str, Any],
    bundle: Any | None,
) -> bool:
    try:
        if bundle is None:
            return False
        envelope = artifact["payload"]
        expected_keys = {
            "schema_version", "module_id", "transport", "host_confidence", "canonical_output",
            "methodology", "source_set", "upstream_artifacts",
        }
        if not isinstance(envelope, dict) or set(envelope) != expected_keys:
            return False
        source_set = store.source_set_by_id(run["plan"].get("source_set_id"))
        research = run.get("research") or {}
        approved_plan = research.get("proposed_plan")
        brief = research.get("brief")
        if not source_set or not isinstance(approved_plan, dict) or not isinstance(brief, dict):
            return False
        expected_upstream = []
        for dependency in node.get("dependencies", []):
            dependency_node = next((item for item in run["nodes"] if item.get("module_id") == dependency), None)
            dependency_artifact = store.get_artifact(dependency_node.get("artifact_id")) if dependency_node else None
            if not dependency_artifact:
                return False
            expected_upstream.append(
                {"module_id": dependency, "artifact_id": dependency_artifact["id"], "digest": dependency_artifact["digest"]}
            )
        approved_hash = research.get("approved_plan_hash")
        expected_scope = {
            "type": brief.get("scope_type"),
            "key": brief.get("scope_key"),
            "source_mode": brief.get("source_mode"),
        }
        expected_fingerprint = digest(
            {
                "plan": run["plan"]["plan_digest"],
                "module": "CP-DR",
                "source_set": source_set,
                "source_ids": list(source_set["source_ids"]),
                "upstream_artifacts": expected_upstream,
            }
        )
        if (
            approved_hash != f"sha256:{digest(approved_plan)}"
            or approved_hash != research.get("proposed_plan_hash")
            or approved_plan.get("methodology_build_id") != bundle.build_id
            or approved_plan.get("brief_digest") != digest(brief)
            or approved_plan.get("source_set") != {"id": source_set["id"], "version": source_set["version"]}
            or approved_plan.get("scope") != expected_scope
            or approved_plan.get("upstream_artifacts") != expected_upstream
            or artifact.get("case_id") != run["case_id"]
            or artifact.get("run_id") != run["id"]
            or artifact.get("module_id") != "CP-DR"
            or artifact.get("input_fingerprint") != expected_fingerprint
        ):
            return False
        host_identity = {
            "module_id": "CP-DR",
            "run_id": run["id"],
            "case_id": run["case_id"],
            "profile_id": run["plan"]["profile_id"],
            "selection_id": run["plan"]["selection_id"],
            "source_set_id": source_set["id"],
            "source_set_version": source_set["version"],
            "approved_plan_hash": approved_hash,
            "upstream_digests": [item["digest"] for item in expected_upstream],
            "scope_type": brief["scope_type"],
            "scope_key": brief["scope_key"],
            "subject_name": brief["subject_name"],
            "research_question": brief["research_question"],
            "reporting_period": brief["as_of_date"],
            "source_mode": "supplied_only",
        }
        transport = envelope["transport"]
        if not isinstance(transport, dict):
            return False
        pinned_sources: dict[str, dict[str, Any]] = {}
        for source_id in source_set["source_ids"]:
            source = store.sources.get(source_id)
            source_digest = (source or {}).get("sha256")
            blocks = (source or {}).get("blocks")
            if (
                not source
                or source.get("case_id") != run["case_id"]
                or source.get("withdrawn")
                or not isinstance(source_digest, str)
                or len(source_digest) != 64
                or any(character not in "0123456789abcdef" for character in source_digest)
                or not isinstance(blocks, list)
                or len({block.get("block_id") for block in blocks if isinstance(block, dict)}) != len(blocks)
            ):
                return False
            pinned_sources[source_id] = source
        returned_evidence: dict[tuple[str, str], dict[str, str]] = {}
        for row in transport.get("evidence", []):
            if not isinstance(row, dict):
                return False
            source = pinned_sources.get(row.get("source_id"))
            if source is None:
                return False
            blocks = [item for item in source.get("blocks", []) if item.get("block_id") == row.get("block_id")]
            if len(blocks) != 1:
                return False
            block = blocks[0]
            source_digest = source["sha256"]
            returned_evidence[(source["id"], block["block_id"])] = {
                "source_digest": source_digest,
                "origin_family": source_digest,
                "authority_class": "unclassified",
                "locator": json.dumps(block.get("locator"), sort_keys=True, separators=(",", ":")),
                "extractor_version": str(block.get("extractor_version")),
                "confidence": str(block.get("confidence")),
            }
        workstream_ids = {item["id"] for item in approved_plan.get("workstreams", [])}
        payload = validate_cpdr_payload(
            transport,
            host_identity,
            workstream_ids,
            returned_evidence,
            approved_plan,
            brief,
        )
        if payload.model_dump(mode="json") != transport:
            return False
        confidence = bundle.cpdr_confidence(confidence_inputs(payload, returned_evidence))
        if envelope["host_confidence"] != confidence:
            return False
        filename, markdown = render_cpdr_markdown(payload, confidence, run["created_at"][:10], expected_upstream)
        canonical_output = envelope["canonical_output"]
        validation = bundle.validate_cpdr_handoff(markdown, filename, run["id"], brief["as_of_date"])
        return bool(
            envelope["schema_version"] == "caos.cpdr.artifact.v1"
            and envelope["module_id"] == "CP-DR"
            and envelope["methodology"]
            == {"build_id": bundle.build_id, "approved_plan_hash": approved_hash}
            and envelope["source_set"]
            == {"id": source_set["id"], "version": source_set["version"], "digest": digest(source_set)}
            and envelope["upstream_artifacts"] == expected_upstream
            and isinstance(canonical_output, dict)
            and set(canonical_output) == {"filename", "markdown_sha256"}
            and canonical_output == {
                "filename": filename,
                "markdown_sha256": hashlib.sha256(markdown.encode("utf-8")).hexdigest(),
            }
            and artifact.get("filename") == filename
            and artifact.get("markdown") == markdown
            and artifact.get("digest") == digest(envelope)
            and not validation.identity_mismatches
            and not validation.errors
            and validation.exit_code == 0
        )
    except Exception:
        return False


def snapshot_diff(previous: dict[str, Any] | None, current: dict[str, Any]) -> dict[str, Any]:
    if not previous:
        return {"changed": True, "added": current.get("artifacts", []), "removed": [], "source_set_changed": True}
    old = {item["module_id"]: item["digest"] for item in previous.get("artifacts", [])}
    new = {item["module_id"]: item["digest"] for item in current.get("artifacts", [])}
    return {
        "changed": old != new or previous.get("source_set_id") != current.get("source_set_id"),
        "added": [{"module_id": k, "digest": v} for k, v in new.items() if k not in old],
        "removed": [{"module_id": k, "digest": v} for k, v in old.items() if k not in new],
        "modified": [{"module_id": k, "before": old[k], "after": v} for k, v in new.items() if k in old and old[k] != v],
        "source_set_changed": previous.get("source_set_id") != current.get("source_set_id"),
    }


def accepted_snapshot(store: MemoryStore, case_id: str) -> dict[str, Any] | None:
    case = store.get_case(case_id)
    snapshot_id = (case.get("visible_snapshot_id") or case.get("accepted_snapshot_id")) if case else None
    return store.get_snapshot(snapshot_id) if snapshot_id else None


def latest_accepted_snapshot(store: MemoryStore, case_id: str) -> dict[str, Any] | None:
    case = store.get_case(case_id)
    return store.get_snapshot(case["accepted_snapshot_id"]) if case and case.get("accepted_snapshot_id") else None
