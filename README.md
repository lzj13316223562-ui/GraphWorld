# GraphWorld

## 快速记录

```bash
tensorboard --logdir backend/data/tensorboard --host 0.0.0.0 --port 6006
```

待确认问题：

1. 场景逻辑是否通顺：执行操作是否有正确反馈，例如开门后门是否真的被打开；每类物体是否都有动作能让状态合理变化，例如垃圾桶是否存在恢复路径。
2. 当前 prompt 给人看时，人是否能做出正确决策。
3. 如果实际把坏状态修好，例如衣服洗好、碗洗好、鞋子放好、垃圾倒掉，分数是否会回升。
4. 当前分数是否合理，尤其是空间分。

GraphWorld 是一个面向长时程具身任务规划的持续运行符号图仿真框架。它不把场景图当作一次性任务的静态快照，而是把图作为运行时世界状态：房间、物体、设备、人和机器人都在同一张图中，状态会随机器人动作、NPC 日程、环境规则和时间推进持续变化。

当前项目主要回答一个问题：机器人如何在一个不断被人使用、不断变乱、不断产生新任务的环境里，长期维持世界状态和人类服务质量，而不是只完成一条给定指令。

## 数据定义

GraphWorld 的世界状态由四类基础数据组成：

```text
GraphWorld_t = Nodes + Edges + States_t + WorldState_t
```

`Nodes` 是世界中的实体，主要包括：

- `room`：房间或区域，例如 bedroom、bathroom、kitchen、living_room。
- `fixed_object`：固定家具、容器和设备，例如 bed、wardrobe、sink、washer、trash_bin。
- `movable_object`：可移动物体，例如 clothes、shoes、cup、bowl、food。
- `control_object`：控制件或门，例如 button、knob、door。
- `agent`：人类 NPC 和机器人。

每个节点保留统一字段：`id`、`node_type`、`semantic_type`、`states`、`parent`、`interactive_actions`。其中 `semantic_type` 决定物体语义，`states` 记录动态状态，`parent` 表示当前挂载位置，`interactive_actions` 给出可执行动作。

`Edges` 描述节点关系，分为三类：

- 结构关系：房间邻接、包含、part-of 等稳定结构。
- 控制关系：button/knob/door 与设备之间的 `controls`。
- 动态关系：`in`、`on`、`at`、`near`、`held_by`、`worn_by` 等运行时位置关系。

运行时不会把所有动态边硬写死，而是维护 `parent_of`、`relation_of`、`room_of`、`children_of` 索引，再按需重建动态边。这使结构拓扑和临时位置变化保持解耦。

`States` 是图世界可演化的核心。当前关键状态包括：

```text
is_dirty, is_clean, is_open, is_on, is_pressed,
is_wet, is_dry, folded, scattered, misplaced_near,
fill_level, is_full, cycle_remaining, dry_remaining,
is_rotten, is_burnt, freshness, temperature,
vitality, is_wilted, mood, current_activity, is_home
```

状态可以被动作改变，也可以被设备周期、晾干过程、NPC 事件和环境时间改变。例如洗衣机完成后会把衣物从 dirty 变为 clean/wet/unfolded，晾衣架会随时间把 wet 变为 dry。

## 场景资产

场景资产按库组织：

- `backend/core/assets/object_library.py`：物体模板、默认状态、交互动作、能力属性。
- `backend/core/assets/room_library.py`：房间类型、邻接约束、默认家具和默认可移动物。
- `backend/core/assets/npc_library.py`：人类角色、日程事件、事件前置条件和扰动效果。
- `backend/core/assets/task_library.py`：机器人可复用维护技能。

物体通过 capability 组合生成。比如 openable 物体自动获得 `is_open` 与 open/close 动作，switchable 物体自动获得 press 相关行为，fillable/perishable/plant-life 等能力会补齐对应状态。新增物体时优先复用 capability，而不是在每个模板里重复写状态和动作。

## 运行机制

主运行时在 `backend/runtime/engine/runtime.py`。每一步大致如下：

1. 根据当前时间生成 NPC/human event。
2. 机器人获得局部观察、合法动作候选和当前 active goal。
3. `RobotActionSystem` 校验并执行机器人动作。
4. `HumanEventSystem` 解释 NPC 事件模板并改写图状态。
5. `EnvironmentSystem` 推进设备周期、自然过程和世界时钟。
6. 输出 scene、metrics、replay 和 TensorBoard scalar。

