from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
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
        self._cpdr_scripts: dict[str, Any] = {}

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

    def plan_research(self, brief: dict[str, Any], source_set_id: str, source_set_version: int, upstream_artifacts: list[dict[str, Any]]) -> tuple[dict[str, Any], str]:
        topics = list(brief.get("must_answer") or [brief["research_question"]])
        lane_count = min(3, len(topics))
        chunk_size = (len(topics) + lane_count - 1) // lane_count
        subject = brief.get("subject_name", "the issuer")
        workstreams = []
        for index in range(0, len(topics), chunk_size):
            assigned = topics[index : index + chunk_size]
            workstreams.append({
                "id": f"WS-{len(workstreams) + 1}",
                "kind": "topical",
                "question": " / ".join(assigned),
                "assigned_questions": assigned,
                "perspective": "Buy-side credit analyst",
                "hypothesis": f"The supplied evidence can resolve the defined credit question for {subject}.",
                "evidence_needs": assigned,
                "source_classes": ["supplied_case_sources"],
                "disconfirming_test": "Identify supplied evidence that contradicts the working credit conclusion.",
                "completion_test": "Answer every assigned question with source locators or record the evidence gap.",
                "effort_cap": "Within the fixed standard research budget.",
            })
        workstreams.extend([
            {
                "id": f"WS-{len(workstreams) + 1}",
                "kind": "synthesis",
                "question": f"What cross-workstream credit conclusion follows for {subject}?",
                "perspective": "Cross-workstream synthesis",
                "hypothesis": "The workstreams support one decision-useful conclusion without exceeding the approved scope.",
                "evidence_needs": ["Completed topical workstreams and their cited supplied evidence."],
                "source_classes": ["supplied_case_sources"],
                "disconfirming_test": "Reconcile contradictions and refuse a conclusion where evidence remains insufficient.",
                "completion_test": "State the direct answer, material disagreement, gaps, and decision implications.",
                "effort_cap": "One synthesis pass within the fixed standard research budget.",
            },
            {
                "id": f"WS-{len(workstreams) + 2}",
                "kind": "adversarial",
                "question": f"What would make the proposed credit conclusion for {subject} wrong?",
                "perspective": "Adversarial credit reviewer",
                "hypothesis": "A plausible downside or contrary reading can be tested from the supplied evidence.",
                "evidence_needs": ["Contrary facts, missing periods, perimeter conflicts, and excluded-scope checks."],
                "source_classes": ["supplied_case_sources"],
                "disconfirming_test": "Attempt to overturn each material conclusion with the strongest supplied counter-evidence.",
                "completion_test": "Record surviving objections, rebuttals, and unresolved downside evidence gaps.",
                "effort_cap": "One adversarial pass within the fixed standard research budget.",
            },
        ])
        plan = {
            "methodology_build_id": self.build_id,
            "brief_digest": digest(brief),
            "source_set": {"id": source_set_id, "version": source_set_version},
            "upstream_artifacts": upstream_artifacts,
            "scope": {"type": brief.get("scope_type"), "key": brief.get("scope_key"), "source_mode": brief.get("source_mode")},
            "workstreams": workstreams,
        }
        return plan, f"sha256:{digest(plan)}"

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

    def _load_cpdr_script(self, name: str) -> Any:
        cached = self._cpdr_scripts.get(name)
        if cached is not None:
            return cached
        path = self.root / "skills" / "cp-dr-deep-research" / "scripts" / f"{name}.py"
        module_name = f"caos_deploy_v_cpdr_{name}_{hashlib.sha256(str(path).encode()).hexdigest()[:12]}"
        registered = sys.modules.get(module_name)
        if registered is not None:
            self._cpdr_scripts[name] = registered
            return registered
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            raise MethodologyError(f"cannot load CP-DR authority script: {name}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        try:
            spec.loader.exec_module(module)
        except BaseException:
            sys.modules.pop(module_name, None)
            raise
        self._cpdr_scripts[name] = module
        return module

    def cpdr_confidence(self, inputs: dict[str, Any]) -> dict[str, Any]:
        module = self._load_cpdr_script("confidence_score")
        return module.compute(
            inputs["lineage_counts"],
            inputs["fields_present"],
            inputs["fields_total"],
            inputs["source_gate"],
            inputs["findings"],
        )

    def cpdr_authority(self) -> str:
        self.verify()
        folder = self.root / "skills" / "cp-dr-deep-research"
        skill = (folder / "SKILL.md").read_text(encoding="utf-8")
        steps = (folder / "references" / "REF_CP-DR_STEPS.md").read_text(encoding="utf-8")

        def section(text: str, heading: str, end_marker: str = "\n## ") -> str:
            try:
                start = text.index(heading)
            except ValueError as exc:
                raise MethodologyError(f"missing CP-DR authority section: {heading}") from exc
            end = text.find(end_marker, start + len(heading))
            return text[start : end if end >= 0 else len(text)].strip()

        source_data_rule = next(
            (line.strip() for line in skill.splitlines() if line.startswith("> Source, email, web, document")),
            None,
        )
        if source_data_rule is None:
            raise MethodologyError("missing CP-DR untrusted-source authority")
        hard_rules = section(skill, "#### HARD RULES", "\n<!-- READING_ORDER:BEGIN -->")
        selected = [
            section(steps, "## REF_CP-DR_C_SourceAndSearchPolicy.md"),
            section(steps, "## REF_CP-DR_D_ClaimEvidenceLedger.md"),
            section(steps, "## REF_CP-DR_E_SynthesisAndStopRules.md"),
            section(steps, "## REF_CP-DR_F_OutputAndQA.md"),
            section(steps, "## REF_CP-DR_H_IssuerProfile.md"),
        ]
        wrapper = """CAOS HOST COMPATIBILITY WRAPPER
CP-0 is required with matching accepted run and source-set lineage. Source mode is supplied_only and evidence is available only through read_evidence. Execute only the exact approved issuer plan and immutable brief. Return exactly one strict CPDRPayload JSON value; the host owns coverage, confidence, canonical Markdown, validation, fencing, and persistence."""
        return "\n\n".join((wrapper, source_data_rule, hard_rules, *selected))

    def validate_cpdr_handoff(
        self,
        text: str,
        filename: str,
        run_id: str,
        reporting_period: str,
    ) -> Any:
        module = self._load_cpdr_script("validate_handoff")
        return module.validate_text(
            text,
            filename=filename,
            expected_module="CP-DR",
            expected_run_id=run_id,
            expected_period=reporting_period,
        )
