from __future__ import annotations

import json
from typing import Any

from backend.tools.agent import llm_query, vlm_query


ALLOWED_ACTIONS = ("move", "pick", "place", "press", "scan", "open", "close", "brush")
ALLOWED_FOCUS = ("explore", "intervene", "support", "recover", "verify")
ACTION_EFFECTS = {
    "move": "Move the robot to a reachable adjacent room or nearby target node.",
    "pick": "Detach a movable object from its current parent and attach it to the robot hand.",
    "place": "Detach a held object from the robot and attach it on or in the placement target.",
    "press": "Trigger a control-like object such as a button, knob, faucet, or appliance control, often changing controlled states.",
    "scan": "Read the target's current states, affordances, local neighborhood, and some control relations without directly changing the world.",
    "open": "Open an openable object such as a door, drawer, cabinet, or appliance door.",
    "close": "Close an openable object such as a door, drawer, cabinet, or appliance door.",
    "brush": "Clean a dirty reachable object or surface and reduce dirt-related penalties.",
}


def _direct_action_system_prompt() -> str:
    return (
        "Choose exactly one legal next action for a service robot. "
        "The input already contains the robot's current believed world state as current_state_graph. "
        "Use current_focus as the current task focus. "
        "Default to acting directly from current_state_graph; do not treat scan as a default prerequisite. "
        "Use scan only when important local state is still missing or when verification is truly needed after acting. "
        "If there is a clear issue and a matching executable action exists, prefer the direct action over scan. "
        "For open door issues prefer close. "
        "If validation_error is present, correct the previous illegal action using an exact entry from action_candidates. "
        "Use action_candidates as the source of truth. "
        "Output a very short current_goal under 8 words. "
        "Return strict JSON only with this schema: "
        '{"reasoning":"short reason","current_goal":"very short task text","action":{"action_type":"move|pick|place|press|scan|open|close|brush","target_id":"node id or room id","object_id":"node id when needed","placement_target_id":"node id when needed for place"}}. '
        "For place, set object_id and placement_target_id. For other actions, target_id is enough. No extra text."
    )


