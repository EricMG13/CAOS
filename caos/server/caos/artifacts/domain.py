from __future__ import annotations

import copy
from typing import Any

from ..contracts import RecommendationMatrixRequest, ThesisRequest, digest
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
                if (source and source.get("case_id") == case_id) or (snapshot and snapshot.get("case_id") == case_id):
                    continue
            raise ValueError("EVIDENCE_CASE_MISMATCH")


def save_thesis(store: MemoryStore, case_id: str, actor: str, request: ThesisRequest) -> dict[str, Any]:
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
    result = store.append_version(store.theses, case_id, request.expected_version, value)
    store.audit_event("thesis.versioned", actor, case_id=case_id, version=result["version"])
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
    result = store.append_version(store.recommendations, case_id, request.expected_version, value)
    store.audit_event("recommendation.versioned", actor, case_id=case_id, version=result["version"])
    return result


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
        store.notes.setdefault(case_id, []).append(note)
    store.persist()
    store.audit_event("note.created", actor, case_id=case_id, note_id=note["id"])
    return copy.deepcopy(note)


def promote_note(store: MemoryStore, case_id: str, note_id: str, actor: str) -> dict[str, Any]:
    with store.lock:
        note = next((note for note in store.notes.get(case_id, []) if note["id"] == note_id), None)
        if not note:
            raise KeyError("NOTE_NOT_FOUND")
        if note["author"] != actor:
            raise PermissionError("only note author can promote")
        if note["promoted"]:
            return copy.deepcopy(note)
        source_id = store._id("src-note")
        note["promoted"] = True
        note["promoted_source_id"] = source_id
        store.sources[source_id] = {
            "id": source_id,
            "case_id": case_id,
            "filename": f"analyst-note-{note_id}.md",
            "media_type": "text/markdown",
            "bytes": len(note["body"].encode()),
            "sha256": digest({"note_id": note_id, "body": note["body"]}),
            "vault_path": None,
            "blocks": [{"block_id": "b00001", "locator": {"note_id": note_id}, "text": note["body"], "extractor_version": "analyst-note-v1", "confidence": "HIGH", "untrusted_data": True}],
            "created_by": actor,
            "created_at": now_iso(),
            "withdrawn": False,
            "source_kind": "analyst_note",
        }
        current = store.source_sets.get(case_id)
        active_source_ids = [existing_id for existing_id in (current["source_ids"] if current else []) if not store.sources.get(existing_id, {}).get("withdrawn")]
        new_source_set = {
            "id": store._id("set"),
            "case_id": case_id,
            "version": (current["version"] + 1) if current else 1,
            "source_ids": [*active_source_ids, source_id],
            "created_by": actor,
            "created_at": now_iso(),
        }
        store.register_source_set(new_source_set)
        store.persist()
    store.audit_event("note.promoted", actor, case_id=case_id, note_id=note_id, source_id=source_id)
    return copy.deepcopy(note)


def create_assumption(store: MemoryStore, case_id: str, actor: str, statement: str, evidence_ids: list[str], affected_module_ids: list[str], supporting_claim: str = "", conflicting_claim: str = "") -> dict[str, Any]:
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
    with store.lock:
        store.assumptions.setdefault(case_id, []).append(assumption)
    store.persist()
    store.audit_event("assumption.created", actor, case_id=case_id, assumption_id=assumption["id"])
    return copy.deepcopy(assumption)


def mark_assumptions_stale(store: MemoryStore, case_id: str, changed_source_ids: set[str]) -> None:
    with store.lock:
        changed = False
        for assumption in store.assumptions.get(case_id, []):
            if changed_source_ids.intersection(assumption["evidence_ids"]):
                assumption["stale"] = True
                assumption["status"] = "STALE"
                changed = True
        if changed:
            store.persist()


def build_snapshot_payload(store: MemoryStore, run: dict[str, Any]) -> dict[str, Any]:
    artifacts = [store.get_artifact(node["artifact_id"]) for node in run["nodes"] if node.get("artifact_id")]
    artifacts = [artifact for artifact in artifacts if artifact]
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
