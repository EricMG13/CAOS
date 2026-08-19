from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from ..contracts import Depth, INTERNAL_PATHWAYS, digest


class MethodologyError(ValueError):
    pass


class DeployVBundle:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.manifest = self._read("DEPLOY_V_MANIFEST.json")
        self.integrity = self._read("DEPLOY_V_INTEGRITY_v1.json")
        self.retrieval = self._read("CP_DEPLOY_V_RETRIEVAL_INDEX_v1.json")
        self.profiles = self._read("CP_DEPLOY_V_EXECUTION_PROFILES_v1.json")
        self.catalog = self._read("skills/cp-os-credit-os/references/CREDIT_OS_V_MODULE_CATALOG_v2.json")

    def _read(self, name: str) -> dict[str, Any]:
        path = self.root / name
        if not path.is_file():
            raise MethodologyError(f"missing Deploy V authority: {name}")
        return json.loads(path.read_text(encoding="utf-8"))

    @property
    def build_id(self) -> str:
        return self.integrity["build_id"]

    def verify(self) -> dict[str, Any]:
        checked = 0
        mismatches: list[str] = []
        for skill in self.integrity["skills"]:
            folder = self.root / "skills" / skill["folder_slug"]
            for relative, expected in skill["relative_file_hashes"].items():
                checked += 1
                path = folder / relative
                if not path.is_file():
                    mismatches.append(f"missing:{skill['folder_slug']}/{relative}")
                    continue
                data = path.read_bytes()
                actual = hashlib.sha256(data).hexdigest()
                if len(data) != expected["bytes"] or actual != expected["sha256"]:
                    mismatches.append(f"changed:{skill['folder_slug']}/{relative}")
        if mismatches:
            raise MethodologyError(f"Deploy V integrity mismatch: {mismatches[:5]}")
        return {"build_id": self.build_id, "checked": checked, "mismatches": 0, "logical_entries": self.manifest["logical_skill_count"], "physical_skills": self.manifest["physical_skill_count"]}

    def _selection(self, pathway: str, depth: Depth) -> tuple[str, str]:
        depth = Depth(depth)
        if pathway not in INTERNAL_PATHWAYS:
            raise MethodologyError("unknown pathway")
        if depth is Depth.FULL:
            return "FULL_CREDIT_32", pathway if pathway != "FULL_CREDIT" else "FULL_CREDIT_ASSESSMENT"
        return "LITE_CREDIT_22", f"LITE_{'FULL_CREDIT_SCREEN' if pathway == 'FULL_CREDIT' else pathway}"

    def compile(self, pathway: str, depth: Depth, source_set_id: str | None, focus_questions: list[str] | None = None, source_set_version: int | None = None) -> dict[str, Any]:
        depth = Depth(depth)
        profile_id, selection_id = self._selection(pathway, depth)
        profile = self.catalog["profiles"][profile_id]
        try:
            route = profile["pathways"][selection_id]
        except KeyError as exc:
            raise MethodologyError("unknown route identity") from exc
        route_nodes = route["nodes"]
        allowed = {node["module_id"] for node in route_nodes}
        dependencies = {module_id: [] for module_id in allowed}
        for edge in self.catalog["navigation"]["dependencies"]:
            source, target = edge["source"], edge["target"]
            if target in allowed and source in allowed:
                dependencies[target].append(source)
        for module_id in allowed:
            if module_id != "CP-0" and not dependencies[module_id]:
                dependencies[module_id] = ["CP-0"]
        nodes = [{
            "module_id": "CP-PARSE",
            "module_name": "DataPreparation",
            "route_node_id": f"RN-{profile_id}-{selection_id}-00-CP-PARSE",
            "stage": 0,
            "dependencies": [],
        }]
        for node in route_nodes:
            nodes.append({**node, "dependencies": ["CP-PARSE"] if node["module_id"] == "CP-0" else sorted(dependencies[node["module_id"]])})
        plan = {
            "build_id": self.build_id,
            "profile_id": profile_id,
            "selection_id": selection_id,
            "pathway": pathway,
            "depth": depth.value,
            "source_set_id": source_set_id,
            "source_set_version": source_set_version,
            "focus_questions": [question[:400] for question in (focus_questions or [])[:5]],
            "nodes": nodes,
            "host_rules": {"prepend": "CP-PARSE", "cp0_requires": "CP-PARSE_DIGEST", "markdown_renderer": "caos.deploy-v.v1"},
            "invocation_plan": {"qualifiers": [], "optional_method_ids": [], "upstream_artifact_ids": [], "focus_questions": [question[:400] for question in (focus_questions or [])[:5]], "gaps": [], "conflicts": [], "evidence_refs": []},
        }
        plan["plan_digest"] = digest(plan)
        return plan

    def validate_payload(self, payload: dict[str, Any], module_id: str) -> dict[str, Any]:
        required = {"module_id", "schema_version", "status", "summary", "evidence_refs", "lineage", "narrative", "authority", "confidence", "provenance"}
        missing = sorted(required - payload.keys())
        if missing or payload.get("module_id") != module_id or payload.get("status") not in {"COMPLETE", "BLOCKED", "NOT_APPLICABLE"}:
            raise MethodologyError(f"invalid typed payload for {module_id}: missing={missing}")
        return payload

    def render_markdown(self, payload: dict[str, Any]) -> str:
        self.validate_payload(payload, payload["module_id"])
        sections = payload["narrative"]
        lines = [
            f"# {payload['module_id']} — {payload['status']}",
            "",
            f"- Schema version: `{payload['schema_version']}`",
            f"- Artifact digest: `{digest(payload)}`",
            f"- Lineage: `{payload['lineage'].get('input_fingerprint', 'unavailable')}`",
            "",
            "## Summary",
            "",
            payload["summary"],
        ]
        for title in ("Takeaway", "Basis", "Exceptions"):
            if sections.get(title.lower()):
                lines.extend(["", f"## {title}", "", sections[title.lower()]])
        lines.extend(["", "## Evidence references", "", *[f"- `{ref}`" for ref in payload["evidence_refs"]]])
        return "\n".join(lines).rstrip() + "\n"

    def route_golden_cases(self) -> list[tuple[str, Depth]]:
        return [(pathway, depth) for pathway in INTERNAL_PATHWAYS for depth in (Depth.FULL, Depth.SCREEN)]
