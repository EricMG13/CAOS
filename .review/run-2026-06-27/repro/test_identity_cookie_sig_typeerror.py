"""Repro for: identity.read_session_token raises an uncaught TypeError when the
cookie signature segment contains a non-ASCII byte.

Critic claim (identity-cookie-sig-typeerror-500): line 88
    if not hmac.compare_digest(sig, _sig(raw, secret)):
compares two `str` values. `sig` derives from the raw cookie value (Starlette
decodes cookies latin-1, so a 0xFF byte survives as a non-ASCII char). Python's
hmac.compare_digest refuses to compare strings containing non-ASCII chars and
raises TypeError. read_session_token only wraps token.rsplit('.',1) in a
try/except (ValueError), so the TypeError on the very next line is uncaught and
propagates. The sibling compares at identity.py:145-147 and main.py:201-203
deliberately .encode(...) to dodge exactly this — line 88 omits the guard.

A correctly-defensive read_session_token would return None (token ignored,
fall-through to proxy/local identity), NOT raise.

Run:
    cd ".../caos" && PYTHONPATH=server server/.venv/bin/python \
        -m pytest ../.review/run-2026-06-27/repro/test_identity_cookie_sig_typeerror.py -q
"""
import os
import sys

# Import the REAL module under test.
SERVER = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "caos", "server"
)
sys.path.insert(0, os.path.abspath(SERVER))

import identity  # noqa: E402


def test_unit_read_session_token_raises_on_non_ascii_sig():
    """Direct call: a token whose signature segment has a high byte should be
    rejected (return None), but the current code raises TypeError instead."""
    secret = "some-secret"
    # rsplit('.', 1) -> raw='abc.def', sig='ghi\xff'  (sig is the part after the
    # LAST dot; the 0xFF byte is what a latin-1-decoded cookie delivers).
    token = "abc.def.ghi\xff"

    # Demonstrate the WRONG behaviour: an exception escapes instead of a clean None.
    raised = None
    try:
        result = identity.read_session_token(token, secret)
    except TypeError as exc:  # current (buggy) behaviour
        raised = exc

    assert raised is not None, (
        "expected the defect: read_session_token raised instead of returning None"
    )
    assert "non-ASCII" in str(raised), f"unexpected error text: {raised!r}"
    print(f"\nCONFIRMED defect: read_session_token raised TypeError: {raised}")


def test_endtoend_get_identity_propagates_typeerror():
    """End-to-end: get_identity (the FastAPI dependency every /api route uses) has
    no try around read_session_token, so the same TypeError escapes the dependency
    — which the global handler turns into a 500, not a clean 401/fall-through.

    We drive get_identity with a minimal fake Request carrying the malicious
    cookie, in a NON-deployed context (settings.environment != production, no edge
    secret) so the edge-origin check is skipped and execution reaches the cookie
    branch. The DB is never touched because the TypeError fires before the lookup.
    """
    import asyncio

    # Force a non-deployed local context so the edge guard is a no-op and we hit
    # the cookie branch. get_settings() reads the environment lazily.
    os.environ.pop("DATABRICKS_APP_PORT", None)
    os.environ["ENVIRONMENT"] = "development"
    os.environ.setdefault("SESSION_SECRET", "test-secret-for-repro")
    # Bust any cached settings so the env override takes effect.
    try:
        from config import get_settings
        get_settings.cache_clear()  # lru_cache
    except Exception:
        pass

    class FakeRequest:
        # The high 0xFF byte arrives in the cookie value exactly as Starlette's
        # latin-1 cookie_parser would deliver it (verified separately).
        cookies = {identity.COOKIE_NAME: "abc.def\xff"}
        headers: dict = {}

        # identity.get_identity only reads .cookies and .headers (via .get).
        class _Headers(dict):
            def get(self, k, default=None):
                return super().get(k, default)

        headers = _Headers()

    class FakeDB:
        async def get(self, *a, **k):  # never reached — TypeError fires first
            return None

    raised = None
    try:
        asyncio.run(identity.get_identity(FakeRequest(), FakeDB()))
    except TypeError as exc:
        raised = exc

    assert raised is not None, (
        "expected get_identity to propagate the TypeError (→ 500), but it did not"
    )
    assert "non-ASCII" in str(raised), f"unexpected error text: {raised!r}"
    print(
        f"\nCONFIRMED end-to-end: get_identity propagated TypeError "
        f"(global handler -> HTTP 500): {raised}"
    )
