# GraphWorld Web Platform Refactor Plan

这份文档描述 GraphWorld 从当前 prototype 形态重构为可维护网页平台的方案。目标不是抛弃现有 runtime，而是把已有的场景图、仿真、agent、observation、visible nodes、replay 和 metrics 能力包装成清晰的 Web 系统。

## 0. 先明确功能需求

一个项目最开始不应该先决定数据库、框架或目录结构，而应该先讲清楚：

```text
谁会用这个系统？
他们进来要完成什么事情？
哪些功能是第一版必须有的？
哪些功能只是后续扩展？
```

GraphWorld Web Platform 的第一目标不是“做一个漂亮网页”，而是把 GraphWorld 变成一个可运行、可测试、可回放、可比较的实验平台。

### 0.1 用户角色

第一版先考虑四类用户：

```text
Researcher
  设计实验、选择场景、配置 agent、查看结果。

Human participant
  进入指定场景，按照任务一步一步手动操作。

Demo viewer
  查看场景、观看 replay、理解 GraphWorld 如何运行。

Admin / developer
  导入场景、调试 runtime、查看 full world 和错误日志。
```

不同用户看到的内容不一样。尤其是 human participant 在迷雾模式下不能看到 full world。

### 0.2 核心使用流程

第一版最重要的流程有五个。

#### 场景浏览

用户需要能：

- 查看有哪些 scene。
- 进入某个 scene。
- 看楼层、房间、物体、agent、状态和边关系。
- 点击节点查看属性和当前状态。

#### 创建实验 Run

用户需要能选择：

- scene version。
- task。
- control mode：agent / human / npc_only。
- visibility mode：full / room / fog_of_war。
- agent model、max steps、seed 等配置。

然后点击开始，生成一个 run。

#### Agent 自动实验

系统需要能：

- 后台运行 agent。
- 每一步生成 observation。
- 根据 observation 生成 candidate actions。
- 让 agent 选择动作。
- 执行动作并推进世界。
- 保存 step、metrics 和 replay。
- 前端展示 run 状态和结果。

#### Human 手动实验

用户需要能：

- 进入 human run 页面。
- 看到当前 observation，而不是 full world。
- 看到当前合法 candidate actions。
- 选择一个动作执行。
- 看到图状态更新、动作反馈和分数变化。
- 重复操作直到完成或结束。

#### Replay 和对比

用户需要能：

- 回放 agent run、human run、npc_only run。
- 拖动时间轴查看每一步。
- 查看 action、reasoning、result、metrics。
- 对比不同 run 的 score 曲线和最终结果。

### 0.3 第一版必须有的功能

```text
Scene list
Scene graph view
Run creation
Agent run
Human run
Fog-of-war observation
Candidate actions
Run status
Replay timeline
Step inspector
Metrics summary
```

这些是 MVP 的底线。

### 0.4 第一版暂时不做的功能

```text
完整用户权限系统
多人同时协作
Human + Agent hybrid 接管
复杂 study assignment
Neo4j 图数据库
在线编辑 scene
复杂 WebSocket 协议
公开部署安全体系
```

这些可以后续做，但不能让第一版被复杂度拖住。

### 0.5 功能需求决定架构

上面的需求推出几个关键架构结论：

```text
因为 agent run 和 human run 都要回放，所以需要统一 Run 模型。
因为 human 和 agent 都受迷雾限制，所以需要统一 Observation 层。
因为动作必须合法，所以 candidate actions 要由后端生成。
因为 agent run 是长任务，所以需要 worker。
因为 replay 和 metrics 要可查询，所以不能只存大 JSON 文件。
因为场景会变化，所以实验必须绑定 SceneVersion。
```

也就是说，技术架构不是先验选择，而是从这些功能需求自然推出来的。

## 1. 目标

GraphWorld Web Platform 应该支持：

- 浏览场景图、楼层、节点、边和状态。
- 创建实验 run，选择由 agent 自动执行或由人类手动执行。
- 支持迷雾模式，让 agent 和 human 只能基于 observation 行动。
- 实时查看 run 状态、动作、分数和世界变化。
- 回放任意 run，包括 agent run 和 human run。
- 对比不同 run 的指标曲线、失败原因和最终效果。
- 保存可复现的 scene version、run config、replay artifact 和 metrics。

