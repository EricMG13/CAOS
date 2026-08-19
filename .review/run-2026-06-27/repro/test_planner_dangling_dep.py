"""Repro for planner-dangling-dep-unflagged.

Claim: a module declaring depends_on a module id that does NOT exist in the
registry is routed Full Run, with no Blocked verdict and no limitation flag.
The dangling reference is silently swallowed.

We assert the WRONG (current) behaviour to prove the validator gap: ideally a
dangling dep would surface as Blocked or a limitation. Today it routes clean.
"""
from __future__ import annotations

import sys

sys.path.insert(0, "/Users/ericguei/Claude/Projects/Credit Operating System/caos/server")

from engine.planner import FULL_RUN, build_route_plan  # noqa: E402
from engine.registry import ModuleSpec  # noqa: E402
from engine.schemas import ModulePayload  # noqa: E402


def _cp0() -> ModulePayload:
    return ModulePayload(
        module_id="CP-0",
        module_name="SourceReadiness",
        owned_object="source_readiness_assessment",
        runtime_output={
            "categories_present": ["financials"],
            "edgar_available": True,
            "files_classified": 3,
        },
        confidence="High",
    )


def test_dangling_dep_is_silently_swallowed():
    specs = [
        ModuleSpec("CP-0", "SourceReadiness", "L0", "source_readiness_assessment",
                   implemented=True),
        ModuleSpec("CP-1", "Canon", "L1", "canonical_financials",
                   depends_on=("CP-0",), implemented=True),
        # CP-9 declares a dep on a module id that does not exist in the registry.
        ModuleSpec("CP-9", "Niner", "L3", "niner_obj",
                   depends_on=("CP-1", "CP-DOESNOTEXIST"), implemented=True),
    ]
    plan = build_route_plan(_cp0(), specs)

    # WRONG (current) behaviour: CP-9 routes to execution as Full Run, with no
    # block and no limitation flag, despite referencing a non-existent module.
    assert plan.verdict("CP-9") == FULL_RUN, plan.verdict("CP-9")
    assert "CP-9" in plan.execution_order, plan.execution_order
    assert plan.blocking_reason("CP-9") is None, plan.blocking_reason("CP-9")

    cp9 = next(r for r in plan.readiness if r.module_id == "CP-9")
    assert cp9.limitation_flags == [], cp9.limitation_flags

    # The dangling id never appears anywhere in the plan — fully swallowed.
    all_ids = {r.module_id for r in plan.readiness}
    assert "CP-DOESNOTEXIST" not in all_ids

    print("verdict(CP-9)        =", plan.verdict("CP-9"))
    print("blocking_reason(CP-9)=", plan.blocking_reason("CP-9"))
    print("limitation_flags     =", cp9.limitation_flags)
    print("execution_order      =", plan.execution_order)
    print("CP-9 declared deps   =", cp9.depends_on)
