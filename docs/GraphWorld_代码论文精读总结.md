# GraphWorld 代码与论文精读总结

本文档基于对 `E:\GraphWorld` 中论文、核心代码、实验脚本、数据场景、Web 平台和分析脚本的逐文件浏览整理，目标是回答三个问题：

1. GraphWorld 到底在做什么。
2. 代码如何支撑论文叙事。
3. 下一版论文主图应该怎么画，避免空泛和 PPT 感。

## 1. 一句话理解

GraphWorld 不是一个“让机器人在图上规划”的项目，而是一个把场景图提升为运行时世界本体的长期评测基准。房间、物体、设备、NPC、人类事件、机器人动作、设备周期、局部感知、动作合法性和评分都围绕同一张动态图演化。

它真正评估的问题是：

> 在人类持续使用并扰动世界的过程中，机器人能否长期维护世界状态、空间秩序和后续人类活动的可用性。

因此，任务不是外部给定的一条指令，而是从状态偏离、空间偏离和人类流程阻塞中自然出现。

## 2. 论文主线

`paper/main.tex` 目前的主线已经比较清楚：

- 引言：从一次性 embodied task 转向长期 human-agent-world symbiosis。
- 相关工作：对比具身评测、场景图长程规划、人类中心/价值感知评测。
- 方法：定义动态图世界、人类事件模型、动作 schema、agent 方法和评分。
- 实验：五个场景、三类 profile、三类 schedule、三种 agent 策略、多模型对比、阻塞恢复诊断。
- 结论：现有 LLM agent 不是不会生成单步合法动作，而是缺少长期调度、阶段保持和恢复窗口判断。

论文中最核心的句子应该围绕这条链：

> Human events disturb the graph -> robot observes partial graph -> schema-checked actions update graph -> world continues -> later human events either succeed or fail -> long-term scores measure symbiosis.

## 3. 核心代码逐文件理解

### 根目录与文档

- `README.md`
  - 项目总说明。定义 GraphWorld 为 dynamic graph benchmark，强调 infinite task stream、human-agent world symbiosis、五场景实验矩阵和三种 agent mode。

- `docs/GraphWorld.md`
  - 早期研究构想文档。它把 GraphWorld 定义为持续运行符号图仿真框架，重点是世界分、人类分、外生事件、长期 agent 闭环。与当前论文相比更偏开题/技术路线。

- `docs/human_blocking_recovery_definition.md`
  - 定义“人类阻塞恢复率”。核心是：某个可恢复的人类事件前置条件失败后，机器人是否把它恢复到下次事件可成功的状态。这个指标直接支撑论文的人类流程恢复诊断。

- `docs/README.md`
  - 开题报告底稿，提出自演化图世界、长期 RL、职责导向评价等更宽的研究设想。

### `backend/core`

- `nodes.py`
  - 定义图节点类型：floor、room、fixed_object、movable_object、control_object、robot、human。节点带 `semantic_type`、中文名、状态、交互动作、父节点等字段。control object 还支持门类型、可见性/导航阻挡、设备启动前必须关闭等约束。

- `edges.py`
  - 定义关系类型和边类。核心关系包括 `at`、`in`、`on`、`near`、`held_by`、`contains`、`connected`、`controls`。这里把结构边、运行时边、控制边区分开。

- `states.py`
  - 定义统一离散状态空间：脏、开、开机、湿、满、腐烂、烧焦、折叠、温度、容量、周期剩余等。所有事件和动作状态都必须来自这里，避免随意造字段。

- `scenegraph.py`
  - 一个轻量静态图容器，支持加节点、加边、序列化和反序列化。

- `domain_rules.py`
  - 领域规则常量：设备周期、晾衣周期、布料语义、垃圾/倒空规则、放置目标规则等。

- `predicates.py`
  - 动作前置条件判断工具：同房间、是否持有、容器是否可访问、容量是否足够、设备门是否关闭、结构门是否阻挡、垃圾能否放入等。

- `effects.py`
  - 动作效果函数：移动节点、开关目标、按按钮、清洁、折叠、放置、倒空容器。它把动作实际落实为图状态/父子关系变化。

- `actions.py`
  - 九个动作原语：`move`、`pick`、`place`、`press`、`open`、`close`、`brush`、`fold`、`dump`。

- `action_schemas.py`
  - GraphWorld 的动作合法性核心。每个动作都有前置条件和效果。关键约束包括：布类不能 brush，必须洗衣；湿布不能 fold；设备门未关不能 press；垃圾桶只接收可丢弃食物；杯子需要在 sink dump；放置要检查容量和容器可访问性。

