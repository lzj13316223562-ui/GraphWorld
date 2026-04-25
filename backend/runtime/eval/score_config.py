from __future__ import annotations

WORLD_SCORE_WEIGHTS = {
    "safety": 0.40,
    "cleanliness": 0.35,
    "orderliness": 0.25,
}

HUMAN_SCORE_WEIGHTS = {
    "safety": 0.35,
    "comfort": 0.25,
    "convenience": 0.20,
    "mood": 0.20,
}

FINAL_SCORE_WEIGHTS = {
    "current_state": 0.85,
    "trend": 0.15,
}

TREND_WINDOW_STEPS = 10

STRUCTURE_PENALTIES = {
    "misplaced_room": 0.08,
    "misplaced_parent": 0.06,
    "scattered": 0.06,
    "misplaced_near": 0.05,
    "over_capacity": 0.07,
}

STATE_PENALTIES = {
    "dirty": 0.04,
    "rotten": 0.12,
    "low_cleanliness": 0.10,
    "trash_full": 0.08,
    "sink_full": 0.08,
    "open": 0.05,
    "open_low": 0.02,
    "open_medium": 0.05,
    "open_high": 0.10,
    "active_risk": 0.14,
    "fridge_off": 0.12,
}
