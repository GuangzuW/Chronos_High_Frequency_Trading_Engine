"""Environment-driven configuration for the API server (12-factor).

    PORT                   listen port (default 8080)
    CHRONOS_DB             SQLite path for persistence (default: in-memory)
    CHRONOS_CORS_ORIGINS   comma-separated allowlist, or "*" (default "*")
    CHRONOS_API_TOKEN      if set, mutating requests require Authorization: Bearer <token>
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class Config:
    port: int = 8080
    db_path: str | None = None
    cors_origins: list[str] = field(default_factory=lambda: ["*"])
    api_token: str | None = None


def load_config() -> Config:
    origins_env = os.environ.get("CHRONOS_CORS_ORIGINS", "*").strip()
    if origins_env in ("", "*"):
        origins = ["*"]
    else:
        origins = [o.strip() for o in origins_env.split(",") if o.strip()]
    return Config(
        port=int(os.environ.get("PORT", "8080")),
        db_path=os.environ.get("CHRONOS_DB") or None,
        cors_origins=origins,
        api_token=os.environ.get("CHRONOS_API_TOKEN") or None,
    )
