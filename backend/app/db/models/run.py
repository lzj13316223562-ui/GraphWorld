from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.models.base import Base, TimestampMixin
from backend.app.db.models.types import JSONBType


class Run(TimestampMixin, Base):
    __tablename__ = "runs"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    scene_version_id: Mapped[str] = mapped_column(ForeignKey("scene_versions.id"), index=True, nullable=False)
    control_mode: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    visibility_mode: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    current_step: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    config: Mapped[dict] = mapped_column(JSONBType, default=dict, nullable=False)
    summary: Mapped[dict] = mapped_column(JSONBType, default=dict, nullable=False)
    artifact_uri: Mapped[str] = mapped_column(Text, default="", nullable=False)
    error_message: Mapped[str] = mapped_column(Text, default="", nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    steps: Mapped[list["RunStep"]] = relationship(back_populates="run", cascade="all, delete-orphan")


class RunStep(TimestampMixin, Base):
    __tablename__ = "run_steps"
    __table_args__ = (UniqueConstraint("run_id", "step_index", name="uq_run_steps_run_step"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"), index=True, nullable=False)
    step_index: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    actor_type: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    actor_id: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    observation: Mapped[dict] = mapped_column(JSONBType, default=dict, nullable=False)
    candidate_actions: Mapped[list] = mapped_column(JSONBType, default=list, nullable=False)
    selected_action: Mapped[dict] = mapped_column(JSONBType, default=dict, nullable=False)
    action_result: Mapped[dict] = mapped_column(JSONBType, default=dict, nullable=False)
    world_state_before: Mapped[dict] = mapped_column(JSONBType, default=dict, nullable=False)
    world_state_after: Mapped[dict] = mapped_column(JSONBType, default=dict, nullable=False)
    events: Mapped[list] = mapped_column(JSONBType, default=list, nullable=False)
    metrics: Mapped[dict] = mapped_column(JSONBType, default=dict, nullable=False)

    run: Mapped[Run] = relationship(back_populates="steps")
