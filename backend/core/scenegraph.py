"""
场景容器
使用新的OOP模型手动创建场景图
"""
import networkx as nx
from typing import Dict, List, Any, Optional, Union

from .nodes import Object, Room, Floor, Agent, MobileTool, NodeType
from .edges import (
    ObjectEdge, RoomEdge, ObjectRoomEdge, RoomFloorEdge, TransportEdge, 
    SpatialRelation, EdgeType, EdgeCategory, create_edge, BaseEdge
)
from .object_library import get_object_template


class SceneGraph:
    """
    场景图容器
    管理所有节点和边，并维护节点内部的一致性
    """
    
    def __init__(self, scene_name: str):
        self.scene_name = scene_name
        self.nodes: Dict[str, Any] = {}
        self.edges: List[Any] = []
        self.agent: Optional[Agent] = None
        self._nx_graph_cache = None 

    # ==========================================
    # 1. 核心底层方法 (Low-Level API)
    # ==========================================
    def add_edge(self, source: str, target: str, relation: SpatialRelation, **kwargs) -> Optional[BaseEdge]:
        """【万能接口】添加边，并自动同步节点内部的列表属性"""
        if source not in self.nodes:
            print(f"⚠️ Warning: Source node '{source}' not found.")
        if target not in self.nodes:
            print(f"⚠️ Warning: Target node '{target}' not found.")

        # 1. 创建并添加边
        new_edge = create_edge(source, target, relation, **kwargs)
        self.edges.append(new_edge)
        
        # 2.更新节点内部的属性列表
        self._update_node_attributes(source, target, relation)
        
        return new_edge


    def _update_node_attributes(self, source_id: str, target_id: str, relation: SpatialRelation):
        """
        根据边的关系，自动更新节点内部的冗余字段
        例如：建立了 CONTAINS 边 -> 更新父节点的 contained_objects 和子节点的 floor_id
        """
        source_node = self.nodes.get(source_id)
        target_node = self.nodes.get(target_id)
        if not source_node or not target_node: return

        # Case A: 房间 -> 包含 -> 楼层 (RoomFloorEdge)
        
        if relation == SpatialRelation.CONTAINS:
            # 1. Floor contains Room (如果是 Floor -> Room)
            if source_node.node_type == NodeType.FLOOR and target_node.node_type == NodeType.ROOM:
                source_node.add_room(target_id) # Floor.rooms.add
                target_node.floor_id = source_id
            
            # 2. Room contains Floor (如果是 Room -> Floor，兼容现有代码)
            elif source_node.node_type == NodeType.ROOM and target_node.node_type == NodeType.FLOOR:
                target_node.add_room(source_id) # Floor.rooms.add
                # room.floor_id 已经在 add_room 时赋值了
                
            # 3. Room contains Object
            elif source_node.node_type == NodeType.ROOM and target_node.node_type == NodeType.OBJECT:
                source_node.add_object(target_id) # Room.contained_objects.add
                
            # 4. Object contains Object (容器)
            elif source_node.node_type == NodeType.OBJECT and target_node.node_type == NodeType.OBJECT:
                # 如果 Object 类有 children 字段可以加，没有就算了
                pass
                
        # Case B: Object -> ONTOP -> Surface
        elif relation == SpatialRelation.ONTOP:
             # 如果 Surface 是 Object (如桌子)，且有 contained_objects
             pass 

        # Case C: Neighbour (双向)
        elif relation == SpatialRelation.NEIGHBOUR:
            if source_node.node_type == NodeType.ROOM and target_node.node_type == NodeType.ROOM:
                source_node.add_neighbour(target_id)
                target_node.add_neighbour(source_id)

    # ==========================================
    # 2. 节点管理方法
    # ==========================================
    def add_floor(self, floor_id: str, name: str = None, **kwargs) -> Floor:
        if name is None: name = floor_id
        floor = Floor(id=floor_id, name=name, node_type=NodeType.FLOOR, **kwargs)
        self.nodes[floor_id] = floor
        return floor
    
    def add_room(self, room_id: str, floor_id: str, name: str = None, **kwargs) -> Room:
        if name is None: name = room_id
        room = Room(id=room_id, name=name, node_type=NodeType.ROOM, floor_id=floor_id, **kwargs)
        self.nodes[room_id] = room
        
        # 建立连接：让 Floor 包含 Room
        if floor_id in self.nodes:
            # 你的旧逻辑是 room -> contains -> floor (不太对劲)，建议改成 floor -> contains -> room
            # 但为了不破坏现有逻辑，我们这里保留原来的方向，但在 _update_node_attributes 里做兼容
            # 或者更好的做法：这里改成 Floor -> Room
            
            # 修正方向：Floor (Source) -> CONTAINS -> Room (Target)
            # 这样更符合直觉
            self.add_edge(source=floor_id, target=room_id, relation=SpatialRelation.CONTAINS, edge_type=EdgeType.ROOM_FLOOR_EDGE)
        
        return room
    
    def add_object(self, obj_id: Union[int, str], object_class: str, name: str = None, **kwargs) -> Object:
        obj_id_str = str(obj_id)
        
        # 1. 获取原始模板并处理列表解包
        raw_template = get_object_template(object_class)
        
        # 如果模板是列表，取出第一个字典元素；如果是字典则直接使用
        if isinstance(raw_template, list) and len(raw_template) > 0:
            template = raw_template[0]
        elif isinstance(raw_template, dict):
            template = raw_template
        else:
            # 兜底处理：防止模板库返回空或其他异常类型
            template = {
                "object_type": "unknown", 
                "affordances": [], 
                "states": {}, 
                "default_states": {}, # 适配 YAML 字段
                "physical_properties": {}
            }

        # 2. 安全地提取属性，优先使用传入的参数 (kwargs)
        # 使用 .get() 代替 [] 索引，防止 Key 不存在时报错
        object_type = kwargs.pop("object_type", template.get("object_type", "unknown"))
        affordances = kwargs.pop("affordances", template.get("affordances", []))
        
        # 3. 核心修复：适配 YAML 中的 default_states
        # 逻辑：优先用参数传的 states -> 其次用模板里的 states -> 最后用模板里的 default_states
        states = kwargs.pop("states", template.get("states", template.get("default_states", {})))
        
        physical_properties = kwargs.pop("physical_properties", template.get("physical_properties", {}))
        
        # 如果 kwargs 中还有额外的 states 增量更新
        if "states" in kwargs: 
            states.update(kwargs.pop("states"))
            
        if name is None: 
            name = obj_id_str
            
        # 4. 创建并存储对象
        obj = Object(
            id=obj_id_str, 
            name=name, 
            node_type=NodeType.OBJECT, 
            object_type=object_type, 
            affordances=affordances, 
            states=states, 
            physical_properties=physical_properties, 
            **kwargs
        )
        self.nodes[obj_id_str] = obj
        return obj
    
    def add_mobile_tool(self, tool_id: str, tool_category: str = "elevator", 
                        initial_location: str = None, name: str = None, 
                        capacity: int = 1, **kwargs) -> MobileTool:
        if name is None: name = f"{tool_category}_{tool_id}"
        states = kwargs.pop("states", {})
        if initial_location: states["current_location"] = initial_location
        physical_props = kwargs.pop("physical_properties", {})
        physical_props["capacity"] = capacity
        
        tool = MobileTool(
            id=tool_id, name=name, node_type=NodeType.MOBILE_TOOL,
            object_type=tool_category, current_location=initial_location if initial_location else "",
            states=states, physical_properties=physical_props, **kwargs
        )
        self.nodes[tool_id] = tool
        return tool
    
    def set_agent(self, agent_id: str, current_room: str, name: str = None, **kwargs) -> Agent:
        if name is None: name = agent_id
        self.agent = Agent(id=agent_id, name=name, node_type=NodeType.AGENT, current_room=current_room, **kwargs)
        self.nodes[agent_id] = self.agent
        return self.agent

    # ==========================================
    # 3. 业务封装连接方法 (High-Level API)
    # ==========================================
    
    def connect_objects(self, obj1_id: str, obj2_id: str, relation: SpatialRelation, **kwargs) -> ObjectEdge:
        return self.add_edge(source=obj1_id, target=obj2_id, relation=relation, **kwargs)
    
    def connect_rooms(self, room1_id: str, room2_id: str, **kwargs) -> RoomEdge:
        return self.add_edge(source=room1_id, target=room2_id, relation=SpatialRelation.NEIGHBOUR, **kwargs)

    def connect_transport_stop(self, station_id: str, tool_id: str, access_type: str):
        """连接站点和交通工具"""
        props = {"connection_type": access_type}
        # 使用 create_edge 无法自动推断 TransportEdge，所以这里暂时手动
        # 或者我们定义 TransportEdge 属于 PHYSICAL
        edge1 = TransportEdge(
            source_id=station_id, target_id=tool_id,
            edge_type=EdgeType.TRANSPORT_EDGE, relation=SpatialRelation.NEIGHBOUR,
            properties=props, category=EdgeCategory.PHYSICAL
        )
        self.edges.append(edge1)
        
        edge2 = TransportEdge(
            source_id=tool_id, target_id=station_id,
            edge_type=EdgeType.TRANSPORT_EDGE, relation=SpatialRelation.NEIGHBOUR,
            properties=props, category=EdgeCategory.PHYSICAL
        )
        self.edges.append(edge2)

    def place_object_in_room(self, obj_id: str, room_id: str, **kwargs) -> ObjectRoomEdge:
        """快捷方式：将物体放置在房间中"""
        # 注意方向：Room -> CONTAINS -> Object
        return self.add_edge(source=room_id, target=obj_id, relation=SpatialRelation.CONTAINS, **kwargs)
    
    def place_object_on_surface(self, item_id: str, receptacle_id: str, **kwargs):
        """快捷方式：建立物体放置关系"""
        edge1 = self.add_edge(source=item_id, target=receptacle_id, relation=SpatialRelation.ONTOP, **kwargs)
        # Receptacle -> Contains -> Item
        self.add_edge(source=receptacle_id, target=item_id, relation=SpatialRelation.CONTAINS, **kwargs)
        return edge1

    # ==========================================
    # 4. 查询与序列化
    # ==========================================
    def get_objects_by_category(self, category: str) -> List[Object]:
        return [n for n in self.nodes.values() if isinstance(n, Object) and getattr(n, 'object_type', '') == category]
    
    def get_node(self, node_id: str) -> Optional[Any]:
        return self.nodes.get(node_id)
    
    def get_rooms_on_floor(self, floor_id: str) -> List[Room]:
        room_ids = {e.source_id for e in self.edges if isinstance(e, RoomFloorEdge) and e.target_id == floor_id}
        return [self.nodes[rid] for rid in room_ids if rid in self.nodes]
    
    def get_objects_in_room(self, room_id: str) -> List[Object]:
        obj_ids = {e.source_id for e in self.edges if isinstance(e, ObjectRoomEdge) and e.target_id == room_id}
        return [self.nodes[oid] for oid in obj_ids if oid in self.nodes]
    
    def get_neighbor_rooms(self, room_id: str) -> List[str]:
        neighbors = set()
        for e in self.edges:
            if isinstance(e, RoomEdge):
                if e.source_id == room_id: neighbors.add(e.target_id)
                elif e.target_id == room_id: neighbors.add(e.source_id)
        return list(neighbors)
    
    def to_dict(self) -> Dict[str, Any]:
        nodes = [node.to_dict() for node in self.nodes.values()]
        edges = [edge.to_dict() for edge in self.edges]
        return {
            "scene_name": self.scene_name,
            "node": {str(node["id"]): node for node in nodes if node.get("id")},
            "edge": {
                str(edge.get("id") or f"edge_{idx:06d}"): edge
                for idx, edge in enumerate(edges)
            },
            "nodes": nodes,
            "edges": edges,
            "agent": self.agent.to_dict() if self.agent else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SceneGraph':
        scene = cls(data["scene_name"])
        for node_data in data["nodes"]:
            n_type = node_data.get("type")
            node = None
            if n_type == NodeType.OBJECT.value: node = Object.from_dict(node_data)
            elif n_type == NodeType.ROOM.value: node = Room.from_dict(node_data)
            elif n_type == NodeType.FLOOR.value: node = Floor.from_dict(node_data)
            elif n_type == NodeType.AGENT.value: 
                node = Agent.from_dict(node_data)
                scene.agent = node
            elif n_type == NodeType.MOBILE_TOOL.value: node = MobileTool.from_dict(node_data)
            if node: scene.nodes[node.id] = node
        
        for edge_data in data["edges"]:
            e_type = edge_data.get("edge_type")
            edge_class = None
            if e_type == EdgeType.OBJECT_EDGE.value: edge_class = ObjectEdge
            elif e_type == EdgeType.ROOM_EDGE.value: edge_class = RoomEdge
            elif e_type == EdgeType.OBJECT_ROOM_EDGE.value: edge_class = ObjectRoomEdge
            elif e_type == EdgeType.ROOM_FLOOR_EDGE.value: edge_class = RoomFloorEdge
            elif e_type == EdgeType.TRANSPORT_EDGE.value: edge_class = TransportEdge
            elif e_type == EdgeType.CONTROL_EDGE.value: edge_class = ObjectEdge
            
            if edge_class:
                edge = edge_class.from_dict(edge_data)
                scene.edges.append(edge)
            else:
                try:
                    edge = ObjectEdge.from_dict(edge_data)
                    scene.edges.append(edge)
                except:
                    print(f"⚠️ Warning: Unknown edge type {e_type}, skipping.")
        return scene
