"""Exact Frozen/Filed Deliverable publication boundary."""

from __future__ import annotations

import copy
import hashlib
from pathlib import Path
from typing import Any

from ..artifacts.domain import latest_accepted_snapshot
from ..atomic_files import publish_hash_addressed_bytes
from ..contracts import DeliverableDraftRequest, clean_json, digest
from ..ledgers import ModelLedger, PublicationLedger, RunLedger, SourceCatalog
from .domain import DeliverableService
from .renderers import (
    FROZEN_SCHEMA_VERSION,
    RENDERER_IDENTITY,
    render_frozen_exports,
)
from .templates import template_for


MAX_DELIVERABLE_EXPORT_BYTES = 64 * 1024 * 1024
FILED_STATUSES = frozenset({"FILED", "SUPERSEDED"})


class DeliverablePublicationService:
    """Freeze, revalidate, and file exact structured deliverable revisions."""

    def __init__(
        self,
        publications: PublicationLedger,
        runs: RunLedger,
        sources: SourceCatalog,
        models: ModelLedger,
        authoring: DeliverableService,
        methodology: Any,
        storage_dir: Path,
    ) -> None:
        self.publications = publications
        self.runs = runs
        self.sources = sources
        self.models = models
        self.authoring = authoring
        self.methodology = methodology
        self.storage_dir = storage_dir

    @staticmethod
    def _draft_request(draft: dict[str, Any]) -> DeliverableDraftRequest:
        content = draft.get("content") or {}
        return DeliverableDraftRequest.model_validate(
            {
                "expected_version": draft["version"] - 1,
                "template_id": content.get("template_id"),
                "template_version": content.get("template_version"),
                "model_selection": content.get("model_selection"),
                "blocks": content.get("blocks"),
            }
        )

    def _current_draft(
        self, case_id: str, pathway: str, draft_id: str
    ) -> dict[str, Any]:
        history = self.publications.list_deliverable_revisions(case_id, pathway)
        current = history[-1] if history else None
        if current is None or current.get("id") != draft_id:
            raise ValueError("DELIVERABLE_DRAFT_STALE")
        return current

    def _methodology_identity(self) -> dict[str, Any]:
        build_id = getattr(self.methodology, "build_id", None)
        if not isinstance(build_id, str) or not build_id:
            raise ValueError("DELIVERABLE_METHODOLOGY_UNAVAILABLE")
        return {"build_id": build_id, "build_digest": digest({"build_id": build_id})}

    def _authority_identity(self, case_id: str) -> dict[str, Any]:
        snapshot = latest_accepted_snapshot(self.runs, case_id)
        if snapshot is None or snapshot.get("case_id") != case_id:
            raise ValueError("DELIVERABLE_ACCEPTED_AUTHORITY_REQUIRED")
        source_set = self.sources.source_set(snapshot.get("source_set_id"))
        if (
            source_set is None
            or source_set.get("case_id") != case_id
            or source_set.get("id") != snapshot.get("source_set_id")
        ):
            raise ValueError("DELIVERABLE_SOURCE_AUTHORITY_STALE")
        return {
            "accepted_snapshot_id": snapshot["id"],
            "accepted_snapshot_digest": digest(snapshot),
            "source_set_id": source_set["id"],
            "source_set_version": source_set.get("version"),
            "source_set_digest": digest(source_set),
        }

    def _evidence_identity(
        self, case_id: str, blocks: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        references: dict[str, set[str]] = {}
        for block in blocks:
            for citation in block.get("citations") or []:
                references.setdefault(citation["source_id"], set()).update(
                    citation["block_ids"]
                )
        evidence: list[dict[str, Any]] = []
        for source_id in sorted(references):
            source = self.sources.get_source(source_id)
            available = {
                block.get("block_id") for block in (source or {}).get("blocks", [])
            }
            if (
                source is None
                or source.get("case_id") != case_id
                or source.get("withdrawn")
                or not references[source_id].issubset(available)
            ):
                raise ValueError("DELIVERABLE_EVIDENCE_STALE")
            evidence.append(
                {
                    "source_id": source_id,
                    "sha256": source.get("sha256"),
                    "block_ids": sorted(references[source_id]),
                    "withdrawn": False,
                }
            )
        return evidence

    def _validated_content(
        self, case_id: str, pathway: str, draft: dict[str, Any]
    ) -> tuple[dict[str, Any], dict[str, Any] | None]:
        template = template_for(pathway)
        request = self._draft_request(draft)
        if (
            request.template_id != template["template_id"]
            or request.template_version != template["template_version"]
        ):
            raise ValueError("DELIVERABLE_TEMPLATE_STALE")
        dumped = request.model_dump(mode="json")
        selection = dumped["model_selection"]
        _eligible, model_record = self.authoring._validate_model(case_id, selection)
        model_identity = self.authoring._pinned_model_identity(selection, model_record)
        if template["model_requirement"] == "REQUIRED" and model_identity is None:
            raise ValueError("DELIVERABLE_MODEL_REQUIRED")
        generated = self.authoring._validate_blocks(
            case_id,
            pathway,
            dumped["blocks"],
            model_record,
            model_identity,
        )
        expected_content = {
            "template_id": request.template_id,
            "template_version": request.template_version,
            "model_selection": selection,
            "model_identity": model_identity,
            "blocks": dumped["blocks"],
            "generated_blocks": generated,
        }
        if (
            draft.get("content") != expected_content
            or draft.get("digest") != digest(expected_content)
        ):
            raise ValueError("DELIVERABLE_DRAFT_AUTHORITY_STALE")
        pinned_model = copy.deepcopy(model_identity)
        if pinned_model is not None and model_record is not None:
            build = (
                model_record
                if selection and selection["kind"] == "APPLICATION_BUILD"
                else self.models.get_build(pinned_model["build_id"])
            )
            build_payload = (build or {}).get("payload")
            build_qa = (build or {}).get("qa")
            if (
                build is None
                or build.get("id") != pinned_model.get("build_id")
                or build.get("case_id") != case_id
                or build.get("status") != "READY"
                or build.get("accepted_snapshot_id")
                != pinned_model.get("accepted_snapshot_id")
                or build.get("input_fingerprint")
                != pinned_model.get("build_input_fingerprint")
                or build.get("payload_digest")
                != pinned_model.get("build_payload_digest")
                or not isinstance(build_payload, dict)
                or digest(build_payload) != build.get("payload_digest")
                or not isinstance(build_qa, dict)
            ):
                raise ValueError("DELIVERABLE_MODEL_AUTHORITY_STALE")
            build_export = build.get("export") or {}
            pinned_model["application_build"] = {
                "payload": copy.deepcopy(build_payload),
                "qa": copy.deepcopy(build_qa),
                "calculation_runtime": copy.deepcopy(
                    build.get("calculation_runtime") or {}
                ),
                "export": (
                    {
                        "sha256": build_export["sha256"],
                        "size": build_export["size"],
                        "filename": build_export.get("filename"),
                    }
                    if build_export.get("status") == "READY"
                    and isinstance(build_export.get("sha256"), str)
                    and isinstance(build_export.get("size"), int)
                    else None
                ),
            }
            export = model_record.get("export") or {}
            pinned_model["model_export"] = (
                {
                    "sha256": export["sha256"],
                    "size": export["size"],
                    "filename": export.get("filename"),
                }
                if export.get("status") == "READY"
                and isinstance(export.get("sha256"), str)
                and isinstance(export.get("size"), int)
                else None
            )
            if selection and selection["kind"] == "ANALYST_REVISION":
                assumptions = model_record.get("effective_assumptions")
                outputs = model_record.get("outputs")
                if (
                    not isinstance(assumptions, list)
                    or digest(assumptions) != model_record.get("assumptions_digest")
                    or not isinstance(outputs, dict)
                    or digest(outputs) != model_record.get("outputs_digest")
                ):
                    raise ValueError("DELIVERABLE_MODEL_AUTHORITY_STALE")
                pinned_model["effective_assumptions"] = copy.deepcopy(assumptions)
                pinned_model["assumption_gaps"] = [
                    copy.deepcopy(row)
                    for row in assumptions
                    if row.get("status") != "READY" or row.get("gap_code")
                ]
                pinned_model["outputs"] = copy.deepcopy(outputs)
                pinned_model["debt"] = {
                    case: {
                        period_id: {
                            output_id: copy.deepcopy(values[output_id])
                            for output_id in ("total_debt_reported", "net_debt")
                            if output_id in values
                        }
                        for period_id, values in (outputs.get(case) or {}).items()
                        if isinstance(values, dict)
                    }
                    for case in ("BASE", "DOWNSIDE")
                    if isinstance(outputs.get(case), dict)
                }
            pinned_model["warnings"] = {
                "limitation_flags": copy.deepcopy(
                    build_qa.get("limitation_flags") or []
                ),
                "validation_warnings": copy.deepcopy(
                    build_qa.get("validation_warnings") or []
                ),
            }
        return expected_content, pinned_model

    def _payload(
        self, case_id: str, pathway: str, draft: dict[str, Any]
    ) -> dict[str, Any]:
        template = template_for(pathway)
        content, model = self._validated_content(case_id, pathway, draft)
        authority = self._authority_identity(case_id)
        if model is not None and model.get("accepted_snapshot_id") != authority.get(
            "accepted_snapshot_id"
        ):
            raise ValueError("DELIVERABLE_MODEL_AUTHORITY_STALE")
        evidence = self._evidence_identity(case_id, content["blocks"])
        methodology = self._methodology_identity()
        input_fingerprint = digest(
            clean_json(
                {
                    "draft": {
                        "id": draft["id"],
                        "version": draft["version"],
                        "digest": draft["digest"],
                    },
                    "authority": authority,
                    "model": model,
                    "evidence": evidence,
                    "template": {
                        "template_id": template["template_id"],
                        "template_version": template["template_version"],
                    },
                    "methodology": methodology,
                    "renderer": RENDERER_IDENTITY,
                }
            )
        )
        payload = {
            "schema_version": FROZEN_SCHEMA_VERSION,
            "case_id": case_id,
            "pathway": pathway,
            "draft": {
                "id": draft["id"],
                "version": draft["version"],
                "digest": draft["digest"],
            },
            "template": {
                "template_id": template["template_id"],
                "template_version": template["template_version"],
                "title": template["title"],
            },
            "authority": authority,
            "model": model,
            "content": copy.deepcopy(content),
            "evidence": evidence,
            "methodology": methodology,
            "renderer": copy.deepcopy(RENDERER_IDENTITY),
            "input_fingerprint": input_fingerprint,
        }
        payload["preview_digest"] = digest(payload)
        return payload

    def freeze(
        self,
        case_id: str,
        pathway: str,
        actor: str,
        draft_id: str,
        draft_version: int,
        draft_digest: str,
    ) -> dict[str, Any]:
        draft = self._current_draft(case_id, pathway, draft_id)
        if draft.get("version") != draft_version or draft.get("digest") != draft_digest:
            raise ValueError("DELIVERABLE_DRAFT_STALE")
        payload = self._payload(case_id, pathway, draft)
        rendered = render_frozen_exports(payload)
        exports: dict[str, dict[str, Any]] = {}
        for format_name, content in rendered.items():
            checksum = hashlib.sha256(content).hexdigest()
            _path, vault_key, size = publish_hash_addressed_bytes(
                self.storage_dir,
                (
                    "deliverables",
                    case_id,
                    pathway,
                    payload["preview_digest"],
                ),
                format_name,
                content,
                expected_sha256=checksum,
                max_bytes=MAX_DELIVERABLE_EXPORT_BYTES,
            )
            exports[format_name] = {
                "format": format_name,
                "vault_key": vault_key,
                "sha256": checksum,
                "size": size,
                "renderer_identity": copy.deepcopy(RENDERER_IDENTITY),
            }
        return self.publications.append_frozen_deliverable(
            case_id,
            pathway,
            actor,
            draft["id"],
            draft["version"],
            draft["digest"],
            {
                "payload": payload,
                "digest": digest(payload),
                "preview_digest": payload["preview_digest"],
                "input_fingerprint": payload["input_fingerprint"],
                "authority_identity": payload["authority"],
                "model_identity": payload["model"],
                "template_identity": payload["template"],
                "render_identity": payload["renderer"],
            },
            exports,
        )

    def _revalidate_frozen(
        self, case_id: str, record: dict[str, Any]
    ) -> None:
        if record.get("case_id") != case_id or record.get("status") != "FROZEN":
            raise ValueError("DELIVERABLE_FROZEN_CONFLICT")
        payload = record.get("payload") or {}
        draft = self._current_draft(case_id, record["pathway"], payload["draft"]["id"])
        rebuilt = self._payload(case_id, record["pathway"], draft)
        if (
            rebuilt != payload
            or digest(payload) != record.get("digest")
            or payload.get("preview_digest") != record.get("preview_digest")
            or payload.get("input_fingerprint") != record.get("input_fingerprint")
        ):
            raise ValueError("DELIVERABLE_FROZEN_AUTHORITY_STALE")

    def file(
        self,
        case_id: str,
        deliverable_id: str,
        actor: str,
        preview_digest: str,
        input_fingerprint: str,
    ) -> dict[str, Any]:
        record = self.publications.get_frozen_deliverable(deliverable_id)
        if record is None:
            raise ValueError("DELIVERABLE_FROZEN_NOT_FOUND")
        self._revalidate_frozen(case_id, record)
        return self.publications.file_deliverable(
            case_id,
            deliverable_id,
            actor,
            preview_digest,
            input_fingerprint,
        )

    def request_changes(
        self,
        case_id: str,
        deliverable_id: str,
        actor: str,
        preview_digest: str,
        input_fingerprint: str,
        comment: str,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        record = self.publications.get_frozen_deliverable(deliverable_id)
        if record is None:
            raise ValueError("DELIVERABLE_FROZEN_NOT_FOUND")
        self._revalidate_frozen(case_id, record)
        return self.publications.request_deliverable_changes(
            case_id,
            deliverable_id,
            actor,
            preview_digest,
            input_fingerprint,
            comment,
        )
