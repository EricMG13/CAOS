from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


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
    anthropic_model: str = "claude-sonnet-4-6"

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            environment=os.getenv("ENVIRONMENT", "development"),
            database_url=os.getenv("DATABASE_URL", ""),
            storage_dir=Path(os.getenv("CAOS_STORAGE_DIR", "/tmp/caos-vault")),
            edge_proxy_secret=os.getenv("EDGE_PROXY_SECRET", "dev-edge-secret"),
            session_secret=os.getenv("SESSION_SECRET", "dev-insecure-session-secret"),
            port=int(os.getenv("PORT", "8000")),
            max_upload_bytes=int(os.getenv("MAX_UPLOAD_MB", "250")) * 1024 * 1024,
            clamav_host=os.getenv("CLAMAV_HOST", ""),
            clamav_port=int(os.getenv("CLAMAV_PORT", "3310")),
            anthropic_model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6"),
        )

    def validate_runtime(self) -> None:
        if self.environment == "production":
            if not self.database_url.startswith(("postgresql://", "postgresql+psycopg://")):
                raise RuntimeError("production requires a PostgreSQL DATABASE_URL")
            if self.edge_proxy_secret == "dev-edge-secret":
                raise RuntimeError("production requires EDGE_PROXY_SECRET")
            if self.session_secret == "dev-insecure-session-secret":
                raise RuntimeError("production requires SESSION_SECRET")