核心原则：

```text
Run 是统一抽象。
Agent 自动实验和 Human 手动测试都是 Run。
Full world 是真实状态。
Observation 是 actor 能看到的局部状态。
Candidate actions 必须由后端根据 observation 生成。
Replay 和 metrics 复用同一套数据结构。
```

## 2. 总体架构

```text
React frontend
  |
  | HTTP / SSE / WebSocket
  v
FastAPI + Pydantic
  |
  | read/write
  v
PostgreSQL
  |
  | enqueue long jobs
  v
Redis
  |
  | worker consumes jobs
  v
RQ / Arq worker
  |
  | calls
  v
GraphWorld runtime
  |
  | saves results
  v
PostgreSQL + artifact files
```

建议技术栈：

```text
Frontend:
  React
  TypeScript
  Vite
  React Router
  TanStack Query
  Zustand
  React Flow
  ECharts / Recharts

Backend:
  FastAPI
  Pydantic v2
  SQLAlchemy 2.0
  Alembic
  PostgreSQL
  Redis
  RQ or Arq
  Uvicorn
  Gunicorn for deployment
```

## 3. 关键领域模型

### SceneVersion

实验不能直接引用“当前场景文件”，必须引用固定版本：

```text
Scene
  场景集合，例如 simple_home_1f

SceneVersion
  某一次导入或生成后的不可变版本
  保存 source_json、节点、边、初始状态和版本号
```

这样旧实验永远可以复现。

### Run

Run 表示一次世界演化记录。

```text
Run
  id
  scene_version_id
  control_mode
  visibility_mode
  status
  current_step
  config
  summary
```

`control_mode`：

```text
agent       agent 自动选择动作
human       用户手动选择动作
npc_only    只跑人类/NPC/环境 baseline
hybrid      后续扩展，人和 agent 交替或协同
```

第一版只需要实现：

```text
agent
human
npc_only
```

### RunStep

RunStep 表示一次决策动作后的完整 transition。

```text
RunStep
  run_id
  step_index
  actor_type
  actor_id
  observation
  candidate_actions
  selected_action
  action_result
  world_state_before
  world_state_after
  environment_events
  npc_events
  metrics_after
```

这里的 step 不只是低层 tick，而是一次 actor 决策后的完整世界变化。

### FullWorld / Observation / Memory

GraphWorld runtime 里已经有局部可见逻辑。当前代码中 `Perception.robot_view()` 会返回 `visible_rooms`、可见节点和可见边；agent planning 和 decision 也已经使用 `observation` 和 `visible_nodes`。

Web 平台应该把这套能力提升为正式 observation 层：

```text
FullWorld
  后端真实完整世界状态

Observation
  当前 actor 能看到的局部图

Memory
  actor 历史见过但当前不可见的旧信息
```

建议 observation 返回：

```json
{
  "actor_id": "robot_01",
  "step_index": 12,
  "visibility_mode": "fog_of_war",
  "visible_rooms": [],
  "visible_nodes": [],
  "visible_edges": [],
  "memory_nodes": [],
  "unknown_rooms": [],
  "confidence_by_room": {},
  "candidate_actions": []
}
```

## 4. 迷雾模式

迷雾模式不能只是前端隐藏节点。正确位置是后端 observation 层。

支持的 visibility mode：

```text
full
  调试和 baseline，全图可见

room
  只看当前房间

fog_of_war
  当前可见 + 历史记忆 + 未知区域
```

第一版建议只做这三个。

执行流程：

```text
FullWorld
  |
ObservationBuilder.build(actor_id, visibility_mode)
  |
Observation
  |
CandidateActionService.generate(observation)
  |
Human or Agent chooses action
  |
Runtime validates against FullWorld
  |
Runtime applies action
  |
New FullWorld + New Observation
```

关键规则：

- Agent prompt 只能使用 observation。
- Human 页面只能显示 observation。
- Candidate actions 只能基于 observation 生成。
- 后端执行动作时仍然用 full world 校验。
- 管理员调试接口可以查看 full world，但普通 human test 不能访问。

## 5. Human 手动实验

Human test 不应该是独立系统，而是：

```text
Run.control_mode = human
```

创建 run：

```http
POST /api/runs
```