动作合法性由 `backend/runtime/engine/validator.py` 检查，状态转移由 `backend/core/transition_rules.py` 执行。当前动作空间为：

```text
move, pick, place, press, open, close, brush, fold, dump
```

重要规则包括：关闭的容器不能直接取放；设备门未关不能启动；布类物体不能用 brush 直接洗干净，必须进入洗衣流程；trash_bin 只接收腐烂或烧焦食物，并需要在 garbage_station 执行 dump；装水的 cup 需要在 sink 执行 dump。

## Agent 方法

当前 Agent 已从“单步反应式选动作”更新为“高层任务 + 技能阶段 + 低层合法动作”的结构。

核心入口在 `backend/runtime/agent/decision.py` 与 `backend/runtime/agent/planning.py`。流程是：

```text
Observation
-> compact world context
-> high-level options
-> active goal / relevant skills
-> legal action candidates
-> LLM 选择 high_level_task + action_index
-> rule-based ranker 校正明显偏离目标的选择
-> engine 执行动作并反馈
```

Prompt 中会给模型五类信息：

- 机器人状态：所在位置、可见房间、是否持有物体。
- 房屋规则：哪些动作能改变哪些状态，哪些捷径不允许。
- `active_goal`：上一阶段未完成的长期目标。
- 相关技能：只放当前状态需要的技能，避免塞完整手册。
- 合法动作候选：每个候选已经过引擎校验，并带简短 hint。

当前技能库包含三类家庭维护流程：

- `laundry_clothes`：脏/湿/未折叠衣物进入洗衣机、启动洗涤、晾干、折叠、收纳到 wardrobe。
- `dispose_food`：腐烂或烧焦食物先进入 trash_bin，再由机器人拿 trash_bin 到 garbage_station 倒掉。
- `empty_cup`：有液体的 cup 被拿到 sink 并执行 dump。

这些技能不是硬编码完整规划器，而是可读的常识流程。LLM 仍负责语义选择，但系统会根据 active goal 的 phase 对候选动作排序。例如 `laundry_clothes` 的 phase 会在 `wash_load -> start_washer -> dry -> fold -> store` 之间随图状态变化；如果模型在 active goal 下选了明显偏离阶段的动作，ranker 会把选择拉回更能推进当前阶段的合法动作。

这个改动解决的是长期任务语义和局部动作候选之间的错配：衣服不能靠 brush 直接恢复，垃圾桶不能永远满着无解，杯子有液体时也不能只靠普通清洁动作跳过倒水步骤。

## 多场景设想

下一阶段不应只扩大家庭物品数量，而是扩展到多种持续运行的服务场景。每个场景都要保留同一个核心问题：NPC 会持续活动、消耗资源、制造副作用，机器人需要长期维持秩序，而不是完成一次性指令。

候选场景：

- 医院：病人挂号、候诊、看诊、取药、输液、离开；护士巡房、送药、换床单、补耗材；医生叫号、检查、开处方。机器人任务包括病床复位、脏床单送洗、药品配送、医疗垃圾分类、轮椅归位、候诊区清洁。这个场景适合强调流程约束和错误代价，例如药不能送错人，医疗垃圾不能混入普通垃圾。
- 超市：顾客进店、拿购物车、选货、结账、离开；店员补货、整理货架、处理退货；收银员扫码、收款、打包。机器人任务包括货架补货、购物车回收、生鲜过期处理、冷柜门关闭、地面清洁、错放商品归位。这个场景扰动密度高，特别适合制造无限任务流。
- 办公室：员工上班、开会、打印、喝咖啡、午餐、下班；前台接待访客、收快递、分发物品；清洁人员整理会议室和倒垃圾。机器人任务包括会议室复位、杯子回茶水间、打印纸补充、快递送到工位、白板擦除、垃圾桶清空。这个场景风险低但高频，适合作为稳定 baseline。
- 工厂：工人取料、操作机器、质检、打包、搬运；质检员标记缺陷品；维修员巡检和修机器。机器人任务包括物料补给、成品搬运、缺陷品隔离、工具归位、机器状态维护、安全通道清理。这个场景流程链条长，适合后期展示多机器人协作。

扩展优先级暂定为：超市 -> 医院 -> 办公室 -> 工厂。超市最容易做出高频扰动和可解释任务；医院论文动机最强；办公室适合做稳态对照；工厂复杂度最高，留到多机器人机制稳定后再做。

## 多 Agent 与多机器人

当前引擎已经有一部分多 Agent 外壳，但还不能认为完整支持多机器人协作。

已经能接住的部分：

