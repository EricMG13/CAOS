"""Repro for finding `nlquery-dead-missing-value-caveat`.

Claim: the caveat at nlquery.py:429
    if any(m["value"] is None for r in results for m in r["metrics"].values()):
        caveats.append("Some issuers are missing values for a displayed metric.")
is DEAD CODE. Every m["value"] is MetricFact.value (nullable=False Float), so it
is never None for a persisted row. When an issuer is *genuinely* missing a
displayed (non-rank) metric, that shows up as an ABSENT KEY in `metrics`
(line 379 filters `if key in spec.metrics` over only the facts that exist), not
as a None value — so the `any(... is None ...)` branch can never fire and the
intended "missing values" warning is silently never surfaced.

This test sets up exactly that scenario with REAL MetricFact rows and the REAL
`execute()` and asserts the WRONG (current) behaviour: the caveat is absent even
though issuer B has no value for the displayed `ebitda_margin` metric.
"""

import os
import sys

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Offline determinism: no model keys.
os.environ.pop("ANTHROPIC_API_KEY", None)
os.environ.pop("GEMINI_API_KEY", None)
# In-memory SQLite so we never touch the user's DB.
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

sys.path.insert(0, "/Users/ericguei/Claude/Projects/Credit Operating System/caos/server")

from database import Base, Issuer, MetricFact  # noqa: E402
import nlquery  # noqa: E402
from nlquery import QuerySpec, execute, validate_spec  # noqa: E402


@pytest.mark.asyncio
async def test_missing_displayed_metric_never_triggers_caveat():
    # Single shared in-memory engine for the whole test.
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with Session() as session:
        a = Issuer(id="iss-a", name="Alpha Corp", ticker="ALP", industry="Energy", country="US")
        b = Issuer(id="iss-b", name="Bravo Corp", ticker="BRV", industry="Energy", country="US")
        session.add_all([a, b])

        # Both issuers have a value for the RANK metric (net_leverage)...
        session.add(MetricFact(issuer_id="iss-a", metric_key="net_leverage", period="LTM",
                               value=4.0, headline=True, provenance="seed", basis="adjusted"))
        session.add(MetricFact(issuer_id="iss-b", metric_key="net_leverage", period="LTM",
                               value=6.0, headline=True, provenance="seed", basis="adjusted"))
        # ...but only issuer A has a value for the DISPLAYED-only metric (ebitda_margin).
        # Issuer B is GENUINELY MISSING ebitda_margin entirely — no row at all.
        session.add(MetricFact(issuer_id="iss-a", metric_key="ebitda_margin", period="LTM",
                               value=22.0, headline=True, provenance="seed"))
        await session.commit()

        spec = validate_spec(QuerySpec(
            metrics=["net_leverage", "ebitda_margin"],
            rank_by="net_leverage",
            direction="desc",
            limit=10,
        ))
        result = await execute(session, spec)

    await engine.dispose()

    rows = result["rows"]
    caveats = result["caveats"]

    # Sanity: both issuers came back, ranked on net_leverage.
    assert len(rows) == 2, rows
    by_id = {r["issuer"]["id"]: r for r in rows}

    # Issuer B is genuinely missing the displayed ebitda_margin metric: it shows up
    # as an ABSENT KEY in `metrics`, not as a {"value": None}. This is the crux.
    assert "ebitda_margin" not in by_id["iss-b"]["metrics"], \
        "expected the missing metric to be an absent key, not a None-valued entry"
    assert "ebitda_margin" in by_id["iss-a"]["metrics"]

    # Every present value is a real float — confirming the line-429 predicate
    # `m['value'] is None` is never satisfiable for any persisted MetricFact.
    assert all(
        isinstance(m["value"], (int, float)) and m["value"] is not None
        for r in rows for m in r["metrics"].values()
    )

    # THE DEFECT: despite issuer B genuinely lacking a value for a displayed metric,
    # the intended "missing values" caveat is NEVER produced. The line-429 branch is
    # dead. We assert the WRONG current behaviour to prove it.
    missing_caveat = "Some issuers are missing values for a displayed metric."
    assert missing_caveat not in caveats, (
        "If this assertion FAILS, the caveat now fires and the finding is wrong. "
        f"caveats={caveats}"
    )

    print("\n--- REPRO OUTPUT ---")
    print("issuer B metrics keys:", sorted(by_id["iss-b"]["metrics"].keys()))
    print("issuer A metrics keys:", sorted(by_id["iss-a"]["metrics"].keys()))
    print("caveats produced     :", caveats)
    print("dead 'missing values' caveat present?:", missing_caveat in caveats)
    print("--- END ---")
