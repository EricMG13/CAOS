"""Storage ports grouped by the consistency boundary that owns each transition."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol


Record = dict[str, Any]


class SourceCatalog(Protocol):
    def ingest(self, source: Record, actor: str) -> Record: ...

    def ingest_promoted_note(self, note: Record, actor: str) -> Record: ...

    def withdraw(self, case_id: str, source_id: str, actor: str) -> Record | None: ...

    def list_sources(self, case_id: str) -> list[Record]: ...

    def get_source(self, source_id: str) -> Record | None: ...

    def current_source_set(self, case_id: str) -> Record | None: ...

    def source_set(self, source_set_id: str | None) -> Record | None: ...

    def read_pinned_evidence(
        self,
        case_id: str,
        source_set_id: str,
        source_id: str,
        block_ids: list[str],
    ) -> list[Record]: ...

    def find_loan_universe_import(
        self,
        case_id: str,
        source_sha256: str,
        template_version: str,
        importer_version: str,
    ) -> Record | None: ...

    def save_loan_universe_import(
        self, record: Record, rows: list[Record], actor: str
    ) -> tuple[Record, bool]: ...

    def active_loan_universe(
        self, case_id: str, *, include_rows: bool = True
    ) -> Record | None: ...


class RunLedger(Protocol):
    def create_case(
        self, name: str, issuer: str, sector: str, actor: str
    ) -> Record: ...

    def list_cases(self, actor: str) -> list[Record]: ...

    def get_case(self, case_id: str) -> Record | None: ...

    def is_member(
        self, case_id: str, actor: str, roles: set[str] | None = None
    ) -> bool: ...

    def add_member(
        self,
        case_id: str,
        actor: str,
        member: str,
        role: str,
        actor_role: str | None = None,
    ) -> bool: ...

    def create_run_with_nodes(
        self,
        case_id: str,
        actor: str,
        plan: Record,
        nodes: list[Record],
        upgraded_from_run_id: str | None = None,
    ) -> Record: ...

    def list_runs(self, case_id: str) -> list[Record]: ...

    def get_run(self, run_id: str) -> Record | None: ...

    def latest_run(self, case_id: str) -> Record | None: ...

    def pending_runs(self) -> list[tuple[str, str]]: ...

    def claim(self, run_id: str, worker: str) -> str | None: ...

    def renew(self, run_id: str, attempt_token: str) -> bool: ...

    def is_current(self, run_id: str, attempt_token: str) -> bool: ...

    def finish(self, run_id: str, attempt_token: str) -> None: ...

    def update_run_fenced(
        self, run_id: str, attempt_token: str, **changes: Any
    ) -> None: ...

    def update_node_fenced(
        self,
        run_id: str,
        attempt_token: str,
        node_id: str,
        **changes: Any,
    ) -> None: ...

    def pause_research_plan(
        self,
        run_id: str,
        attempt_token: str,
        node_id: str,
        research: Record,
    ) -> None: ...

    def approve_research_plan(
        self, run_id: str, actor: str, plan_hash: str
    ) -> Record: ...

    def emit(self, run_id: str, event: str, data: Record) -> None: ...

    def emit_fenced(
        self,
        run_id: str,
        attempt_token: str,
        event: str,
        data: Record,
    ) -> None: ...

    def artifact_for_fingerprint(
        self, run_id: str, module_id: str, input_fingerprint: str
    ) -> Record | None: ...

    def complete_node(
        self,
        run_id: str,
        attempt_token: str,
        node_id: str,
        artifact: Record,
        research: Record | None,
        event_data: Record,
        artifact_validator: Callable[[Record], bool] | None = None,
    ) -> Record: ...

    def finalize_success(
        self,
        run_id: str,
        attempt_token: str,
        research: Record | None,
        event_data: Record,
        *,
        deadline: float | None = None,
    ) -> None: ...

    def get_artifact(self, artifact_id: str) -> Record | None: ...

    def accept_snapshot(
        self,
        case_id: str,
        run_id: str,
        actor: str,
        snapshot: Record,
    ) -> Record: ...

    def get_snapshot(self, snapshot_id: str) -> Record | None: ...

    def switch_visible_snapshot(
        self, case_id: str, snapshot_id: str, actor: str
    ) -> Record | None: ...

    def events_after(self, run_id: str, cursor: int = 0) -> list[Record]: ...

    def wait_for_events(
        self, run_id: str, cursor: int, timeout: float = 1.0
    ) -> list[Record]: ...


class PublicationLedger(Protocol):
    def append_thesis(
        self, case_id: str, actor: str, expected_version: int, thesis: Record
    ) -> Record: ...

    def list_theses(self, case_id: str) -> list[Record]: ...

    def append_recommendations(
        self,
        case_id: str,
        actor: str,
        expected_version: int,
        recommendations: Record,
    ) -> Record: ...

    def list_recommendations(self, case_id: str) -> list[Record]: ...

    def save_report_inputs(
        self,
        case_id: str,
        actor: str,
        thesis: Record,
        recommendations: Record,
        accepted_snapshot_id: str | None,
    ) -> Record: ...

    def create_note(self, case_id: str, actor: str, body: str) -> Record: ...

    def list_notes(self, case_id: str) -> list[Record]: ...

    def promote_note(self, case_id: str, note_id: str, actor: str) -> Record: ...

    def create_assumption(
        self,
        case_id: str,
        actor: str,
        statement: str,
        evidence_ids: list[str],
        affected_module_ids: list[str],
        supporting_claim: str = "",
        conflicting_claim: str = "",
    ) -> Record: ...

    def list_assumptions(self, case_id: str) -> list[Record]: ...

    def freeze_report(self, case_id: str, actor: str, report: Record) -> Record: ...

    def get_report(self, case_id: str) -> Record | None: ...

    def approve_report(
        self,
        case_id: str,
        actor: str,
        expected_status: str,
        preview_digest: str,
        input_fingerprint: str,
        comment: str | None,
    ) -> Record: ...

    def save_rv_universe(
        self, case_id: str, actor: str, universe: Record
    ) -> Record: ...

    def get_rv_universe(self, case_id: str) -> Record | None: ...

    def list_audit(self) -> list[Record]: ...

    def create_methodology_draft(self, draft: Record, actor: str) -> Record: ...

    def list_methodology_drafts(self) -> list[Record]: ...

    def validate_methodology_draft(self, draft_id: str, actor: str) -> Record: ...

    def confirm_methodology_draft(
        self, draft_id: str, actor: str, signature: str
    ) -> Record: ...


class ModelLedger(Protocol):
    def queue_build(self, build: Record, actor: str) -> tuple[Record, bool]: ...

    def retry_build(self, build_id: str, actor: str) -> Record: ...

    def get_build(self, build_id: str) -> Record | None: ...

    def list_builds(self, case_id: str) -> list[Record]: ...

    def queue_export(self, build_id: str, actor: str) -> tuple[Record, bool]: ...

    def pending_jobs(self) -> list[tuple[str, str, str]]: ...

    def claim(
        self, build_id: str, worker: str, kind: str = "calculate"
    ) -> str | None: ...

    def renew(
        self, build_id: str, attempt_token: str, kind: str = "calculate"
    ) -> bool: ...

    def is_current(
        self, build_id: str, attempt_token: str, kind: str = "calculate"
    ) -> bool: ...

    def complete(
        self,
        build_id: str,
        attempt_token: str,
        result: Record,
        actor: str,
        kind: str = "calculate",
    ) -> Record: ...

    def fail(
        self,
        build_id: str,
        attempt_token: str,
        error: Record,
        actor: str,
        kind: str = "calculate",
    ) -> Record: ...

    def record_export_download(
        self, build_id: str, case_id: str, actor: str
    ) -> None: ...
