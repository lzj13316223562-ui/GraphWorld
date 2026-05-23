from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from backend.app.schemas.action import ActionResult, CandidateAction
from backend.app.schemas.observation import Observation


class ControlMode(str, Enum):
    agent = "agent"
    human = "human"
    npc_only = "npc_only"
    hybrid = "hybrid"


class VisibilityMode(str, Enum):
    full = "full"
    room = "room"
    fog_of_war = "fog_of_war"


class RunStatus(str, Enum):
    pending = "pending"
    running = "running"
    waiting_for_human = "waiting_for_human"
    completed = "completed"
    failed = "failed"
    canceled = "canceled"


class RunCreate(BaseModel):
    scene_version_id: str
    control_mode: ControlMode
    visibility_mode: VisibilityMode = VisibilityMode.fog_of_war
    task_id: str = "maintain_order"
    agent_model: str | None = None
    max_steps: int = 1600
    seed: int | None = None
    config: dict[str, Any] = Field(default_factory=dict)


class RunRead(BaseModel):
    id: str
    scene_version_id: str
    control_mode: ControlMode
    visibility_mode: VisibilityMode
    status: RunStatus
    current_step: int = 0
    config: dict[str, Any] = Field(default_factory=dict)
    summary: dict[str, Any] = Field(default_factory=dict)
    artifact_uri: str = ""
    error_message: str = ""
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime | None = None


class RunCurrentResponse(BaseModel):
    run: RunRead
    observation: Observation | None = None
    candidate_actions: list[CandidateAction] = Field(default_factory=list)
    latest_action_result: ActionResult | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)
