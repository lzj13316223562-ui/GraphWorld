from __future__ import annotations

from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.models.base import Base, TimestampMixin
from backend.app.db.models.types import JSONBType


class Metric(TimestampMixin, Base):
    __tablename__ = "metrics"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"), index=True, nullable=False)
    step_index: Mapped[int | None] = mapped_column(Integer, index=True)
    metric_name: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    metric_value: Mapped[float | None] = mapped_column(Float)
    metric_payload: Mapped[dict] = mapped_column(JSONBType, default=dict, nullable=False)
