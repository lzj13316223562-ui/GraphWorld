import React, { memo, useCallback, useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  BaseEdge,
  Background,
  Controls,
  Handle,
  Panel,
  Position,
  ReactFlow,
  ReactFlowProvider,
  useEdgesState,
  useNodesState,
  useReactFlow,
  useStore,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import "./graphflow.css";

function cn(...values) {
  return values.filter(Boolean).join(" ");
}

const ICON_PATHS = {
  furniture: "M5 9h14M7 9v10M17 9v10M7 19h10",
  appliance: "M7 3h10v18H7zM9 6h6M12 10a4 4 0 1 0 0 8a4 4 0 1 0 0-8z",
  control: "M12 7a5 5 0 1 0 0 10a5 5 0 1 0 0-10zM12 10v4",
  container: "M5 7h14v4H5zM5 13h14v4H5zM12 9h0M12 15h0",
  tool: "M9 6l3-2l3 2l-1 3h-4zM8 9h8v11H8z",
  decoration: "M12 4c2 2 3 4 3 6c0 4-3 7-3 10c0-3-3-6-3-10c0-2 1-4 3-6zM8 14c2-1 6-1 8 0",
  consumable: "M9 4h6M10 4v3M8 7h8l-1 12H9L8 7M12 10v6",
  personal_item: "M8 7h8M9 7V5h6v2M7 9h10v10H7zM10 12h4M10 15h4",
  agent: "M12 5a3 3 0 1 0 0 6a3 3 0 1 0 0-6zM7 20c0-3 2-6 5-6s5 3 5 6",
};

const SEMANTIC_ICON_CATEGORY = {
  furniture: "furniture",
  sofa: "furniture",
  bed: "furniture",
  table: "furniture",
  coffee_table: "furniture",
  desk: "furniture",
  chair: "furniture",
  seat: "furniture",
  shelf: "furniture",
  counter: "furniture",
  drying_rack: "furniture",
  rack: "furniture",
  appliance: "appliance",
  refrigerator: "appliance",
  fridge: "appliance",
  computer: "appliance",
  printer: "appliance",
  water_dispenser: "appliance",
  hand_sanitizer_dispenser: "appliance",
  medicine_fridge: "appliance",
  dispenser: "appliance",
  drinking_fountain: "appliance",
  washer: "appliance",
  washing_machine: "appliance",
  dishwasher: "appliance",
  microwave: "appliance",
  stove: "appliance",
  sink: "appliance",
  faucet: "appliance",
  toilet: "appliance",
  tv: "appliance",
  display: "appliance",
  room_light: "appliance",
  light: "appliance",
  control: "control",
  button: "control",
  knob: "control",
  door: "control",
  container: "container",
  cabinet: "container",
  drawer: "container",
  wardrobe: "container",
  shoe_rack: "container",
  box: "container",
  trash_bin: "container",
  tool: "tool",
  brush: "tool",
  toilet_brush: "tool",
  cloth: "tool",
  broom: "tool",
  watering_can: "tool",
  toothbrush: "tool",
  syringe: "tool",
  medical_cart: "tool",
  iv_bag: "tool",
  saline_bag: "tool",
  wheelchair: "tool",
  cart: "tool",
  decoration: "decoration",
  plant: "decoration",
  potted_plant: "decoration",
  planter: "decoration",
  flowerpot: "decoration",
  vase: "decoration",
  ornament: "decoration",
  decor: "decoration",
  consumable: "consumable",
  milk: "consumable",
  juice: "consumable",
  vegetable: "consumable",
  fruit: "consumable",
  yogurt: "consumable",
  bowl: "consumable",
  cup: "consumable",
  plate: "consumable",
  clothes: "consumable",
  shoes: "consumable",
  book: "consumable",
  medicine: "consumable",
  pill_bottle: "consumable",
  refrigerated_medicine: "consumable",
  infusion_bag: "consumable",
  stationery: "consumable",
  personal_item: "personal_item",
  personal_belonging: "personal_item",
  medical_form: "personal_item",
  prescription_sheet: "personal_item",
  receipt: "personal_item",
  nurse_uniform: "personal_item",
  doctor_coat: "personal_item",
  key: "personal_item",
  wallet: "personal_item",
  phone: "personal_item",
  bag: "personal_item",
  handbag: "personal_item",
  backpack: "personal_item",
  agent: "agent",
  human: "agent",
  robot: "agent",
};

function iconKeyForSemantic(semantic, nodeType = "") {
  if (nodeType === "agent") return "agent";
  return SEMANTIC_ICON_CATEGORY[semantic] || "";
}

function GraphEdge({ id, source, target, sourceX, sourceY, targetX, targetY, style }) {
  const sourceNode = useStore((state) => state.nodeLookup.get(source));
  const targetNode = useStore((state) => state.nodeLookup.get(target));
  const sourceCenterX = sourceNode?.internals?.positionAbsolute?.x != null
    ? sourceNode.internals.positionAbsolute.x + ((sourceNode.measured?.width ?? sourceNode.width ?? 0) / 2)
    : sourceX;
  const sourceCenterY = sourceNode?.internals?.positionAbsolute?.y != null
    ? sourceNode.internals.positionAbsolute.y + ((sourceNode.measured?.height ?? sourceNode.height ?? 0) / 2)
    : sourceY;
  const targetCenterX = targetNode?.internals?.positionAbsolute?.x != null
    ? targetNode.internals.positionAbsolute.x + ((targetNode.measured?.width ?? targetNode.width ?? 0) / 2)
    : targetX;
  const targetCenterY = targetNode?.internals?.positionAbsolute?.y != null
    ? targetNode.internals.positionAbsolute.y + ((targetNode.measured?.height ?? targetNode.height ?? 0) / 2)
    : targetY;
  const path = `M ${sourceCenterX} ${sourceCenterY} L ${targetCenterX} ${targetCenterY}`;
  return <BaseEdge id={id} path={path} style={style} />;
}

const GraphNode = memo(function GraphNode({ data, selected }) {
  const iconPath = data.iconKey ? ICON_PATHS[data.iconKey] : null;
  return (
    <div
      className={cn(
        "gw-node",
        `gw-node--${data.kind || "fixture"}`,
        data.temporalClass ? `gw-node--${data.temporalClass}` : "",
        data.stateClass ? `gw-node--${data.stateClass}` : "",
        selected ? "gw-node--selected" : ""
      )}
      style={{ width: data.width, height: data.height }}
    >
      <div className="gw-node__shape" />
      <Handle className="gw-node__handle gw-node__handle--center" id="target" type="target" position={Position.Top} isConnectable={false} />
      <Handle className="gw-node__handle gw-node__handle--center" id="source" type="source" position={Position.Top} isConnectable={false} />
      {iconPath ? (
        <svg className="gw-node__icon" viewBox="0 0 24 24" aria-hidden="true">
          <path d={iconPath} />
        </svg>
      ) : null}
      {data.labelHidden ? null : <div className="gw-node__label">{data.label}</div>}
    </div>
  );
});

const nodeTypes = {
  graphworld: GraphNode,
};

const edgeTypes = {
  graphworld: GraphEdge,
};

function GraphCanvas({ payload, callbacks }) {
  const reactFlow = useReactFlow();
  const [nodes, setNodes, onNodesChange] = useNodesState(payload.nodes || []);
  const [edges, setEdges, onEdgesChange] = useEdgesState(payload.edges || []);
  const [lastFitKey, setLastFitKey] = useState("");
  const flowKey = `${payload.floorKey || ""}:${payload.fitNonce || 0}`;

  useEffect(() => {
    setNodes(payload.nodes || []);
  }, [payload.nodes, setNodes]);

  useEffect(() => {
    setEdges(payload.edges || []);
  }, [payload.edges, setEdges]);

  useEffect(() => {
    const fitKey = `${payload.floorKey || ""}:${payload.fitNonce || 0}`;
    if (!fitKey || fitKey === lastFitKey) return;
    setLastFitKey(fitKey);
    requestAnimationFrame(() => {
      reactFlow.fitView({ padding: 0.18, duration: 280 });
    });
  }, [payload.fitNonce, payload.floorKey, lastFitKey, reactFlow]);

  const onNodeClick = useCallback(
    (event, node) => {
      callbacks.onNodeClick?.(node.data.rawNode);
    },
    [callbacks]
  );

  const onNodeMouseEnter = useCallback(
    (event, node) => {
      callbacks.onNodeMouseEnter?.(node.data.rawNode, event);
    },
    [callbacks]
  );

  const onNodeMouseMove = useCallback(
    (event, node) => {
      callbacks.onNodeMouseMove?.(node.data.rawNode, event);
    },
    [callbacks]
  );

  const onNodeMouseLeave = useCallback(
    (event, node) => {
      callbacks.onNodeMouseLeave?.(node.data.rawNode, event);
    },
    [callbacks]
  );

  const onNodeDragStop = useCallback(
    (event, node) => {
      callbacks.onNodeDragStop?.(node.id, node.position, node.data.rawNode);
    },
    [callbacks]
  );

  const defaultEdgeOptions = useMemo(
    () => ({
      type: "straight",
      selectable: false,
      focusable: false,
      interactionWidth: 12,
      animated: false,
    }),
    []
  );

  return (
    <div className="graphflow-shell">
      <ReactFlow
        key={flowKey}
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={onNodeClick}
        onNodeMouseEnter={onNodeMouseEnter}
        onNodeMouseMove={onNodeMouseMove}
        onNodeMouseLeave={onNodeMouseLeave}
        onNodeDragStop={onNodeDragStop}
        fitView={false}
        minZoom={0.18}
        maxZoom={2.4}
        panOnDrag={true}
        selectionOnDrag={false}
        selectNodesOnDrag={false}
        nodesDraggable={true}
        nodesConnectable={false}
        elementsSelectable={true}
        proOptions={{ hideAttribution: true }}
        defaultEdgeOptions={defaultEdgeOptions}
      >
        <Background gap={26} size={1} color="rgba(108, 87, 63, 0.10)" />
        <Controls showInteractive={false} position="bottom-right" />
        <Panel position="top-right">
          <div className="graphflow-panel">
            <button
              className="graphflow-panel__button"
              type="button"
              onClick={() => reactFlow.fitView({ padding: 0.18, duration: 240 })}
            >
              Fit
            </button>
            <button className="graphflow-panel__button" type="button" onClick={() => callbacks.onResetLayout?.()}>
              Auto Layout
            </button>
          </div>
        </Panel>
      </ReactFlow>
    </div>
  );
}

function GraphFlowApp({ payload, callbacks }) {
  return (
    <ReactFlowProvider>
      <GraphCanvas key={`${payload.floorKey || ""}:${payload.fitNonce || 0}`} payload={payload} callbacks={callbacks} />
    </ReactFlowProvider>
  );
}

let root = null;
let containerRef = null;
let latestPayload = null;
let latestCallbacks = null;

function mount(container, payload, callbacks) {
  if (!container) return;
  latestPayload = payload || null;
  latestCallbacks = callbacks || {};
  if (!root || containerRef !== container) {
    if (root && containerRef && containerRef !== container) {
      root.unmount();
    }
    containerRef = container;
    root = createRoot(container);
  }
  root.render(<GraphFlowApp payload={payload} callbacks={callbacks || {}} />);
}

function unmount() {
  if (!root) return;
  root.unmount();
  root = null;
  containerRef = null;
}

window.GraphFlowBridge = {
  mount,
  unmount,
  getPayload() {
    return latestPayload;
  },
  simulateNodeDragStop(nodeId, position) {
    latestCallbacks?.onNodeDragStop?.(nodeId, position);
  },
  resetLayout() {
    latestCallbacks?.onResetLayout?.();
  },
};
