from __future__ import annotations

import copy

from ..schema.home_schema import canonical_node_type, normalize_home_scene, scene_edges, scene_nodes
from ..world.npc_runtime import ensure_default_npcs


def _is_dynamic_relation(relation: str, category: str) -> bool:
    if category == 'control':
        return False
    return relation in {'contains', 'inside_room', 'in', 'on', 'held_by', 'worn_by', 'at', 'near', 'part_of'}


def _room_for(node_by_id: dict, parent_of: dict[str, str], node_id: str) -> str:
    current = node_id
    seen: set[str] = set()
    while current and current not in seen:
        seen.add(current)
        node = node_by_id.get(current) or {}
        if canonical_node_type(node) == 'room':
            return current
        current = parent_of.get(current, '')
    return ''


def connected_rooms_for_door_node(node: dict) -> list[str]:
    runtime = node.get('runtime') or {}
    raw_rooms = runtime.get('connected_rooms') or node.get('connected_rooms') or []
    if not isinstance(raw_rooms, list):
        return []
    rooms: list[str] = []
    for room_id in raw_rooms:
        value = str(room_id or '')
        if value and value not in rooms:
            rooms.append(value)
    return rooms


def is_room_door_node(node: dict) -> bool:
    return canonical_node_type(node) != 'room' and str(node.get('semantic_type') or '').lower() == 'door' and bool(connected_rooms_for_door_node(node))


def _adjacent_room_map(edges: list[dict]) -> dict[str, list[str]]:
    adjacent: dict[str, list[str]] = {}
    for edge in edges:
        relation = str(edge.get('relation') or '').lower()
        category = str(edge.get('category') or '').lower()
        if relation != 'adjacent_to' or category != 'structural':
            continue
        source = str(edge.get('source_id') or '')
        target = str(edge.get('target_id') or '')
        if not source or not target:
            continue
        adjacent.setdefault(source, [])
        adjacent.setdefault(target, [])
        if target not in adjacent[source]:
            adjacent[source].append(target)
        if source not in adjacent[target]:
            adjacent[target].append(source)
    return adjacent


def _doorway_targets(room_node: dict, node_by_id: dict[str, dict]) -> list[str]:
    layout = room_node.get('layout') or {}
    targets: list[str] = []
    for doorway in layout.get('doorways') or []:
        if not isinstance(doorway, dict):
            continue
        target = str(doorway.get('to') or doorway.get('target_room') or '')
        if target and target in node_by_id and canonical_node_type(node_by_id[target]) == 'room' and target not in targets:
            targets.append(target)
    return targets


def _attach_door_to_adjacent_edges(structural_edges: list[dict], room_a: str, room_targets: list[str], door_id: str) -> None:
    target_set = set(room_targets)
    for edge in structural_edges:
        relation = str(edge.get('relation') or '').lower()
        if relation != 'adjacent_to':
            continue
        source = str(edge.get('source_id') or '')
        target = str(edge.get('target_id') or '')
        if room_a not in {source, target}:
            continue
        other = target if source == room_a else source
        if target_set and other not in target_set:
            continue
        properties = edge.setdefault('properties', {})
        door_ids = properties.setdefault('door_ids', [])
        if door_id not in door_ids:
            door_ids.append(door_id)
        if len(door_ids) == 1:
            properties['door_id'] = door_id


def _adjacent_edge_door_ids(edge: dict) -> list[str]:
    properties = edge.get('properties') or {}
    door_ids: list[str] = []
    primary = str(properties.get('door_id') or '')
    if primary:
        door_ids.append(primary)
    for door_id in properties.get('door_ids') or []:
        value = str(door_id or '')
        if value and value not in door_ids:
            door_ids.append(value)
    return door_ids


def _match_room_doors_to_adjacent_edges(structural_edges: list[dict]) -> tuple[dict[str, dict], dict[int, str]]:
    candidate_edge_ids_by_door: dict[str, list[int]] = {}
    edge_by_index: dict[int, dict] = {}
    for index, edge in enumerate(structural_edges):
        if str(edge.get('relation') or '').lower() != 'adjacent_to':
            continue
        edge_by_index[index] = edge
        for door_id in _adjacent_edge_door_ids(edge):
            candidate_edge_ids_by_door.setdefault(door_id, []).append(index)

    matched_door_by_edge: dict[int, str] = {}

    def assign_door(door_id: str, visited: set[int]) -> bool:
        for edge_index in candidate_edge_ids_by_door.get(door_id, []):
            if edge_index in visited:
                continue
            visited.add(edge_index)
            current = matched_door_by_edge.get(edge_index)
            if not current or assign_door(current, visited):
                matched_door_by_edge[edge_index] = door_id
                return True
        return False

    for door_id in sorted(candidate_edge_ids_by_door, key=lambda item: (len(candidate_edge_ids_by_door[item]), item)):
        assign_door(door_id, set())

    assigned_edge_by_door: dict[str, dict] = {}
    for edge_index, door_id in matched_door_by_edge.items():
        edge = edge_by_index.get(edge_index)
        if edge:
            assigned_edge_by_door[door_id] = edge
    return assigned_edge_by_door, matched_door_by_edge


