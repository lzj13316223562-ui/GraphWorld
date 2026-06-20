# 800-step 诊断指标 V2

- 输入：`docs/experiment_inventory_800_dedup.csv` 中的 75 个 `with_robot` run
- 输出：`docs/diagnostic_metrics_800_v2.csv`

## 指标定义

1. `阶段完成率（代理）`：以 `active_goal.task` 为任务实例；任务从出现到消失，且消失前未进入 stale drop（`steps_without_progress < 12`），记为一次代理完成。
2. `局部固着率`：单条轨迹里最常见 `(action, target)` 对的出现次数，占全部机器人动作的比例。
3. `过早切换次数`：`active_goal.task` 从任务 A 直接切到任务 B，且中间没有回到空任务状态，记为一次过早切换代理。
4. `reactive` 方法通常没有 `active_goal`，因此前两项任务级指标会天然更弱；这属于日志语义限制，不代表它完全没有任务行为。

## 按方法平均

| 方法 | run 数 | 平均 delta | 平均阶段完成率（代理） | 平均局部固着率 | 平均过早切换次数 |
|---|---:|---:|---:|---:|---:|
| reactive | 25 | 0.0063 | 0.0000 | 0.5331 | 0.0000 |
| single_round | 25 | 0.1592 | 0.8994 | 0.3182 | 0.0000 |
| goal_review | 25 | 0.1591 | 0.9874 | 0.2885 | 0.5600 |

## Top 5：阶段完成率（代理）

| scene | model | schedule | 阶段完成率（代理） | delta |
|---|---|---|---:|---:|
| simple_office_1f | vllm_qwen3_5_9b_single_round | fixed | 1.0000 | 0.2988 |
| simple_office_1f | vllm_deepseek_r1_14b_goal_review | fixed | 1.0000 | 0.2856 |
| simple_office_1f | vllm_deepseek_r1_14b_single_round | fixed | 1.0000 | 0.2839 |
| simple_office_1f | vllm_llama3_1_8b_single_round | calendar | 1.0000 | 0.2805 |
| simple_factory_1f | vllm_llama3_1_8b_single_round | stochastic | 1.0000 | 0.2795 |

## Top 5：局部固着率最高

| scene | model | schedule | 局部固着率 | delta |
|---|---|---|---:|---:|
| simple_home_1f | vllm_llama3_1_8b_reactive | calendar | 0.9950 | -0.0068 |
| simple_hospital_1f | vllm_deepseek_r1_14b_reactive | fixed | 0.9900 | -0.0047 |
| simple_factory_1f | vllm_llama3_1_8b_reactive | fixed | 0.9625 | -0.0286 |
| simple_factory_1f | vllm_llama3_1_8b_reactive | calendar | 0.9625 | -0.0285 |
| simple_home_1f | vllm_llama3_1_8b_reactive | stochastic | 0.9387 | 0.0177 |