def _extract_json_block(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        return stripped
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start >= 0 and end > start:
        return stripped[start : end + 1]
    raise ValueError("planner response does not contain a JSON object")


def _normalize_action_list(raw: Any) -> list[str]:
    if not isinstance(raw, list):
        return []
    normalized: list[str] = []
    for item in raw:
        action = str(item or "").strip().lower()
        if action in ALLOWED_ACTIONS and action not in normalized:
            normalized.append(action)
    return normalized[:6]


def _normalize_id_list(raw: Any) -> list[str]:
    if not isinstance(raw, list):
        return []
    normalized: list[str] = []
    for item in raw:
        node_id = str(item or "").strip()
        if node_id and node_id not in normalized:
            normalized.append(node_id)
    return normalized[:8]


def _compact_goal_text(text: str, *, fallback: str = "") -> str:
    raw = " ".join(str(text or "").strip().split())
    if not raw:
        return fallback
    lowered = raw.lower()
    sentence = raw
    for sep in (". ", "; ", " However", " Since", " This action", " This step", " Previous", " previous"):
        idx = sentence.find(sep)
        if idx > 0:
            sentence = sentence[:idx].strip(" .;,:")
            break
    short = sentence.strip(" .;,:")
    if len(short) > 96:
        short = short[:96].rsplit(" ", 1)[0].strip(" .;,:")
    if not short:
        short = fallback or raw[:96].strip(" .;,:")
    if short.lower().startswith("the robot is currently"):
        if "explor" in lowered and "kitchen" in lowered:
            return "explore kitchen"
        if "explor" in lowered and "living_room" in lowered:
            return "explore living_room"
        if "press" in lowered and "button_kitchen" in lowered:
            return "press button_kitchen"
    return short or fallback


def parse_direct_action(raw_text: str) -> dict[str, Any]:
    payload = json.loads(_extract_json_block(raw_text))
    reasoning = str(payload.get("reasoning") or "").strip()
    current_goal = _compact_goal_text(str(payload.get("current_goal") or "").strip(), fallback="")
    action = payload.get("action") or {}
    if not isinstance(action, dict):
        raise ValueError("planner action must be an object")

    action_type = str(action.get("action_type") or action.get("action") or "").strip().lower()
    if action_type not in ALLOWED_ACTIONS:
        raise ValueError(f"unsupported action_type: {action_type}")

    target_id = str(action.get("target_id") or action.get("target") or "").strip()
    object_id = str(action.get("object_id") or action.get("object") or "").strip()
    placement_target_id = str(action.get("placement_target_id") or "").strip()

    if action_type == "place":
        if not object_id:
            raise ValueError("place action requires object_id")
        if not placement_target_id and not target_id:
            raise ValueError("place action requires placement_target_id")
    elif not target_id:
        raise ValueError(f"{action_type} action requires target_id")

    return {
        "reasoning": reasoning,
        "current_goal": current_goal,
        "action": action_type,
        "target": placement_target_id or target_id,
        "object": object_id,
        "target_id": target_id,
        "object_id": object_id,
        "placement_target_id": placement_target_id or target_id,
    }


def default_high_level_plan(packet: dict[str, Any]) -> dict[str, Any]:
    local_issue_objects = list(packet.get("local_issue_objects") or [])
    active_goal = packet.get("active_goal") or {}
    previous_goal_review = packet.get("previous_goal_review") or {}
    if active_goal and not bool(active_goal.get("completed")):
        intent = _compact_goal_text(
            str(active_goal.get("goal_text") or "").strip(),
            fallback="continue current goal",
        )
        focus = "support"
    elif local_issue_objects:
        issue = local_issue_objects[0]
        issue_tags = list(issue.get("issue_tags") or [])
        target_id = str(issue.get("id") or "")
        tag = issue_tags[0] if issue_tags else "issue"
        intent = _compact_goal_text(f"handle {tag} on {target_id}", fallback="resolve a clear local problem")
        focus = "intervene"
    elif previous_goal_review and not bool(previous_goal_review.get("goal_completed")):
        intent = _compact_goal_text(
            str(previous_goal_review.get("next_goal") or "").strip(),
            fallback="continue previous useful goal",
        )
        focus = str(previous_goal_review.get("recommended_focus") or "support")
    else:
        intent = "explore a nearby room"
        focus = "explore"
    return {
        "reasoning": "deterministic fallback intent",
        "focus": focus,
        "intent": intent,
        "target_ids": [],
        "preferred_action_types": [],
        "avoid_action_types": [],
        "success_criteria": "",
        "raw_response": "",
        "source": "fallback",
    }


def default_direct_action(packet: dict[str, Any]) -> dict[str, Any]:
    action_candidates = list(packet.get("action_candidates") or [])
    if not action_candidates:
        return {
            "error": "no legal actions available",
            "raw_response": "",
            "reasoning": "",
        }
    selected = action_candidates[0]
    action_type = str(selected.get("action_type") or "")
    target_id = str(selected.get("target_id") or "")
    object_id = str(selected.get("object_id") or "")
    placement_target_id = str(selected.get("placement_target_id") or "")
    return {
        "reasoning": "deterministic fallback action",
        "current_goal": _compact_goal_text(
            str(((packet.get("active_goal") or {}).get("goal_text") or "")).strip(),
            fallback="take legal action",
        ),
        "action": action_type,
        "target": placement_target_id or target_id,
        "object": object_id,
        "target_id": target_id,
        "object_id": object_id,
        "placement_target_id": placement_target_id,
        "raw_response": "",
        "source": "fallback",
    }


def query_direct_action(
    packet: dict[str, Any],
    *,
    agent_model: str,
    timeout: int,
    enable_search: bool,
    image_path: str | None,
) -> dict[str, Any]:
    user_query = json.dumps(packet, ensure_ascii=False, separators=(",", ":"))
    if image_path:
        raw = vlm_query(
            system_prompt=_direct_action_system_prompt(),
            image_path=image_path,
            user_query=user_query,
            agent=agent_model,
            enable_search=enable_search,
        )
    else:
        raw = llm_query(
            system_prompt=_direct_action_system_prompt(),
            user_query=user_query,
            agent=agent_model,
            timeout=timeout,
            enable_search=enable_search,
        )
    try:
        parsed = parse_direct_action(raw)
    except ValueError as exc:
        return {
            "error": str(exc),
            "raw_response": raw,
            "reasoning": "",
        }
    parsed["raw_response"] = raw
    parsed["source"] = "llm_direct_action"
    return parsed


__all__ = [
    "ACTION_EFFECTS",
    "ALLOWED_ACTIONS",
    "ALLOWED_FOCUS",
    "default_high_level_plan",
    "default_direct_action",
    "parse_direct_action",
    "query_direct_action",
]
