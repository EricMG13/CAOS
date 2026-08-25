"""Narrow fault-injection helpers for memory-ledger tests only."""

from __future__ import annotations

from typing import Any

import copy

from caos.store import now_iso


def seed_source(
    ledger_set: Any,
    case_id: str,
    actor: str,
    *,
    filename: str = "source.txt",
    sha256: str = "0" * 64,
    blocks: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return ledger_set.sources.ingest(
        {
            "case_id": case_id,
            "filename": filename,
            "media_type": "text/plain",
            "bytes": 1,
            "sha256": sha256,
            "blocks": blocks or [],
        },
        actor,
    )


def seed_source_set(
    ledger_set: Any,
    case_id: str,
    actor: str,
    sources: list[dict[str, Any]],
    *,
    source_set_id: str = "set-test",
) -> dict[str, Any]:
    """Seed stable source identities required by canonical fixture payloads."""
    state = ledger_set.sources._state
    source_set = {
        "id": source_set_id,
        "case_id": case_id,
        "version": 1,
        "source_ids": [source["id"] for source in sources],
        "created_by": actor,
        "created_at": now_iso(),
    }
    with state.lock:
        for source in sources:
            state.sources[source["id"]] = {
                **copy.deepcopy(source),
                "case_id": case_id,
                "created_by": actor,
                "created_at": now_iso(),
                "withdrawn": False,
            }
        state.source_sets[case_id] = copy.deepcopy(source_set)
        state.source_set_history[source_set_id] = copy.deepcopy(source_set)
    return copy.deepcopy(source_set)


def remove_source_set(ledger_set: Any, source_set_id: str) -> None:
    state = ledger_set.sources._state
    with state.lock:
        state.source_set_history.pop(source_set_id, None)


def remove_source(ledger_set: Any, source_id: str) -> None:
    state = ledger_set.sources._state
    with state.lock:
        state.sources.pop(source_id, None)


def mutate_run(ledger_set: Any, run_id: str, **changes: Any) -> None:
    state = ledger_set.runs._state
    with state.lock:
        state.runs[run_id].update(changes)


def mutate_job(ledger_set: Any, run_id: str, **changes: Any) -> None:
    state = ledger_set.runs._state
    with state.lock:
        state.jobs[run_id].update(changes)


def list_artifacts(
    ledger_set: Any,
    *,
    run_id: str | None = None,
    module_id: str | None = None,
) -> list[dict[str, Any]]:
    state = ledger_set.runs._state
    with state.lock:
        return [
            copy.deepcopy(artifact)
            for artifact in state.artifacts.values()
            if (run_id is None or artifact.get("run_id") == run_id)
            and (module_id is None or artifact.get("module_id") == module_id)
        ]


def replace_artifact(
    ledger_set: Any, artifact_id: str, artifact: dict[str, Any]
) -> None:
    state = ledger_set.runs._state
    with state.lock:
        state.artifacts[artifact_id] = copy.deepcopy(artifact)


def remove_artifact(ledger_set: Any, artifact_id: str) -> None:
    state = ledger_set.runs._state
    with state.lock:
        state.artifacts.pop(artifact_id, None)


def mutate_node(ledger_set: Any, node_id: str, **changes: Any) -> None:
    state = ledger_set.runs._state
    with state.lock:
        state.nodes[node_id].update(changes)


def mutate_source(ledger_set: Any, source_id: str, **changes: Any) -> None:
    state = ledger_set.sources._state
    with state.lock:
        state.sources[source_id].update(changes)


def replace_current_source_set(
    ledger_set: Any, case_id: str, source_set: dict[str, Any]
) -> None:
    state = ledger_set.sources._state
    with state.lock:
        state.source_sets[case_id] = copy.deepcopy(source_set)


def append_audit_event(
    ledger_set: Any, action: str, actor: str, **details: Any
) -> None:
    state = ledger_set.publications._state
    with state.lock:
        state.audit_event(action, actor, **copy.deepcopy(details))


def mutate_model_build(ledger_set: Any, build_id: str, **changes: Any) -> None:
    state = ledger_set.models._state
    with state.lock:
        state.model_builds[build_id].update(changes)


def mutate_model_job(
    ledger_set: Any, build_id: str, kind: str = "calculate", **changes: Any
) -> None:
    state = ledger_set.models._state
    with state.lock:
        state.model_jobs[f"{build_id}:{kind}"].update(changes)


def tamper_thesis_version(
    ledger_set: Any,
    case_id: str,
    version: int,
    *,
    postgres_dsn: str | None = None,
) -> None:
    """Corrupt an immutable authority row to verify approval-time revalidation."""
    state = getattr(ledger_set.publications, "_state", None)
    if state is not None:
        with state.lock:
            thesis = next(
                row
                for row in state.theses[case_id]
                if row.get("version") == version
            )
            thesis["core_thesis"] = "tampered after freeze"
        return
    if postgres_dsn is None:
        raise AssertionError("PostgreSQL authority tamper requires a test DSN")
    import psycopg

    with psycopg.connect(postgres_dsn) as connection, connection.cursor() as cursor:
        cursor.execute(
            "UPDATE thesis_versions "
            "SET value=jsonb_set(value, '{core_thesis}', to_jsonb(%s::text)) "
            "WHERE case_id=%s AND version=%s",
            ("tampered after freeze", case_id, version),
        )
        assert cursor.rowcount == 1
