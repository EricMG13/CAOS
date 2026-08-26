"""Server-owned structured Deliverable templates."""

from __future__ import annotations

from typing import Any


TEMPLATE_VERSION = "caos.deliverable-template.v1"

OPTIONAL_BLOCKS = (
    {
        "kind": "GENERATED_METRIC",
        "slot_stem": "appendix.generated-metric",
        "max_items": 20,
        "order": 1,
        "model_dependent": True,
    },
    {
        "kind": "GENERATED_TABLE",
        "slot_stem": "appendix.generated-table",
        "max_items": 20,
        "order": 2,
        "model_dependent": True,
    },
    {
        "kind": "GENERATED_CHART",
        "slot_stem": "appendix.generated-chart",
        "max_items": 20,
        "order": 3,
        "model_dependent": True,
    },
    {
        "kind": "SCENARIO_EXHIBIT",
        "slot_stem": "appendix.scenario",
        "max_items": 20,
        "order": 4,
        "model_dependent": True,
    },
    {
        "kind": "MODEL_APPENDIX",
        "slot_stem": "appendix.model-appendix",
        "max_items": 1,
        "order": 5,
        "model_dependent": True,
    },
    {
        "kind": "LIMITATIONS",
        "slot_stem": "appendix.limitations",
        "max_items": 1,
        "order": 6,
        "model_dependent": False,
    },
)


def _template(
    pathway: str,
    title: str,
    sections: tuple[str, ...],
    *,
    model_required: bool,
) -> dict[str, Any]:
    blocks = [
        {
            "block_id": f"{pathway.lower()}.section.{index:02d}",
            "slot_id": f"section.{index:02d}",
            "kind": "NARRATIVE",
            "title": section,
            "required": True,
            "order": index,
        }
        for index, section in enumerate(sections, start=1)
    ]
    blocks.append(
        {
            "block_id": f"{pathway.lower()}.evidence-register",
            "slot_id": "appendix.evidence-register",
            "kind": "EVIDENCE_REGISTER",
            "title": "Evidence Register",
            "required": True,
            "order": len(blocks) + 1,
        }
    )
    optional_blocks = [dict(policy) for policy in OPTIONAL_BLOCKS]
    return {
        "template_id": f"caos.{pathway.lower().replace('_', '-')}.v1",
        "template_version": TEMPLATE_VERSION,
        "pathway": pathway,
        "title": title,
        "model_requirement": "REQUIRED" if model_required else "OPTIONAL",
        "allowed_appendices": [policy["kind"] for policy in optional_blocks],
        "optional_blocks": optional_blocks,
        "blocks": blocks,
    }


DELIVERABLE_TEMPLATES = {
    "FULL_CREDIT": _template(
        "FULL_CREDIT",
        "Investment Committee Credit Memo",
        (
            "Credit Snapshot",
            "Recommendation",
            "Thesis and Variant View",
            "Business and Industry",
            "Capital Structure",
            "Base and Downside Model",
            "Liquidity and Covenants",
            "Risks, Catalysts, and Falsifiers",
            "Monitoring",
        ),
        model_required=True,
    ),
    "EARNINGS_UPDATE": _template(
        "EARNINGS_UPDATE",
        "Earnings Update",
        (
            "Credit Snapshot",
            "What Changed",
            "Reported Versus Prior Bridge",
            "Model Impact",
            "Leverage and Liquidity",
            "Thesis and Recommendation Impact",
            "Risks, Catalysts, and Monitoring",
        ),
        model_required=True,
    ),
    "COVENANT_REFINANCING": _template(
        "COVENANT_REFINANCING",
        "Covenant and Refinancing Brief",
        (
            "Credit Snapshot",
            "Capital Structure and Maturity Wall",
            "Covenant Definitions and Headroom",
            "Liquidity",
            "Refinancing Options",
            "Base and Downside Breakpoints",
            "Actions and Monitoring",
        ),
        model_required=True,
    ),
    "RELATIVE_VALUE": _template(
        "RELATIVE_VALUE",
        "Relative Value Note",
        (
            "Credit Snapshot",
            "Instrument Comparison",
            "Structure and Seniority",
            "Relative Compensation",
            "Catalysts and Risks",
            "Recommendation and Trade Gates",
            "Market Freshness",
        ),
        model_required=False,
    ),
    "DISTRESSED_RESTRUCTURING": _template(
        "DISTRESSED_RESTRUCTURING",
        "Scenario and Recovery Pack",
        (
            "Credit Snapshot",
            "Capital Structure and Priority",
            "Liquidity Runway",
            "Base, Downside, and Scenario Exhibits",
            "Recovery",
            "Covenant, Default, and Refinancing Milestones",
            "Catalysts and Process Risks",
            "Recommendation",
        ),
        model_required=True,
    ),
    "DEEP_RESEARCH": _template(
        "DEEP_RESEARCH",
        "Evidence-Bound Research Memorandum",
        (
            "Research Question and Scope",
            "Executive Findings",
            "Evidence Synthesis",
            "Counterevidence and Gaps",
            "Implications for Thesis, Model, and Recommendation",
            "Unresolved Questions",
        ),
        model_required=False,
    ),
}


def template_for(pathway: str) -> dict[str, Any]:
    try:
        return DELIVERABLE_TEMPLATES[pathway]
    except KeyError as exc:
        raise ValueError("DELIVERABLE_PATHWAY_INVALID") from exc