```json
{
  "scene_version_id": "scene_v1",
  "control_mode": "human",
  "visibility_mode": "fog_of_war",
  "task_id": "restore_home",
  "max_steps": 1600
}
```

返回当前状态：

```http
GET /api/runs/{run_id}/current
```

```json
{
  "run_id": "run_123",
  "status": "waiting_for_human",
  "step_index": 0,
  "observation": {},
  "candidate_actions": [],
  "metrics": {}
}
```

用户执行动作：

```http
POST /api/runs/{run_id}/actions
```

```json
{
  "action_id": "pick:cup_01"
}
```

后端执行一步并返回：

```json
{
  "run_id": "run_123",
  "status": "waiting_for_human",
  "step_index": 1,
  "observation": {},
  "candidate_actions": [],
  "action_result": {
    "ok": true
  },
  "metrics": {}
}
```

Human 模式每一步应该走低延迟 HTTP 请求，不需要每步都进 worker。

## 6. Agent 自动实验

Agent run 适合走后台 worker。

```text
POST /api/runs
  |
create run row with status=pending
  |
enqueue run_agent_job in Redis
  |
worker loads scene version
  |
worker creates GraphWorld orchestrator
  |
loop:
    build observation
    generate candidate actions
    call agent
    apply action
    save run step
    save metrics
  |
save summary + artifact
```

Agent run 创建请求：

```json
{
  "scene_version_id": "scene_v1",
  "control_mode": "agent",
  "visibility_mode": "fog_of_war",
  "agent_model": "vllm-qwen3.5-9b",
  "task_id": "restore_home",
  "max_steps": 1600
}
```

前端可以轮询：

```http
GET /api/runs/{run_id}
GET /api/runs/{run_id}/steps?offset=0&limit=100
```

也可以用 SSE：

```http
GET /api/runs/{run_id}/events
```

## 7. 后端目录结构

建议新后端结构：

```text
backend/
  app/
    main.py

    api/
      routes/
        scenes.py
        scene_versions.py
        runs.py
        run_steps.py
        replays.py
        metrics.py
        agents.py
        health.py

    core/
      config.py
      errors.py
      logging.py
      security.py

    db/
      session.py
      models/
        scene.py
        run.py
        replay.py
        metric.py
        artifact.py
      migrations/

    schemas/
      scene.py
      graph.py
      run.py
      observation.py
      action.py
      replay.py
      metrics.py

    repositories/
      scene_repo.py
      run_repo.py
      run_step_repo.py
      metric_repo.py

    services/
      scene_service.py
      run_service.py
      observation_service.py
      candidate_action_service.py
      replay_service.py
      metric_service.py

    runtime/
      graphworld_adapter.py
      scene_importer.py
      observation_adapter.py
      replay_adapter.py
      metric_extractor.py

    workers/
      queue.py
      jobs.py

    storage/
      artifact_store.py
      local_store.py
```

分层职责：

```text
api/routes
  HTTP 输入输出，不写复杂业务逻辑

schemas
  Pydantic 请求和响应模型

services
  业务逻辑，例如创建 run、执行 human action、生成 observation

repositories
  数据库读写

runtime
  包装现有 GraphWorld runtime，不把 Web 逻辑塞进仿真核心

workers
  agent 自动实验、批量评测、离线指标计算

storage
  replay.json、checkpoint、tensorboard logs、图片和导出文件
```

## 8. 数据库设计

第一版用 PostgreSQL + JSONB。

```text
scenes
  id
  name
  domain
  description
  created_at

scene_versions
  id
  scene_id
  version
  source_json jsonb
  graph_summary jsonb
  created_at

scene_nodes
  id
  scene_version_id
  node_key
  node_type
  semantic_type
  properties jsonb

scene_edges
  id
  scene_version_id
  source_key
  target_key
  relation
  properties jsonb

runs
  id
  scene_version_id
  control_mode
  visibility_mode
  status
  current_step
  config jsonb
  summary jsonb
  artifact_uri
  error_message
  started_at
  finished_at
  created_at

run_steps
  id
  run_id
  step_index
  actor_type
  actor_id
  observation jsonb
  candidate_actions jsonb
  selected_action jsonb
  action_result jsonb
  world_state_before jsonb
  world_state_after jsonb
  events jsonb
  metrics jsonb
  created_at

metrics
  id
  run_id
  step_index
  metric_name
  metric_value
  metric_payload jsonb

artifacts
  id
  run_id
  artifact_type
  uri
  metadata jsonb
  created_at
```