- `timed_transitions.py`
  - 时间过程。设备运行会减少 `cycle_remaining`，洗衣机完成后布料变干净但湿，晾衣架倒计时后变干，洗碗机完成后餐具变干净。

### `backend/core/assets`

- `object_library.py`
  - 对象模板库。按 capability 组合对象能力，如 cleanable、openable、switchable、fillable、pickable、foldable、结构门、容器阻挡、设备需关门启动等。覆盖家庭、医院、超市、办公室、工厂对象。

- `room_library.py`
  - 房间类型和楼层模板。提供不同房间的默认 fixture、默认可移动物和房间连接模板。

- `task_library.py`
  - 技能库。包含 `dispose_food`、`empty_cup`、`laundry_clothes` 和医院相关补给/清洁技能。它不是实验答案，而是 procedural prior：告诉 agent 一旦决定处理某类问题，大致阶段是什么。

- `npc_library.py`
  - 项目最关键文件之一。定义五个场景的 NPC、56 个事件、事件前置条件、成功效果、失败效果、价值驱动和日程。
  - Home：起床、穿衣、洗漱、吃饭、回家、夜间洗漱等。
  - Hospital：挂号、候诊、看诊、开方、取药、输液、护士送药、换床单等。
  - Supermarket：进店、取车、买生鲜、买冷链、结账、理货、收银等。
  - Office：到岗、专注工作、会议、经理审阅、访客协作等。
  - Factory：穿 PPE、取零件、装配、质检、维护、交接等。
  - 这些事件会把世界弄乱，也会因世界没维护好而失败。它是 GraphWorld “人类持续扰动世界”的源头。

### `backend/runtime`

- `engine/runtime.py`
  - 运行时核心。`SceneGraph` 维护节点、边、父子关系、房间索引和事件日志。
  - `RobotActionSystem` 验证并执行机器人动作。
  - `HumanEventSystem` 检查 NPC 事件前置条件，写入成功/失败效果，并生成 blocking cases。
  - `EnvironmentSystem` 推进设备/时间过程。
  - `Perception` 只给机器人局部可见图，包括当前房间、相邻可见房间、打开门后的可见范围、记忆置信度。
  - `Orchestrator.step` 的顺序是：机器人动作 -> 捕获 robot_scene -> 人类事件 -> 时间推进 -> 输出场景。

- `agent/planning.py`
  - 根据局部观测生成合法候选动作。候选动作先经过运行时验证，确保 agent 只能在 legal action space 内选择。

- `agent/decision.py`
  - LLM agent 决策核心。它把局部图、初始位置、空间偏离、技能库、active goal 和候选动作压缩成 prompt。
  - 三类模式：reactive、single_round、goal_review。
  - 代码中还有候选动作重排，确保 active goal 的下一步优先，例如洗衣阶段、倒垃圾阶段、医院补给归位阶段。

- `agent/memory.py`
  - 简单记忆：把观察到的节点写入 memory。

- `agent/perception.py`
  - 调用运行时 perception 输出机器人视角。

- `agent/reflection.py`
  - 把执行结果追加到 memory 的 history。

- `eval/matrix_evaluator.py`
  - 评分核心。把场景转换为状态矩阵、动态关系矩阵和人类事件向量。
  - `state_score` 衡量状态接近初始健康状态。
  - `spatial_score` 衡量可移动物体父关系是否归位。
  - `human_event_score` 衡量人类事件成功率。
  - `final_score = 0.45 state + 0.35 spatial + 0.20 human`。

### `backend/run_experiment.py`

这是实验总控脚本，也是论文结果的主要来源。

- 准备场景：添加机器人和 NPC，设置世界时间、日程模式、支持节点。
- 生成人类事件：根据角色日程、day、time_min、schedule_mode 得到每步 NPC 事件。
- 生成/维护 active goal：从全局偏离、可见坏食物、满杯、洗衣、空间归位、医院补给等生成任务。
- goal-review：先让 LLM 判断 keep/switch/finish/drop，再选低层动作。
- 冲突处理：多机器人时避免争抢同一目标。
- 记录指标：即时分、累计平均分、阻塞总数、阻塞恢复数、动作、active goal、LLM 回答、回放、checkpoint。
- 支持 resume 和 TensorBoard。

这个文件说明：论文中的实验不是只跑 runtime，而是围绕“长期维护任务实例、阶段保持、恢复诊断”做了完整实验工程。

