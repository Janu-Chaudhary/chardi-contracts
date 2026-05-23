"""Environment-backed configuration for workers and database access."""

from __future__ import annotations

import os


def _env(name: str, default: str | None = None, required: bool = False) -> str:
    value = os.environ.get(name, default)
    if required and not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value or ""


DATABASE_URL: str = _env("DATABASE_URL", required=True)
SAM_GOV_API_KEY: str = _env("SAM_GOV_API_KEY", required=True)
SAM_GOV_BASE_URL: str = _env(
    "SAM_GOV_BASE_URL",
    default="https://api.sam.gov/prod/opportunities/v2/search",
)
USER_AGENT: str = _env(
    "USER_AGENT",
    default="Janu-Chaudhary-ChardiAI-Trial/1.0",
)
REQUEST_TIMEOUT_SECONDS: float = float(_env("REQUEST_TIMEOUT_SECONDS", default="60"))