def build_runtime_state(raw: dict) -> dict:
    normalized = normalize_home_scene(raw)
    nodes = [copy.deepcopy(node) for node in scene_nodes(normalized)]
    edges = [copy.deepcopy(edge) for edge in scene_edges(normalized)]
    node_by_id = {str(node['id']): node for node in nodes if node.get('id')}
    adjacent_rooms = _adjacent_room_map(edges)
    parent_of: dict[str, str] = {}
    room_of: dict[str, str] = {}
    structural_edges = []
    control_edges = []

    for edge in edges:
        source = str(edge.get('source_id') or '')
        target = str(edge.get('target_id') or '')
        relation = str(edge.get('relation') or '').lower()
        category = str(edge.get('category') or '').lower()
        
        # 1. 获取源节点和目标节点的信息
        source_node = node_by_id.get(source) or {}
        target_node = node_by_id.get(target) or {}
        
        target_semantic = str(target_node.get('semantic_type') or '').lower()
        source_type = canonical_node_type(source_node) # 获取父节点类型

        if category == 'control' or relation == 'controls':
            control_edges.append(edge)
            continue

        if target_semantic == 'door' and source_type == 'room':
            doorway_targets = _doorway_targets(source_node, node_by_id)
            connected_rooms = [source]
            fallback_targets = doorway_targets or adjacent_rooms.get(source, [])
            for room_id in fallback_targets:
                if room_id not in connected_rooms:
                    connected_rooms.append(room_id)
            target_runtime = copy.deepcopy(target_node.get('runtime') or {})
            target_runtime['connected_rooms'] = connected_rooms
            if len(connected_rooms) > 1:
                target_runtime['doorway_to'] = connected_rooms[1]
            target_runtime['door_anchor_room'] = source
            target_node['runtime'] = target_runtime
            target_node['parent'] = None
        elif target_semantic == 'door' and source and target:
            target_runtime = copy.deepcopy(target_node.get('runtime') or {})
            target_runtime['relation'] = 'in'
            target_node['runtime'] = target_runtime
            parent_of[target] = source
        elif relation in {'adjacent_to', 'contains', 'inside_room', 'part_of'} and category == 'structural':
            structural_edges.append(edge)
            # Keep structural containment edges as hierarchy anchors so room reachability
            # can be derived for fixed objects and their children.
            if relation in {'contains', 'inside_room', 'part_of'} and source and target:
                parent_of[target] = source

        elif source and target and _is_dynamic_relation(relation, category):
            # 2. 如果是“设备门”（如微波炉门），它的父节点是 Object
            # 它会进入这里，保持原有的包含关系（棕色虚线）
            parent_of[target] = source

    for node_id, node in node_by_id.items():
        if not is_room_door_node(node):
            continue
        connected_rooms = connected_rooms_for_door_node(node)
        if connected_rooms:
            room_of[node_id] = connected_rooms[0]
            _attach_door_to_adjacent_edges(structural_edges, connected_rooms[0], connected_rooms[1:], node_id)

    assigned_edge_by_door, matched_door_by_edge = _match_room_doors_to_adjacent_edges(structural_edges)
    room_door_edges: list[dict] = []
    for index, edge in enumerate(structural_edges):
        if str(edge.get('relation') or '').lower() != 'adjacent_to':
            continue
        properties = edge.setdefault('properties', {})
        matched_door = matched_door_by_edge.get(index)
        if matched_door:
            properties['door_id'] = matched_door
            properties['door_ids'] = [matched_door]
        else:
            properties.pop('door_id', None)
            properties.pop('door_ids', None)

    for node_id, node in node_by_id.items():
        if not is_room_door_node(node):
            continue
        edge = assigned_edge_by_door.get(node_id)
        if not edge:
            continue
        source = str(edge.get('source_id') or '')
        target = str(edge.get('target_id') or '')
        if not source or not target:
            continue
        runtime = copy.deepcopy(node.get('runtime') or {})
        anchor_room = str(runtime.get('door_anchor_room') or '')
        if anchor_room not in {source, target}:
            anchor_room = source
        other_room = target if anchor_room == source else source
        runtime['connected_rooms'] = [anchor_room, other_room]
        runtime['doorway_to'] = other_room
        runtime['door_anchor_room'] = anchor_room
        node['runtime'] = runtime
        room_of[node_id] = anchor_room
        for room_id in (anchor_room, other_room):
            room_door_edges.append(
                {
                    'source_id': room_id,
                    'target_id': node_id,
                    'edge_type': 'structural_edge',
                    'relation': 'room_door',
                    'category': 'structural',
                    'properties': {'runtime': True},
                }
            )

    structural_edges.extend(room_door_edges)

    for node_id in list(node_by_id):
        if node_id in room_of:
            continue
        room = _room_for(node_by_id, parent_of, node_id)
        if room:
            room_of[node_id] = room

    state = {
        'nodes': node_by_id,
        'parent_of': parent_of,
        'room_of': room_of,
        'structural_edges': structural_edges,
        'control_edges': control_edges,
        'world_state': copy.deepcopy(normalized.get('world_state') or {}),
        'logs': [],
        'human': {'id': 'human_resident', 'current_state': 'sleeping'},
        'scene_name': normalized.get('scene_name') or '',
    }
    state['world_state'].setdefault('scene_name', normalized.get('scene_name') or '')

    ensure_default_npcs(state)
    node_by_id = state['nodes']
    parent_of = state['parent_of']
    room_of = state['room_of']
    for node_id, parent_id in parent_of.items():
        if node_id in node_by_id:
            node_by_id[node_id]['parent'] = parent_id
    for node_id, node in node_by_id.items():
        node.setdefault('child', [])
    for parent_id in list(node_by_id):
        node_by_id[parent_id]['child'] = []
    for child_id, parent_id in parent_of.items():
        if parent_id in node_by_id:
            node_by_id[parent_id].setdefault('child', []).append(child_id)
    for node in node_by_id.values():
        node['child'] = sorted(set(node.get('child') or []))

    return state
