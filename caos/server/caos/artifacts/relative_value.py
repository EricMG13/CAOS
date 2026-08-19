from __future__ import annotations

import copy
import math
from datetime import date
from typing import Any

from ..contracts import RVUniverseRequest, SystemSignal, digest
from ..store import MemoryStore, now_iso


def _finite(value: float | None) -> bool:
    return value is None or math.isfinite(value)


def signal_for_spread(spread_bps: float | None) -> SystemSignal | None:
    if spread_bps is None or not math.isfinite(spread_bps):
        return None
    # Metric registry owns the threshold and polarity; sign alone has no credit meaning.
    if spread_bps <= 350:
        return SystemSignal.ATTRACTIVE
    if spread_bps <= 500:
        return SystemSignal.FAIR
    return SystemSignal.UNATTRACTIVE


def _basis(row: dict[str, Any]) -> str:
    for field in ("spread_bps", "yield_bps", "price"):
        if row.get(field) is not None:
            return field
    return "none"


def save_universe(store: MemoryStore, case_id: str, actor: str, request: RVUniverseRequest) -> dict[str, Any]:
    for row in request.rows:
        if not all(_finite(value) for value in (row.price, row.yield_bps, row.spread_bps, row.duration)):
            raise ValueError("non-finite market value")
        try:
            date.fromisoformat(row.observation_date)
            date.fromisoformat(row.maturity)
        except ValueError as exc:
            raise ValueError("invalid market date") from exc
        if row.duration is None and row.spread_bps is not None:
            raise ValueError("duration is required when spread is supplied")
    with store.lock:
        version = (store.rv_universes.get(case_id, {}).get("version", 0) + 1)
        universe = {
            "id": store._id("rv"),
            "case_id": case_id,
            "version": version,
            "source_version": request.source_version,
            "rows": [row.model_dump(mode="json") for row in request.rows],
            "created_by": actor,
            "created_at": now_iso(),
            "digest": digest(request.model_dump(mode="json")),
        }
        store.rv_universes[case_id] = universe
    store.audit_event("rv.universe_versioned", actor, case_id=case_id, version=version)
    return copy.deepcopy(universe)


def compare_universe(store: MemoryStore, case_id: str, accepted_snapshot: dict[str, Any] | None) -> dict[str, Any]:
    universe = copy.deepcopy(store.rv_universes.get(case_id))
    if not universe:
        return {"status": "NO_UNIVERSE", "rows": [], "excluded": []}
    eligible: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    reference_key: tuple[str, str, str, str] | None = None
    for row in universe["rows"]:
        reasons: list[str] = []
        if row.get("duration") is None:
            reasons.append("MISSING_DURATION")
        if row.get("spread_bps") is None and row.get("yield_bps") is None and row.get("price") is None:
            reasons.append("MISSING_PRICE_YIELD_SPREAD")
        if reasons:
            excluded.append({"row": row, "reasons": reasons})
            continue
        comparison_key = (row["observation_date"], row["currency"], row["source_version"], _basis(row))
        if reference_key is None:
            reference_key = comparison_key
        elif comparison_key != reference_key:
            reasons.append("CROSS_COMPARABILITY_GROUP")
        if reasons:
            excluded.append({"row": row, "reasons": reasons})
            continue
        eligible.append({**row, "system_signal": signal_for_spread(row.get("spread_bps")), "recommendation": None})
    return {
        "status": "READY" if eligible else "NO_ELIGIBLE_ROWS",
        "universe_id": universe["id"],
        "universe_version": universe["version"],
        "source_version": universe["source_version"],
        "case_snapshot_id": accepted_snapshot["id"] if accepted_snapshot else None,
        "rows": eligible,
        "excluded": excluded,
        "authority_note": "System signal is separate from the Analyst recommendation matrix.",
    }