大 replay 和 checkpoint 可以放 artifact files，但数据库必须保存可查询索引。

## 9. API 设计

### Scene API

```http
GET    /api/scenes
POST   /api/scenes/import
GET    /api/scenes/{scene_id}
GET    /api/scenes/{scene_id}/versions
GET    /api/scene-versions/{version_id}
GET    /api/scene-versions/{version_id}/graph
POST   /api/scene-versions/{version_id}/validate
```

### Run API

```http
POST   /api/runs
GET    /api/runs
GET    /api/runs/{run_id}
GET    /api/runs/{run_id}/current
POST   /api/runs/{run_id}/actions
POST   /api/runs/{run_id}/advance
POST   /api/runs/{run_id}/cancel
GET    /api/runs/{run_id}/events
```

说明：

- `POST /api/runs/{run_id}/actions` 用于 human 模式。
- `POST /api/runs/{run_id}/advance` 可用于调试或手动推进 agent 一步。
- agent 自动跑时一般由 worker 自己 advance。

### Replay API

```http
GET /api/runs/{run_id}/replay
GET /api/runs/{run_id}/steps?offset=0&limit=100
GET /api/runs/{run_id}/steps/{step_index}
GET /api/runs/{run_id}/diff?from_step=10&to_step=11
```

### Metrics API

```http
GET /api/runs/{run_id}/metrics
GET /api/runs/{run_id}/metrics/{metric_name}
GET /api/compare?run_ids=a,b,c
```

## 10. 前端目录结构

建议使用 React + TypeScript + Vite。

```text
frontend/
  src/
    app/
      App.tsx
      router.tsx
      providers.tsx

    api/
      client.ts
      scenes.ts
      runs.ts
      replays.ts
      metrics.ts

    types/
      scene.ts
      graph.ts
      run.ts
      observation.ts
      action.ts
      replay.ts
      metrics.ts

    stores/
      uiStore.ts
      sceneViewStore.ts
      replayPlayerStore.ts

    features/
      scene-browser/
        SceneListPage.tsx
        SceneDetailPage.tsx

      scene-graph/
        SceneGraphCanvas.tsx
        SceneGraphNode.tsx
        SceneGraphEdge.tsx
        graphAdapter.ts
        graphLayout.ts
        graphStyle.ts

      run-config/
        RunConfigPage.tsx
        ControlModeSelect.tsx
        VisibilityModeSelect.tsx
        AgentModelSelect.tsx

      run-monitor/
        RunDetailPage.tsx
        RunStatusPanel.tsx
        RunEventStream.tsx

      human-control/
        HumanRunPage.tsx
        CandidateActionPanel.tsx
        ActionResultPanel.tsx

      replay/
        ReplayPage.tsx
        ReplayTimeline.tsx
        ReplayControls.tsx
        ReplayStepInspector.tsx
        ReplayDiffPanel.tsx

      metrics/
        MetricsPanel.tsx
        ScoreChart.tsx
        RunComparisonView.tsx

    components/
      layout/
      ui/
      forms/
```

## 11. 前端页面

### `/scenes`

场景列表：

- 搜索 scene。
- 查看 domain、floor count、node count、version count。
- 进入 scene detail。

### `/scenes/:sceneId`

场景详情：

- 展示最新 scene version。
- 图可视化。
- 楼层切换。
- 节点详情。
- 版本列表。

### `/runs/new`

创建 run：

- 选择 scene version。
- 选择 task。
- 选择 `control_mode`。
- 选择 `visibility_mode`。
- 如果是 agent，选择 model、max steps、seed。
- 如果是 human，进入手动操作页。

### `/runs/:runId`

统一 run 页面：

- agent run：显示运行状态、最新 step、score、日志。
- human run：显示图、候选动作、当前 observation、执行反馈。
- completed run：显示 summary 和 replay 入口。

### `/runs/:runId/replay`

回放：

- 时间轴。
- step 播放。
- 当前 action、reasoning、result。
- 图状态变化。
- metrics 曲线。

### `/compare`

实验对比：

