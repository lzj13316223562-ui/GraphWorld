from __future__ import annotations

import copy

from ..schema.home_schema import canonical_node_type, normalize_home_scene
from ..world.environment import apply_environment_step, ensure_world_environment
from ..world.npc_runtime import apply_npc_routines
from ..world.rules import apply_runtime_rules
from .state import build_runtime_state


def _dynamic_edges(state: dict) -> list[dict]:
    edges = []
    nodes = state['nodes']
    for node_id, parent_id in state['parent_of'].items():
        if parent_id == 'outside_home':
            continue
        if node_id not in nodes or parent_id not in nodes:
            continue
        node = nodes[node_id]
        parent = nodes[parent_id]
        relation = ((node.get('runtime') or {}).get('relation')) or 'in'
        parent_type = canonical_node_type(parent)
        if parent_type == 'room' and relation not in {'held_by', 'worn_by'}:
            relation = 'in'
        category = 'containment'
        edge_type = 'containment_edge'
        if relation in {'inside_room', 'part_of'}:
            category = 'structural'
            edge_type = 'structural_edge'
        edges.append({'source_id': parent_id, 'target_id': node_id, 'edge_type': edge_type, 'relation': relation, 'category': category, 'properties': {'runtime': True}})
    return edges


def simulate_scene_with_state(raw_scene: dict, start_step: int = 0, runtime_state: dict | None = None) -> tuple[dict, dict]:
    raw = normalize_home_scene(copy.deepcopy(raw_scene))
    step_count = int((raw.get('world_state') or {}).get('step') or 0)
    ensure_world_environment(raw.setdefault('world_state', {}))
    state = copy.deepcopy(runtime_state) if runtime_state is not None else build_runtime_state(raw)
    ensure_world_environment(state.setdefault('world_state', {}))
    state['scene_name'] = raw.get('scene_name') or state.get('scene_name') or ''
    base_time_min = int((raw.get('world_state') or {}).get('time_min') or state['world_state'].get('time_min') or 0)
    base_day = int((raw.get('world_state') or {}).get('day') or state['world_state'].get('day') or 1)
    minutes_per_step = max(1, int((raw.get('world_state') or {}).get('minutes_per_step') or state['world_state'].get('minutes_per_step') or 10))
    initial_step = max(0, int(start_step))
    if step_count < initial_step:
        initial_step = 0
    for step in range(initial_step, step_count + 1):
        absolute_time = base_time_min + step * minutes_per_step
        state['world_state']['day'] = base_day + (absolute_time // (24 * 60))
        state['world_state']['time_min'] = absolute_time % (24 * 60)
        state['world_state']['minutes_per_step'] = minutes_per_step
        ensure_world_environment(state['world_state'])
        apply_npc_routines(state, step)
        apply_runtime_rules(state, step)
        apply_environment_step(state, step)
    state.setdefault('world_state', {})
    state['world_state']['step'] = step_count
    raw['nodes'] = list(state['nodes'].values())
    raw['edges'] = state['structural_edges'] + state['control_edges'] + _dynamic_edges(state)
    raw.setdefault('world_state', {})
    raw['world_state'].update(copy.deepcopy(state.get('world_state') or {}))
    raw['world_state']['event_log'] = state['logs'][-16:]
    resident_id = 'human_resident' if 'human_resident' in state['nodes'] else next(iter([nid for nid, node in state['nodes'].items() if canonical_node_type(node) == 'agent']), '')
    raw['agent'] = {'id': resident_id, 'current_room': state['room_of'].get(resident_id, ''), 'inventory': []}
    return raw, state


def simulate_scene(raw_scene: dict, start_step: int = 0, runtime_state: dict | None = None) -> dict:
    raw, _ = simulate_scene_with_state(raw_scene, start_step=start_step, runtime_state=runtime_state)
    return raw
