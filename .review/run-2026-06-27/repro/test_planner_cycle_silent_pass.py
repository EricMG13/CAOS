"""Repro for planner-cycle-silent-pass (planner.py:244).

Claim: a dependency cycle in the module registry is silently routed as Full Run
and executed in a dependency-violating order, instead of being Blocked. The
code comment at planner.py:242-244 says cycle nodes "never execute", but
build_route_plan still runs them through _verdict and they end up in
execution_order with readiness='Full Run' and blocking_reason=None.
"""

import os
import sys

# Engine imports.
sys.path.insert(0, "/Users/ericguei/Claude/Projects/Credit Operating System/caos/server")

# Offline determinism.
os.environ.pop("ANTHROPIC_API_KEY", None)
os.environ.pop("GEMINI_API_KEY", None)

from engine.registry import ModuleSpec
from engine.planner import build_route_plan, FULL_RUN, BLOCKED
from engine.schemas import ModulePayload


def _cp0():
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


def test_cycle_nodes_silently_full_run_and_misordered():
    # A and B form a 2-cycle: A depends_on B, B depends_on A.
    specs = [
        ModuleSpec("CP-0", "SourceReadiness", "L0", "source_readiness_assessment",
                   implemented=True),
        ModuleSpec("A", "Amod", "L1", "obj_a", depends_on=("B",), implemented=True),
        ModuleSpec("B", "Bmod", "L1", "obj_b", depends_on=("A",), implemented=True),
    ]

    plan = build_route_plan(_cp0(), specs)

    by_id = {r.module_id: r for r in plan.readiness}

    # 1) Both cycle nodes are routed as FULL_RUN with NO blocking reason.
    assert by_id["A"].readiness == FULL_RUN, by_id["A"].readiness
    assert by_id["B"].readiness == FULL_RUN, by_id["B"].readiness
    assert by_id["A"].blocking_reason is None
    assert by_id["B"].blocking_reason is None

    # 2) Neither is Blocked despite the cycle.
    assert by_id["A"].readiness != BLOCKED
    assert by_id["B"].readiness != BLOCKED

    # 3) Both land in execution_order — they DO execute, contradicting the
    #    "never executes" comment.
    assert "A" in plan.execution_order
    assert "B" in plan.execution_order

    # 4) The order violates the dependency: A is scheduled before B even though
    #    A depends_on B, so at runtime upstream.get("B") would be None for A.
    ia, ib = plan.execution_order.index("A"), plan.execution_order.index("B")
    assert ia < ib, plan.execution_order  # A (needs B) runs first -> dep violated

    print("execution_order:", plan.execution_order)
    print("readiness:", [(r.module_id, r.readiness, r.blocking_reason)
                         for r in plan.readiness])
