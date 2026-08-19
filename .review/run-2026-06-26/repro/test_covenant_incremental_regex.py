"""Repro: covenants.derive_covenant_terms grabs the FIRST '$N million' in the
chunk as the incremental capacity, even when an unrelated dollar figure precedes
the actual incremental basket. Deterministic (keyless) path only.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "caos", "server"))

from engine.covenants import derive_covenant_terms  # noqa: E402


def test_incremental_binds_to_clause_after_fix():
    # ORIGINALLY proved the defect (returned 5.0, the fee). After the fix the amount
    # binds to the incremental clause → 250.0, the real basket.
    text = ("The Borrower paid $5 million in arrangement fees. The agreement "
            "provides incremental capacity in the form of an incurrence basket "
            "of up to $250 million of additional term loans.")
    terms = derive_covenant_terms([("c1", text)])
    assert terms is not None
    assert terms["incremental_musd"][0] == 250.0  # was 5.0 before review run-2026-06-26 #1
