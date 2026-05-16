# Schedule Randomness Experiment Commands

目标：

```text
5 scenes × base graph × 3 schedules × 2 methods × 1600 steps = 30 runs
```

方法：

```text
no_robot
goal_review
```

日程：

```text
fixed       # 原始固定日程
calendar    # day 会推进，home/office/factory 有工作日/周末差异
stochastic  # calendar + 每个 actor/day 按 seed 打乱非休眠事件顺序
```

## No Robot: 15 Runs

状态：2026-05-15 已跑完 1600 steps。

```bash
cd /home/jansen/GraphWorld

for item in \
  "simple_home_1f 1" \
  "simple_hospital_1f 3" \
  "simple_supermarket_1f 3" \
  "simple_office_1f 3" \
  "simple_factory_1f 3"
do
  set -- $item
  scene="$1"
  humans="$2"
  for mode in fixed calendar stochastic
  do
    seed=0
    if [ "$mode" = "stochastic" ]; then seed=42; fi
    /home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py \
      --scene "$scene" \
      --steps 1600 \
      --only no_robot \
      --robots 0 \
      --humans "$humans" \
      --schedule-mode "$mode" \
      --schedule-seed "$seed" \
      --no-clean \
      --replay-scene-interval 20 \
      --metric-log-interval 10
  done
done
```

## Goal Review: 15 Runs

这 15 条可以分终端并发跑。home 用 `--humans 1`，其他场景用 `--humans 3`。

### Home

```bash
cd /home/jansen/GraphWorld

VLLM_MODEL=qwen35-9b VLLM_BASE_URL=http://127.0.0.1:8000/v1 /home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py --scene simple_home_1f --steps 1600 --only with_robot --robots 1 --humans 1 --agent-model vllm-qwen3.5-9b --agent-mode goal_review --schedule-mode fixed --schedule-seed 0 --no-clean --replay-scene-interval 20 --metric-log-interval 10
```

```bash
cd /home/jansen/GraphWorld

VLLM_MODEL=qwen35-9b VLLM_BASE_URL=http://127.0.0.1:8000/v1 /home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py --scene simple_home_1f --steps 1600 --only with_robot --robots 1 --humans 1 --agent-model vllm-qwen3.5-9b --agent-mode goal_review --schedule-mode calendar --schedule-seed 0 --no-clean --replay-scene-interval 20 --metric-log-interval 10
```

```bash
cd /home/jansen/GraphWorld

VLLM_MODEL=qwen35-9b VLLM_BASE_URL=http://127.0.0.1:8000/v1 /home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py --scene simple_home_1f --steps 1600 --only with_robot --robots 1 --humans 1 --agent-model vllm-qwen3.5-9b --agent-mode goal_review --schedule-mode stochastic --schedule-seed 42 --no-clean --replay-scene-interval 20 --metric-log-interval 10
```

### Hospital

```bash
cd /home/jansen/GraphWorld

VLLM_MODEL=qwen35-9b VLLM_BASE_URL=http://127.0.0.1:8000/v1 /home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py --scene simple_hospital_1f --steps 1600 --only with_robot --robots 1 --humans 3 --agent-model vllm-qwen3.5-9b --agent-mode goal_review --schedule-mode fixed --schedule-seed 0 --no-clean --replay-scene-interval 20 --metric-log-interval 10
```

```bash
cd /home/jansen/GraphWorld

VLLM_MODEL=qwen35-9b VLLM_BASE_URL=http://127.0.0.1:8000/v1 /home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py --scene simple_hospital_1f --steps 1600 --only with_robot --robots 1 --humans 3 --agent-model vllm-qwen3.5-9b --agent-mode goal_review --schedule-mode calendar --schedule-seed 0 --no-clean --replay-scene-interval 20 --metric-log-interval 10
```

```bash
cd /home/jansen/GraphWorld

VLLM_MODEL=qwen35-9b VLLM_BASE_URL=http://127.0.0.1:8000/v1 /home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py --scene simple_hospital_1f --steps 1600 --only with_robot --robots 1 --humans 3 --agent-model vllm-qwen3.5-9b --agent-mode goal_review --schedule-mode stochastic --schedule-seed 42 --no-clean --replay-scene-interval 20 --metric-log-interval 10
```

