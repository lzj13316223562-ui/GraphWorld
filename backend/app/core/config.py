from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import os


def _csv_env(name: str, default: str = "") -> tuple[str, ...]:
    raw = os.getenv(name, default)
    return tuple(item.strip() for item in raw.split(",") if item.strip())


@dataclass(frozen=True)
class Settings:
    app_name: str
    app_version: str
    environment: str
    api_prefix: str
    database_url: str
    redis_url: str
    artifact_root: str
    cors_origins: tuple[str, ...]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        app_name=os.getenv("GRAPHWORLD_APP_NAME", "GraphWorld Web API"),
        app_version=os.getenv("GRAPHWORLD_APP_VERSION", "0.1.0"),
        environment=os.getenv("GRAPHWORLD_ENV", "development"),
        api_prefix=os.getenv("GRAPHWORLD_API_PREFIX", "/api"),
        database_url=os.getenv(
            "GRAPHWORLD_DATABASE_URL",
            "postgresql+psycopg://graphworld:graphworld@localhost:5432/graphworld",
        ),
        redis_url=os.getenv("GRAPHWORLD_REDIS_URL", "redis://localhost:6379/0"),
        artifact_root=os.getenv("GRAPHWORLD_ARTIFACT_ROOT", "backend/data/web_artifacts"),
        cors_origins=_csv_env("GRAPHWORLD_CORS_ORIGINS", "http://localhost:5173"),
    )
