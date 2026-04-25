from __future__ import annotations

from ..engine.events import log_event
from ..schema.home_schema import canonical_node_type, canonical_semantic_type
from .npc_runtime import minute_of_day


WEEKDAY_NAMES = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
WEEKDAY_NAMES_CN = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
SEASON_NAMES = ["spring", "summer", "autumn", "winter"]
SEASON_NAMES_CN = ["春", "夏", "秋", "冬"]

WEATHER_PRESETS: dict[str, dict[str, float]] = {
    "sunny": {"base": 27.0, "swing": 5.5},
    "cloudy": {"base": 23.0, "swing": 3.0},
    "rainy": {"base": 20.0, "swing": 2.0},
    "foggy": {"base": 18.0, "swing": 1.5},
    "windy": {"base": 19.0, "swing": 4.5},
    "stormy": {"base": 17.0, "swing": 3.0},
    "snowy": {"base": 1.0, "swing": 2.5},
    "cold_wave": {"base": 8.0, "swing": 3.5},
    "heatwave": {"base": 33.0, "swing": 4.0},
}

SEASONAL_WEATHER_CYCLE: dict[str, list[str]] = {
    "spring": ["sunny", "cloudy", "rainy", "foggy", "sunny", "windy"],
    "summer": ["sunny", "heatwave", "cloudy", "rainy", "stormy", "sunny"],
    "autumn": ["sunny", "windy", "cloudy", "foggy", "sunny", "rainy"],
    "winter": ["cloudy", "snowy", "cold_wave", "sunny", "foggy", "windy"],
}


def weekday_index(day: int) -> int:
    return max(0, (int(day) - 1) % 7)


def weekday_name(day: int) -> str:
    return WEEKDAY_NAMES[weekday_index(day)]


def weekday_name_cn(day: int) -> str:
    return WEEKDAY_NAMES_CN[weekday_index(day)]