- 多个 run 的 score 曲线。
- final score。
- success/failure reason。
- 不同 control mode 和 visibility mode 的对比。

## 12. 前端状态管理

服务端数据用 TanStack Query：

```text
scene list
scene version
run detail
run current state
run steps
metrics
replay
```

本地 UI 状态用 Zustand：

```text
selected floor
selected node
graph layout
replay current step
sidebar open/closed
language
```

不要再使用一个全局大 `state` 管所有东西。

## 13. 从现有前端迁移

当前前端主要是：

```text
frontend/web/index.html
frontend/web/app.js
frontend/web/styles.css
frontend/reactflow-src/graphflow.jsx
```

迁移策略：

1. 新建 React + TypeScript + Vite 工程。
2. 先实现 API client 和基础路由。
3. 把 `reactflow-src/graphflow.jsx` 升级为正式 `SceneGraphCanvas.tsx`。
4. 把 `app.js` 里的 layout 函数抽到 `graphLayout.ts`。
5. 先做 `/scenes` 和 `/scenes/:sceneId`。
6. 再做 `/runs/new` 和 `/runs/:runId`。
7. 再做 `/runs/:runId/replay`。
8. 最后迁移 metrics、human control 和 compare 页面。

现有 `app.js` 应该当作需求样本和算法来源，不建议继续在里面叠功能。

## 14. 实施步骤

### Step 1: 后端骨架

- 建 FastAPI app。
- 建 Pydantic schemas。
- 建 SQLAlchemy models。
- 配 PostgreSQL。
- 配 Alembic。
- 实现 health check。

完成标志：

```text
GET /api/health
alembic upgrade head
pytest backend tests pass
```

### Step 2: Scene import

- 从现有 scene JSON 导入 `scene_versions`。
- 保存 source_json。
- 解析 nodes 和 edges。
- 实现 scene graph 查询接口。

完成标志：

```text
GET /api/scenes
GET /api/scene-versions/{id}/graph
```

### Step 3: Runtime adapter

- 包装现有 GraphWorld runtime。
- 提供创建 orchestrator、读取 full world、执行 action、提取 metrics 的统一接口。
- 不把 Web 逻辑写入 runtime 核心。

完成标志：

```text
RuntimeAdapter.load_scene_version(...)
RuntimeAdapter.apply_action(...)
RuntimeAdapter.build_observation(...)
```

### Step 4: Observation service

- 复用现有 `Perception.robot_view()`。
- 支持 `full`、`room`、`fog_of_war`。
- 返回 `visible_nodes`、`visible_edges`、`memory_nodes`、`unknown_rooms`、`confidence_by_room`。

完成标志：

```text
GET /api/runs/{run_id}/current
```

返回的是 observation，而不是 full world。

### Step 5: Candidate action service

- 复用现有 `candidate_actions(orchestrator, observation)`。
- 返回 action id、action type、target、reason、preview。
- human 和 agent 使用同一候选动作集合。

完成标志：

```text
candidate_actions 只包含当前 observation 中合法可见动作
```

### Step 6: Human run

- 创建 `control_mode=human` 的 run。
- 返回初始 observation。
- 用户每次提交 action。
- 后端执行一步、保存 run_step、返回新 observation。

完成标志：

```text
POST /api/runs
POST /api/runs/{run_id}/actions
GET /api/runs/{run_id}/steps
```

### Step 7: Agent run worker

- 配 Redis。
- 选择 RQ 或 Arq。
- 创建 agent run 后入队。
- Worker 循环执行 GraphWorld runtime。
- 每步保存 run_step 和 metrics。

完成标志：

```text
POST /api/runs with control_mode=agent
worker consumes job
run status changes pending -> running -> completed
```

### Step 8: Frontend MVP

- React/Vite/TypeScript 工程。
- Scene list。
- Scene graph。
- Run create。
- Human action panel。
- Run status。
- Replay timeline。

完成标志：

```text
用户可以选择场景
选择 agent 或 human
开始 run
human 模式可以一步一步点动作
agent 模式可以看状态和结果
completed run 可以 replay
```

### Step 9: Metrics and compare

- 保存 per-step metrics。
- 做 run metrics 页面。
- 做 compare 页面。
- 支持按 scene、agent、visibility mode 过滤。

完成标志：

```text
不同 control_mode 和 visibility_mode 的 run 可以统一比较
```

