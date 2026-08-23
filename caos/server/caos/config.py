from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _strict_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    if value == "true":
        return True
    if value == "false":
        return False
    raise ValueError(f"{name} must be true or false")


def _bounded_csv(name: str) -> tuple[str, ...]:
    values = tuple(dict.fromkeys(part.strip() for part in os.getenv(name, "").split(",") if part.strip()))
    if len(values) > 100 or any(len(value) > 200 for value in values):
        raise ValueError(f"{name} exceeds its bounded allowlist")
    return values


@dataclass(frozen=True)
class Settings:
    environment: str = "development"
    database_url: str = ""
    storage_dir: Path = Path("/tmp/caos-vault")
    edge_proxy_secret: str = "dev-edge-secret"
    session_secret: str = "dev-insecure-session-secret"
    port: int = 8000
    max_upload_bytes: int = 250 * 1024 * 1024
    clamav_host: str = ""
    clamav_port: int = 3310
    deploy_v_root: Path = Path(__file__).parent / "methodology" / "vendor" / "deploy_v"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-6"
    anthropic_timeout_seconds: float = 150.0
    cpdr_agent_enabled: bool = False
    cpdr_pilot_case_ids: tuple[str, ...] = ()
    cpdr_pilot_subjects: tuple[str, ...] = ()

    @classmethod
    def from_env(cls) -> "Settings":
        port = int(os.getenv("PORT", "8000"))
        max_upload_mb = int(os.getenv("MAX_UPLOAD_MB", "250"))
        clamav_port = int(os.getenv("CLAMAV_PORT", "3310"))
        if not 0 <= port <= 65535:
            raise ValueError("PORT must be between 0 and 65535")
        if max_upload_mb <= 0:
            raise ValueError("MAX_UPLOAD_MB must be greater than 0")
        if not 1 <= clamav_port <= 65535:
            raise ValueError("CLAMAV_PORT must be between 1 and 65535")
        return cls(
            environment=os.getenv("ENVIRONMENT", "development"),
            database_url=os.getenv("DATABASE_URL", ""),
            storage_dir=Path(os.getenv("CAOS_STORAGE_DIR", "/tmp/caos-vault")),
            edge_proxy_secret=os.getenv("EDGE_PROXY_SECRET", "dev-edge-secret"),
            session_secret=os.getenv("SESSION_SECRET", "dev-insecure-session-secret"),
            port=port,
            max_upload_bytes=max_upload_mb * 1024 * 1024,
            clamav_host=os.getenv("CLAMAV_HOST", ""),
            clamav_port=clamav_port,
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
            anthropic_model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6"),
            cpdr_agent_enabled=_strict_bool("CPDR_AGENT_ENABLED", False),
            cpdr_pilot_case_ids=_bounded_csv("CPDR_PILOT_CASE_IDS"),
            cpdr_pilot_subjects=_bounded_csv("CPDR_PILOT_SUBJECTS"),
        )

    def validate_runtime(self) -> None:
        if self.environment == "production":
            if not self.database_url.startswith(("postgresql://", "postgresql+psycopg://")):
                raise RuntimeError("production requires a PostgreSQL DATABASE_URL")
            if self.edge_proxy_secret == "dev-edge-secret":
                raise RuntimeError("production requires EDGE_PROXY_SECRET")
            if self.session_secret == "dev-insecure-session-secret":
                raise RuntimeError("production requires SESSION_SECRET")