def season_index(day: int) -> int:
    return max(0, ((int(day) - 1) // 21) % 4)


def season_name(day: int) -> str:
    return SEASON_NAMES[season_index(day)]


def season_name_cn(day: int) -> str:
    return SEASON_NAMES_CN[season_index(day)]


def infer_weather(day: int, season: str) -> str:
    cycle = SEASONAL_WEATHER_CYCLE.get(season) or SEASONAL_WEATHER_CYCLE["spring"]
    cycle_index = max(0, (int(day) * 3 + season_index(day)) % len(cycle))
    return cycle[cycle_index]


def collapse_stage(entropy: float) -> str:
    if entropy >= 1.0:
        return "collapsed"
    if entropy >= 0.72:
        return "critical"
    if entropy >= 0.45:
        return "strained"
    if entropy >= 0.2:
        return "aging"
    return "stable"


def infer_day_phase(minute: int) -> str:
    if 300 <= minute < 420:
        return "dawn"
    if 420 <= minute < 1080:
        return "day"
    if 1080 <= minute < 1200:
        return "dusk"
    return "night"


def outdoor_temperature_c(weather: str, minute: int) -> float:
    preset = WEATHER_PRESETS.get(weather, WEATHER_PRESETS["sunny"])
    if 300 <= minute < 480:
        factor = -0.6
    elif 480 <= minute < 720:
        factor = 0.15
    elif 720 <= minute < 960:
        factor = 0.85
    elif 960 <= minute < 1200:
        factor = 0.2
    else:
        factor = -0.9
    return round(preset["base"] + preset["swing"] * factor, 2)


def ensure_world_environment(world_state: dict) -> dict:
    world_state.setdefault("day", 1)
    world_state.setdefault("time_min", 360)
    world_state.setdefault("minutes_per_step", 10)
    day = int(world_state.get("day") or 1)
    minute = int(world_state.get("time_min") or 0) % (24 * 60)
    current_season = season_name(day)
    auto_weather = infer_weather(day, current_season)
    world_state.setdefault("weather_mode", "auto")
    if str(world_state.get("weather_mode") or "auto") == "manual":
        world_state.setdefault("weather", "sunny")
    else:
        world_state["weather"] = str(world_state.get("weather") or auto_weather)
    world_state.setdefault("entropy", 0.0)
    world_state["weekday_index"] = weekday_index(day)
    world_state["weekday_name"] = weekday_name(day)
    world_state["weekday_name_cn"] = weekday_name_cn(day)
    world_state["week_index"] = ((day - 1) // 7) + 1
    world_state["season_index"] = season_index(day)
    world_state["season_name"] = current_season
    world_state["season_name_cn"] = season_name_cn(day)
    world_state["day_of_season"] = ((day - 1) % 21) + 1
    world_state["season_week"] = (((day - 1) % 21) // 7) + 1
    world_state["is_workday"] = world_state["weekday_name"] in {"monday", "tuesday", "wednesday", "thursday", "friday"}
    minute = int(world_state.get("time_min") or 0) % (24 * 60)
    world_state["day_phase"] = infer_day_phase(minute)
    world_state["is_daytime"] = world_state["day_phase"] in {"dawn", "day", "dusk"}
    world_state["outdoor_temperature"] = outdoor_temperature_c(str(world_state["weather"]), minute)
    world_state["collapse_stage"] = collapse_stage(float(world_state.get("entropy") or 0.0))
    return world_state


def _room_nodes(state: dict) -> list[dict]:
    return [
        node
        for node in (state.get("nodes") or {}).values()
        if canonical_node_type(node) == "room"
    ]


def _room_hvac_nodes(state: dict, room_id: str) -> list[dict]:
    return [
        node
        for node_id, node in (state.get("nodes") or {}).items()
        if state.get("room_of", {}).get(node_id) == room_id and canonical_semantic_type(node) == "air_conditioner"
    ]


def apply_environment_step(state: dict, step: int) -> None:
    world = ensure_world_environment(state.setdefault("world_state", {}))
    minute = minute_of_day(world, step)
    world["clock_minute"] = minute
    world["day_phase"] = infer_day_phase(minute)
    world["is_daytime"] = world["day_phase"] in {"dawn", "day", "dusk"}
    world["outdoor_temperature"] = outdoor_temperature_c(str(world.get("weather") or "sunny"), minute)

    active_issue_count = 0
    for node in (state.get("nodes") or {}).values():
        node_states = node.get("states") or {}
        semantic = canonical_semantic_type(node)
        if bool(node_states.get("is_dirty", False)):
            active_issue_count += 1
        if bool(node_states.get("is_rotten", False)):
            active_issue_count += 1
        if bool(node_states.get("is_open", False)) and semantic in {"door", "window", "microwave", "washer", "dishwasher"}:
            active_issue_count += 1
        if bool(node_states.get("is_on", False)) and semantic in {"stove", "faucet", "washer", "dishwasher", "microwave"}:
            active_issue_count += 1
        if float(node_states.get("fill_level", 0.0)) >= 0.75:
            active_issue_count += 1
        if "cleanliness" in node_states and float(node_states.get("cleanliness", 1.0)) < 0.5:
            active_issue_count += 1
        if bool(node_states.get("is_wilted", False)):
            active_issue_count += 1

    weather = str(world.get("weather") or "sunny")
    season = str(world.get("season_name") or "spring")
    weather_pressure = {
        "sunny": 0.00010,
        "cloudy": 0.00016,
        "rainy": 0.00032,
        "foggy": 0.00028,
        "windy": 0.00022,
        "stormy": 0.00040,
        "snowy": 0.00030,
        "cold_wave": 0.00026,
        "heatwave": 0.00036,
    }.get(weather, 0.00018)
    season_pressure = {"spring": 0.00010, "summer": 0.00022, "autumn": 0.00014, "winter": 0.00018}.get(season, 0.00012)
    entropy_gain = 0.0008 + weather_pressure + season_pressure + min(0.004, active_issue_count * 0.00025)
    entropy = min(1.25, round(float(world.get("entropy") or 0.0) + entropy_gain, 6))
    world["entropy"] = entropy
    world["collapse_stage"] = collapse_stage(entropy)

    for room in _room_nodes(state):
        room_id = str(room.get("id") or "")
        states = room.setdefault("states", {})
        current = float(states.get("temperature", 24.0))
        outdoor = float(world["outdoor_temperature"])
        temperature = current + (outdoor - current) * 0.08

        active_hvac = False
        for hvac in _room_hvac_nodes(state, room_id):
            hvac_states = hvac.setdefault("states", {})
            if not bool(hvac_states.get("is_on", False)):
                continue
            active_hvac = True
            target = float(hvac_states.get("target_temperature", 24.0))
            fan_level = max(1.0, float(hvac_states.get("fan_level", 2)))
            temperature += (target - temperature) * min(0.55, 0.18 + 0.08 * fan_level)

        next_temp = round(temperature, 2)
        prev_temp = float(states.get("temperature", 24.0))
        states["temperature"] = next_temp
        room_cleanliness = max(0.0, float(states.get("cleanliness", 0.96)) - (0.0003 + entropy_gain * 0.08))
        states["cleanliness"] = round(room_cleanliness, 4)
        states["is_dirty"] = room_cleanliness <= 0.45
        if active_hvac and abs(next_temp - prev_temp) >= 0.3:
            log_event(state, step, "room_temperature_changed", f"{room_id} temperature adjusted to {next_temp}C")

    for node_id, node in (state.get("nodes") or {}).items():
        if canonical_node_type(node) != "agent":
            continue
        states = node.setdefault("states", {})
        current_mood = float(states.get("mood", 1.0))
        activity = str(states.get("current_activity") or "")
        recovery = 0.0008 if activity == "sleeping" else 0.0
        next_mood = max(0.0, min(1.0, current_mood - (0.0005 + entropy_gain * 0.05) + recovery))
        states["mood"] = round(next_mood, 4)
        if next_mood <= 0.25:
            log_event(state, step, "npc_mood_drop", f"{node_id} mood dropped to {next_mood:.2f} during {world['collapse_stage']}")