### `backend/tools`

- `build_scene_variants.py`
  - 生成三类 graph profile：`compact_cleaning`、`normal_logistics`、`spread_device`。它改变房间拓扑、对象状态和任务压力轴，用来测试图结构是否改变长期调度难度。

- `analyze_experiments.py`
  - 对 replay 做行为分析，包括动作响应、问题窗口、世界/人类分变化。

- `plot_replay_comparison.py`
  - 生成回放对比图：动作时间线、世界变化时间线、分数曲线。

- `try_laundry_fastdownward.py`
  - 用小型洗衣场景尝试 PDDL/Fast Downward 规划，说明洗衣流程本身可以规划，真正难点是长期动态环境中的调度。

- `run_scene_variant_no_robot_checks.py`
  - 检查不同 scene/profile 在无机器人情况下的曲线顺序和难度表现。

- `agent.py`
  - LLM/VLM 客户端封装，支持 Ollama、Anthropic 等。

### `backend/data/sg_output/simple_graph`

包含 5 个 base scene 和每个 scene 的 3 个 profile 变体：

- Home：75-79 个节点，生活洗漱、洗衣、餐厨、归位任务密集。
- Hospital：72 个节点，3 个 human，医疗流程和补给链最强。
- Supermarket：34 个节点，购物车、货架、冷柜、收银流程。
- Office：34 个节点，报告、杯子、会议/访客流程。
- Factory：37 个节点，PPE、零件箱、装配、质检记录、工具包。

### Web 后端 `backend/app`

- `runtime/graphworld_adapter.py`
  - 把 GraphWorld runtime 接到 Web 平台，支持 full/room/fog_of_war 三类可见性，输出 observation 和 candidate actions。

- `runtime/scene_importer.py`
  - 导入 scene JSON，提取节点、边、摘要和版本。

- `runtime/schedule.py`
  - Web 端复用 NPC 日程，生成 expected events 和每步计划事件。

- `services/run_service.py`
  - Web 运行服务。创建 run、回放已选动作、生成当前 observation、执行人类/agent/npc-only step、计算指标、保存 run step。

- `api/routes/*.py`
  - FastAPI 路由：场景、运行、回放、指标、认证、健康检查。

- `db/models/*.py`
  - 数据库模型：用户、场景版本、节点、边、run、run step、metric、artifact。

- `workers/*.py`
  - 后台队列运行 agent run。

### Frontend

- `src/features/scene-graph/SceneGraphCanvas.tsx`
  - ECharts force graph，用颜色区分 room、robot/human、movable、fixed、control、door、button 等，支持关系过滤、搜索、hover、拖拽。

- `src/features/run-monitor/RunDetailPage.tsx`
  - 运行详情页，展示当前 observation、候选动作、指标、最近事件、运行控制。

- `src/features/replay/ReplayPage.tsx`
  - 回放页面，按 step 查看观测、动作和事件。

- `src/features/run-config/RunConfigPage.tsx`
  - 创建运行，选择场景、控制模式、可见性、步数、模型等。

- `src/features/metrics/MetricsPanel.tsx`
  - 展示运行指标。

- `src/styles.css`
  - Web UI 风格是克制的工程仪表盘：白底、浅灰线、蓝色强调、8px 内圆角。这种干净风格可借鉴，但主图不能照搬力导图。

### 论文分析脚本 `paper/analysis`

- `plot_main_800_curves.py` / `plot_focused_figures.py`
  - 生成主实验曲线、雷达图、动作画像和失败案例时间线。

- `plot_model_comparison.py`
  - 生成 Qwen、DeepSeek、Llama 不同方法最终分对比。

- `plot_profile_diversity_800.py`
  - 生成 graph profile 多样性实验。

- `plot_goal_review_schedule_grid.py` / `plot_schedule_agent_vs_baseline_grid.py`
  - 生成日程扰动实验。

- `compute_diagnostic_metrics_v2.py`
  - 计算阶段完成率、局部固着、过早切换、人类阻塞恢复率等诊断指标。

- `recompute_debt_state_scores.py`
  - 重新计算状态债务分，用于更细地看状态偏离。

## 4. 代码和论文的对应关系