- 场景初始化支持多个 human 和多个 robot。`run_experiment.py` 会生成 `human_resident`, `human_resident_02`, ... 和 `robot_01`, `robot_02`, ...。
- 每个机器人有独立的 `memory` 和 `active_goal` 字典。
- 每一步会为每个机器人分别感知、生成候选动作、调用 LLM 或 fallback，再把多个 `robot_actions` 一起交给 `Orchestrator.step()`。
- `RobotActionSystem` 和 validator 的动作字段支持 `agent`，理论上可以执行不同机器人动作。
- `HumanEventSystem` 的 event payload 支持 `actor`，多 NPC 可以各自执行同一日程事件。

主要缺口：

- 机器人动作目前在 `Orchestrator.step()` 里按列表顺序执行，不是并发解析；两个机器人抢同一个物体、同时打开/关闭同一设备、同时向同一容器放东西时，还缺少冲突检测和事务式提交。
- `backend/runtime/agent/decision.py` 里还有多处 `robot_01` 硬编码。多机器人跑起来时，prompt 内的 holding、空间问题过滤、高层选项都可能误以为当前机器人是 `robot_01`。
- `global_restore_goal()` 是每个机器人独立选目标，但没有全局任务分配。多个机器人可能同时追同一个 cup、同一个 trash_bin 或同一扇门。
- 评分和 TensorBoard 轨迹目前主要记录 primary robot；多机器人需要记录每个机器人的房间、动作、active goal、成功率和冲突率。
- 多 human 现在更像同一日程模板复制给多个人，缺少角色差异、资源竞争和队列机制。例如医院的病人、护士、医生不应共享同一套事件流。

因此，多机器人路线建议分三步：

1. 先修单机器人泛化：把 `decision.py` 和相关 prompt 组装中的 `robot_01` 全部改成当前 `agent_id`，确保 `robot_02` 单独跑也行为正确。
2. 再做集中式任务分配：每步先枚举全局问题池，再给每个机器人分配不同 active goal，避免重复抢任务。早期可以用简单规则：已被某个机器人认领的 object/target 暂时不再分给其他机器人。
3. 最后做动作冲突处理：在执行前检查多个 action 是否争用同一 object、container、device 或 door；无冲突的一起执行，有冲突的按优先级执行或让后者失败并反馈给 agent。

多 NPC 路线也应分阶段做：

1. 先支持不同 NPC role 的日程模板，例如 patient、doctor、nurse、customer、cashier、worker。
2. 再支持共享资源和队列，例如收银台、诊室、病床、机器工位。
3. 最后支持 NPC 之间的依赖事件，例如医生看完病人才生成处方，护士拿到处方后才能送药。

## 评分

GraphWorld 当前用三类分数评估长期表现：

```text
final_score = 0.45 * state_score
            + 0.35 * spatial_score
            + 0.20 * human_event_score
```

`state_score` 比较当前状态矩阵 `S_t` 与稳态目标 `S_w`，衡量清洁、开关、湿度、腐烂、垃圾容量、植物活力等状态是否健康。

`spatial_score` 比较当前关系矩阵 `R_t` 与稳态关系 `R_w`，衡量物品是否在合理位置，例如衣服是否收纳、鞋是否回鞋架、餐具是否回到清洗/收纳路径。

`human_event_score` 统计人类日程事件的成功率，衡量机器人是否支持了人的正常活动。

分数是累计平均：坏状态持续越久，历史债越重；如果后面真的把衣服洗好、餐具处理好、鞋子归位、垃圾倒掉，单步 instant score 会改善，累计分也会回升，但会受到前期低分拖累。

当前仍需继续细化的是稳态定义。`S_w` / `R_w` 不应只是初始照片，而应支持 activity override：吃饭时餐具在桌上、出门时鞋在人身上、穿衣时衣服在人身上都应被视为活动中的合理偏离；活动结束后才切回恢复目标。

## 运行

后端实验：

```bash
python -m backend.run_experiment
```

查看 TensorBoard：

```bash
tensorboard --logdir backend/data/tensorboard --host 0.0.0.0 --port 6006
```

前端：

```bash
cd frontend
npm install
npm run dev
```

## 文档

- `docs/README.md`：开题报告和研究主线底稿。
- `docs/GraphWorld.md`：当前方法、相关工作和实现说明。
- `paper/main.tex`：论文草稿，包含 Infinite Task Problem、图世界定义和技能条件化 Agent。
- `backend/core/assets/task_library.md`：家庭维护技能模板说明。