### Supermarket

```bash
cd /home/jansen/GraphWorld

VLLM_MODEL=qwen35-9b VLLM_BASE_URL=http://127.0.0.1:8000/v1 /home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py --scene simple_supermarket_1f --steps 1600 --only with_robot --robots 1 --humans 3 --agent-model vllm-qwen3.5-9b --agent-mode goal_review --schedule-mode fixed --schedule-seed 0 --no-clean --replay-scene-interval 20 --metric-log-interval 10
```

```bash
cd /home/jansen/GraphWorld

VLLM_MODEL=qwen35-9b VLLM_BASE_URL=http://127.0.0.1:8000/v1 /home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py --scene simple_supermarket_1f --steps 1600 --only with_robot --robots 1 --humans 3 --agent-model vllm-qwen3.5-9b --agent-mode goal_review --schedule-mode calendar --schedule-seed 0 --no-clean --replay-scene-interval 20 --metric-log-interval 10
```

```bash
cd /home/jansen/GraphWorld

VLLM_MODEL=qwen35-9b VLLM_BASE_URL=http://127.0.0.1:8000/v1 /home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py --scene simple_supermarket_1f --steps 1600 --only with_robot --robots 1 --humans 3 --agent-model vllm-qwen3.5-9b --agent-mode goal_review --schedule-mode stochastic --schedule-seed 42 --no-clean --replay-scene-interval 20 --metric-log-interval 10
```

### Office

```bash
cd /home/jansen/GraphWorld

VLLM_MODEL=qwen35-9b VLLM_BASE_URL=http://127.0.0.1:8000/v1 /home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py --scene simple_office_1f --steps 1600 --only with_robot --robots 1 --humans 3 --agent-model vllm-qwen3.5-9b --agent-mode goal_review --schedule-mode fixed --schedule-seed 0 --no-clean --replay-scene-interval 20 --metric-log-interval 10
```

```bash
cd /home/jansen/GraphWorld

VLLM_MODEL=qwen35-9b VLLM_BASE_URL=http://127.0.0.1:8000/v1 /home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py --scene simple_office_1f --steps 1600 --only with_robot --robots 1 --humans 3 --agent-model vllm-qwen3.5-9b --agent-mode goal_review --schedule-mode calendar --schedule-seed 0 --no-clean --replay-scene-interval 20 --metric-log-interval 10
```

```bash
cd /home/jansen/GraphWorld

VLLM_MODEL=qwen35-9b VLLM_BASE_URL=http://127.0.0.1:8000/v1 /home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py --scene simple_office_1f --steps 1600 --only with_robot --robots 1 --humans 3 --agent-model vllm-qwen3.5-9b --agent-mode goal_review --schedule-mode stochastic --schedule-seed 42 --no-clean --replay-scene-interval 20 --metric-log-interval 10
```

### Factory

```bash
cd /home/jansen/GraphWorld

VLLM_MODEL=qwen35-9b VLLM_BASE_URL=http://127.0.0.1:8000/v1 /home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py --scene simple_factory_1f --steps 1600 --only with_robot --robots 1 --humans 3 --agent-model vllm-qwen3.5-9b --agent-mode goal_review --schedule-mode fixed --schedule-seed 0 --no-clean --replay-scene-interval 20 --metric-log-interval 10
```

```bash
cd /home/jansen/GraphWorld

VLLM_MODEL=qwen35-9b VLLM_BASE_URL=http://127.0.0.1:8000/v1 /home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py --scene simple_factory_1f --steps 1600 --only with_robot --robots 1 --humans 3 --agent-model vllm-qwen3.5-9b --agent-mode goal_review --schedule-mode calendar --schedule-seed 0 --no-clean --replay-scene-interval 20 --metric-log-interval 10
```

```bash
cd /home/jansen/GraphWorld

VLLM_MODEL=qwen35-9b VLLM_BASE_URL=http://127.0.0.1:8000/v1 /home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py --scene simple_factory_1f --steps 1600 --only with_robot --robots 1 --humans 3 --agent-model vllm-qwen3.5-9b --agent-mode goal_review --schedule-mode stochastic --schedule-seed 42 --no-clean --replay-scene-interval 20 --metric-log-interval 10
```