- 论文的“动态图世界”对应 `core/nodes.py`、`edges.py`、`states.py`、`runtime/engine/runtime.py`。
- 论文的“人类事件模型”对应 `core/assets/npc_library.py`。
- 论文的“动作 Schema 与合法性”对应 `core/actions.py`、`action_schemas.py`、`predicates.py`、`effects.py`。
- 论文的“Agent 方法”对应 `runtime/agent/*` 和 `run_experiment.py` 中 active goal/goal review 逻辑。
- 论文的“评分”对应 `runtime/eval/matrix_evaluator.py` 和 `run_experiment.py` 的累计平均分。
- 论文的“Graph profile 多样性”对应 `tools/build_scene_variants.py`。
- 论文的“失败分析”对应 replay、active goal、blocking cases、diagnostic metrics。

## 5. 当前项目真正的贡献

1. 把 scene graph 从静态表示推进为运行时状态转移系统。
2. 把人类活动建模为持续扰动和可阻塞流程，而不是背景故事。
3. 用 schema-checked action space 防止 LLM 靠非法动作刷分。
4. 把任务从外部指令变成动态图中的状态/空间/流程偏离。
5. 用 state、spatial、human event 三维长期指标拆解 agent 行为。
6. 用多场景、多 profile、多 schedule 揭示长期调度难点。
7. 指出当前 LLM agent 的核心瓶颈是全局调度、阶段保持和恢复窗口，而不是单步动作生成。

## 6. 主图应该怎么改

上一版图的问题：

- 太像三栏 PPT 框架图。
- 图节点过于抽象，没有具体人类事件。
- 没有展示“前置条件失败 -> 机器人恢复 -> 后续人类事件成功/失败”的核心闭环。
- 文字太多，像摘要可视化，不像论文 teaser。
- 右侧评分和 benchmark axes 堆得太直白，没有和具体世界过程绑定。

下一版主图建议采用“具体场景放大镜 + 动态图小切片 + 指标读数”的风格。参考很多 embodied benchmark / robotics paper 的主图方式：第一眼给一个具体任务世界，而不是先给抽象模块。

推荐画法：

### 方案 A：Hospital Flow Teaser

主画面用医院作为具体例子，因为它最能体现 human event blocking：

1. 左侧 `t`
   - 医生开出处方，护士移动冷藏药，病人等候。
   - 图中显示 `prescription_sheet`、`refrigerated_medicine`、`medicine_fridge`、`patient`、`nurse` 的局部关系。
   - 标出一个红色前置条件失败：`medicine not in fridge` 或 `prescription missing`。

2. 中间 Robot
   - 机器人看到局部图，不是全局上帝视角。
   - active goal：`return_refrigerated_medicine`。
   - action schema：`pick -> move -> open -> place -> close`。

3. 右侧 `t+1`
   - 药回到药房/冰箱，下一次护士送药或病人取药成功。
   - 三个小指标跟随世界变化：state、spatial、human。

底部用五个小图标表示场景扩展：home / hospital / supermarket / office / factory。

### 方案 B：Three Failure Modes Strip

用三个横向小案例：

- Home：衣服脏/湿/未折，穿衣事件失败，需要 laundry phase。
- Supermarket：冷柜开着或牛奶不在冷柜，顾客冷链购物失败。
- Factory：PPE 不在入口柜，工人上岗失败。

每个案例都画成 `human event -> graph deviation -> robot repair -> next event`。右侧小角落给总评估公式。

### 方案 C：GraphWorld Runtime Loop

如果想更方法图：

- 中央是一张具体房间图，不是抽象节点。
- 四周环绕：Human Schedule、Environment Process、Robot Action Schema、Evaluation。
- 每个环节都有真实对象例子：clothes、fridge、cart、PPE、report。

## 7. 我建议采用的主图方向

最建议用方案 A 和方案 B 的混合：

> 一个医院主案例作为中心视觉，旁边用三张小卡展示 home/supermarket/factory 的同构扰动，右下角放三维评分。

这样有几个好处：

- 一眼能看懂 GraphWorld 不是普通图规划。
- 有具体对象和人类流程，不空。
- 能自然引出 blocking recovery。
- 视觉上更像论文 teaser，而不是系统架构 PPT。
- 五场景泛化可以用底部小图标/小条带表达，不需要把所有内容堆满。

## 8. 下一步画图时的具体要求

- 用矢量风格输出 PNG + PDF，放在 `E:\GraphWorld\paper\figures\teaser`。
- 保持白底、细线、低饱和配色，和论文实验图协调。
- 少文字，多对象、关系、状态标签。
- 不画大而空的“LLM Agent”圆圈。
- 不画无意义的抽象彩色节点团。
- 必须出现：Human event、recoverable precondition failure、partial observation、schema-checked action、graph update、human event success score。
- 图中文字建议控制在英文短标签，方便直接进论文。
