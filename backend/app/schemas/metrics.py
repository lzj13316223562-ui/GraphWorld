from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class MetricPoint(BaseModel):
    step_index: int | None = None
    metric_name: str
    metric_value: float | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class RunMetricsResponse(BaseModel):
    run_id: str
    metrics: list[MetricPoint] = Field(default_factory=list)
    summary: dict[str, Any] = Field(default_factory=dict)
