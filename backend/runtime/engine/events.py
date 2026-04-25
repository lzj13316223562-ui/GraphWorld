from __future__ import annotations


def log_event(state: dict, step: int, event_type: str, detail: str) -> None:
    state['logs'].append({'step': step, 'type': event_type, 'detail': detail})


def set_node_state(state: dict, node_id: str, **updates) -> None:
    node = state['nodes'].get(node_id)
    if not node:
        return
    node.setdefault('states', {}).update(updates)


def move_item(state: dict, item_id: str, parent_id: str, relation: str) -> None:
    state['parent_of'][item_id] = parent_id
    if parent_id == 'outside_home':
        state['room_of'][item_id] = 'outside_home'
    else:
        parent = state['nodes'].get(parent_id, {})
        
        # ✅ 修复：将 parent.get('type') 改为 parent.get('node_type') or parent.get('type')
        parent_type = str(parent.get('node_type') or parent.get('type') or '').lower()
        
        if parent_type == 'room':
            state['room_of'][item_id] = parent_id
        elif parent_id in state['room_of']:
            state['room_of'][item_id] = state['room_of'][parent_id]
    node = state['nodes'].get(item_id)
    if node is not None:
        node['parent'] = parent_id
        node.setdefault('runtime', {})
        node['runtime']['relation'] = relation


def move_actor(state: dict, actor_id: str, parent_id: str, room_id: str, activity: str) -> None:
    move_item(state, actor_id, parent_id, 'at' if parent_id == room_id else 'in')
    actor = state['nodes'].get(actor_id, {}).setdefault('states', {})
    actor['current_activity'] = activity
    actor['is_home'] = room_id != 'outside_home'
