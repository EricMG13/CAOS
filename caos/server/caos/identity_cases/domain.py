from __future__ import annotations

from dataclasses import dataclass

from fastapi import HTTPException, Request

from ..config import Settings
from ..ledgers import RunLedger


@dataclass(frozen=True)
class Identity:
    subject: str
    email: str
    role: str
    groups: tuple[str, ...] = ()


def _role_from_groups(groups: tuple[str, ...]) -> str:
    normalized = {group.strip().lower() for group in groups}
    for group, role in (
        ("caos-admin", "ADMIN"),
        ("caos-approver", "APPROVER"),
        ("caos-analyst", "ANALYST"),
        ("caos-reader", "READER"),
    ):
        if group in normalized:
            return role
    return "READER"


def identity_from_request(request: Request, settings: Settings) -> Identity:
    if (
        settings.environment == "production"
        and request.headers.get("x-edge-authorization") != settings.edge_proxy_secret
    ):
        raise HTTPException(status_code=401, detail="trusted edge identity required")
    subject = request.headers.get("x-forwarded-user") or request.headers.get(
        "x-forwarded-email"
    )
    email = request.headers.get("x-forwarded-email") or subject
    groups = tuple(
        filter(None, (request.headers.get("x-forwarded-groups") or "").split(","))
    )
    role = (
        _role_from_groups(groups)
        if settings.environment == "production"
        else request.headers.get("x-caos-role", "ANALYST").upper()
    )
    if settings.environment == "production" and not subject:
        raise HTTPException(status_code=401, detail="OIDC identity required")
    if not subject:
        subject, email = "local-analyst", "analyst@local"
    if role not in {"ANALYST", "APPROVER", "ADMIN", "READER"}:
        raise HTTPException(status_code=403, detail="unknown role")
    return Identity(subject=subject, email=email, role=role, groups=groups)


def require_case(
    runs: RunLedger, case_id: str, identity: Identity, write: bool = False
) -> dict:
    case = runs.get_case(case_id)
    if not case or not runs.is_member(case_id, identity.subject):
        raise HTTPException(status_code=404, detail="case not found")
    writer_roles = {"ANALYST", "APPROVER", "ADMIN"}
    if write and (
        identity.role not in writer_roles
        or not runs.is_member(case_id, identity.subject, roles=writer_roles)
    ):
        raise HTTPException(status_code=403, detail="analyst authority required")
    return case


def require_role(identity: Identity, *roles: str) -> None:
    if identity.role not in set(roles):
        raise HTTPException(status_code=403, detail="insufficient role")
