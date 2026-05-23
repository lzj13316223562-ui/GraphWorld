from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ReplayStepRead(BaseModel):
    run_id: str
    step_index: int
    actor_type: str
    actor_id: str = ""
    observation: dict[str, Any] = Field(default_factory=dict)
    candidate_actions: list[dict[str, Any]] = Field(default_factory=list)
    selected_action: dict[str, Any] = Field(default_factory=dict)
    action_result: dict[str, Any] = Field(default_factory=dict)
    world_state_before: dict[str, Any] = Field(default_factory=dict)
    world_state_after: dict[str, Any] = Field(default_factory=dict)
    events: list[dict[str, Any]] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None


class ReplayResponse(BaseModel):
    run_id: str
    steps: list[ReplayStepRead] = Field(default_factory=list)
    summary: dict[str, Any] = Field(default_factory=dict)
