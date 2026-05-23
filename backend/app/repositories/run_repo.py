from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.db.models import Run, RunStep


class RunRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, run: Run) -> Run:
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run

    def get(self, run_id: str) -> Run | None:
        return self.db.get(Run, run_id)

    def list(self) -> list[Run]:
        statement = select(Run).order_by(Run.created_at.desc(), Run.id.asc())
        return list(self.db.scalars(statement).all())

    def steps(self, run_id: str, *, offset: int = 0, limit: int | None = None) -> list[RunStep]:
        statement = select(RunStep).where(RunStep.run_id == run_id).order_by(RunStep.step_index.asc()).offset(max(0, offset))
        if limit is not None:
            statement = statement.limit(max(1, min(limit, 500)))
        return list(self.db.scalars(statement).all())

    def step(self, run_id: str, step_index: int) -> RunStep | None:
        statement = select(RunStep).where(RunStep.run_id == run_id, RunStep.step_index == step_index)
        return self.db.scalar(statement)

    def add_step(self, step: RunStep) -> RunStep:
        self.db.add(step)
        self.db.flush()
        self.db.refresh(step)
        return step

    def commit(self) -> None:
        self.db.commit()
