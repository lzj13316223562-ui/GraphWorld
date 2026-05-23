from __future__ import annotations

from backend.app.db.session import SessionLocal
from backend.app.services.run_service import RunService
from backend.app.schemas.run import RunRead


def run_agent_job(run_id: str) -> dict:
    with SessionLocal() as db:
        result: RunRead = RunService(db).run_to_completion(run_id)
        return result.model_dump(mode="json")