## 15. MVP 范围

第一版只做：

```text
Backend:
  FastAPI
  PostgreSQL
  scene import
  run create
  human step
  agent worker
  replay steps
  metrics summary

Frontend:
  scene list
  scene graph
  run config
  human action panel
  run monitor
  replay page

Modes:
  control_mode = agent | human | npc_only
  visibility_mode = full | room | fog_of_war
```

第一版暂不做：

```text
Neo4j
复杂多人协作
完整权限系统
hybrid 接管
复杂 study assignment
全量 WebSocket 协议
```

## 16. 风险和约束

### 不要拆成两套 run

错误方向：

```text
agent_run
human_session
replay
```

正确方向：

```text
Run + control_mode
```

### 不要让前端生成合法动作

前端只展示候选动作。后端负责生成和校验。

### 不要让实验接口暴露 full world

迷雾模式下，人和 agent 都只能得到 observation。

### 不要只存 replay JSON

Replay artifact 可以存文件，但数据库必须保存 run、step、action、score、status 等索引。

### 不要把 layout 当世界事实

图布局属于前端展示层。Runtime world 只保存语义图和状态。

## 17. 最终形态

GraphWorld Web Platform 最终应该是：

```text
一个统一 run 系统
  agent 可以自动跑
  human 可以手动跑
  npc_only 可以做 baseline

一个统一 observation 系统
  full world 后端保存
  observation 给 actor 使用
  fog_of_war 是正式实验条件

一个统一 replay 系统
  agent run 和 human run 都能回放
  metrics 都能比较

一个清晰前端
  场景
  实验
  运行
  回放
  指标
```

这样 GraphWorld 不只是一个仿真脚本集合，而是一个可以支撑实验、论文展示、人类测试和 agent 对比的网页平台。

## 18. 当前落地状态

当前仓库已经按这份方案落地了第一版 Web MVP 骨架。

### 后端已经完成

```text
backend/app/
  FastAPI app
  Pydantic v2 schemas
  SQLAlchemy 2.0 models
  Alembic migration
  PostgreSQL JSONB schema
  Scene import
  Scene graph API
  Run create/list/current
  Human action step
  Agent/NPC advance
  RQ worker job
  Replay steps API
  Metrics API
  full / room / fog_of_war observation
```

主要接口：

```http
GET  /api/health
GET  /api/scenes
POST /api/scenes/import
GET  /api/scenes/{scene_id}/versions
GET  /api/scene-versions/{version_id}/graph

POST /api/runs
GET  /api/runs
GET  /api/runs/{run_id}
GET  /api/runs/{run_id}/current
POST /api/runs/{run_id}/actions
POST /api/runs/{run_id}/advance
POST /api/runs/{run_id}/cancel
GET  /api/runs/{run_id}/steps
GET  /api/runs/{run_id}/replay
GET  /api/runs/{run_id}/metrics
```

### 前端已经完成

```text
frontend/src/
  React + TypeScript + Vite
  React Router
  TanStack Query
  Zustand UI store
  React Flow graph canvas

Pages:
  /scenes
  /scenes/:sceneId
  /runs/new
  /runs/:runId
  /runs/:runId/replay
```

第一版页面支持：

```text
查看 scene list
查看 scene graph
选择 scene version 创建 run
选择 agent / human / npc_only
选择 full / room / fog_of_war
human 模式一步一步点动作
agent/npc 模式手动 advance 或交给 worker
查看 replay timeline
查看 per-step metrics
```

### 本地启动

后端依赖装在：

```bash
/home/jansen/GraphWorld/.venv
```

本地 PostgreSQL 和 Redis 装在：

```bash
/home/jansen/GraphWorld/.gw-services
```

启动数据库和 Redis：

```bash
scripts/web_services.sh start
```

运行 migration：

```bash
GRAPHWORLD_DATABASE_URL=postgresql+psycopg://graphworld:graphworld@127.0.0.1:55432/graphworld \
  .venv/bin/alembic upgrade head
```

启动 API：

```bash
scripts/web_api.sh
```

启动 worker：

```bash
scripts/web_worker.sh
```

启动前端：

```bash
cd frontend
npm run dev
```

验证命令：

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m compileall -q backend/app
cd frontend && npm run build
```
