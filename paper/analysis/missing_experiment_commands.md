# Missing GraphWorld Experiment Commands

## 已完成

### 主实验：20/20 已完成

- 5 base scenes x fixed schedule x 4 methods
- methods: no_robot, reactive, single_round, goal_review
- scenes: simple_home_1f, simple_hospital_1f, simple_supermarket_1f, simple_office_1f, simple_factory_1f

### 日程随机性实验：30/30 已完成

- 5 base scenes x 3 schedules x 2 methods
- schedules: fixed, calendar, stochastic
- methods: no_robot, goal_review

## 未完成

### 多样性实验：缺 30 组

- 5 scenes x 3 graph profiles x 2 methods
- profiles: compact_cleaning, normal_logistics, spread_device
- methods: no_robot, goal_review

### 补充方法实验：缺 20 组

- 5 base scenes x 2 schedules x 2 methods
- schedules: calendar, stochastic
- methods: reactive, single_round
- 用途：判断 state 拉不开是不是 goal_review 特有问题。

---

# 1. 多样性实验：30 commands

## Home variants

```bash
/home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py --scene simple_home_1f__compact_cleaning --steps 1600 --only no_robot --robots 0 --humans 1 --no-clean --replay-scene-interval 20 --metric-log-interval 10
```

```bash
VLLM_MODEL=qwen35-9b VLLM_BASE_URL=http://127.0.0.1:8000/v1 /home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py --scene simple_home_1f__compact_cleaning --steps 1600 --only with_robot --robots 1 --humans 1 --agent-model vllm-qwen3.5-9b --agent-mode goal_review --no-clean --replay-scene-interval 20 --metric-log-interval 10
```

```bash
/home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py --scene simple_home_1f__normal_logistics --steps 1600 --only no_robot --robots 0 --humans 1 --no-clean --replay-scene-interval 20 --metric-log-interval 10
```

```bash
VLLM_MODEL=qwen35-9b VLLM_BASE_URL=http://127.0.0.1:8000/v1 /home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py --scene simple_home_1f__normal_logistics --steps 1600 --only with_robot --robots 1 --humans 1 --agent-model vllm-qwen3.5-9b --agent-mode goal_review --no-clean --replay-scene-interval 20 --metric-log-interval 10
```

```bash
/home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py --scene simple_home_1f__spread_device --steps 1600 --only no_robot --robots 0 --humans 1 --no-clean --replay-scene-interval 20 --metric-log-interval 10
```

```bash
VLLM_MODEL=qwen35-9b VLLM_BASE_URL=http://127.0.0.1:8000/v1 /home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py --scene simple_home_1f__spread_device --steps 1600 --only with_robot --robots 1 --humans 1 --agent-model vllm-qwen3.5-9b --agent-mode goal_review --no-clean --replay-scene-interval 20 --metric-log-interval 10
```

## Hospital variants

```bash
/home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py --scene simple_hospital_1f__compact_cleaning --steps 1600 --only no_robot --robots 0 --humans 3 --no-clean --replay-scene-interval 20 --metric-log-interval 10
```

```bash
VLLM_MODEL=qwen35-9b VLLM_BASE_URL=http://127.0.0.1:8000/v1 /home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py --scene simple_hospital_1f__compact_cleaning --steps 1600 --only with_robot --robots 1 --humans 3 --agent-model vllm-qwen3.5-9b --agent-mode goal_review --no-clean --replay-scene-interval 20 --metric-log-interval 10
```

```bash
/home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py --scene simple_hospital_1f__normal_logistics --steps 1600 --only no_robot --robots 0 --humans 3 --no-clean --replay-scene-interval 20 --metric-log-interval 10
```

```bash
VLLM_MODEL=qwen35-9b VLLM_BASE_URL=http://127.0.0.1:8000/v1 /home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py --scene simple_hospital_1f__normal_logistics --steps 1600 --only with_robot --robots 1 --humans 3 --agent-model vllm-qwen3.5-9b --agent-mode goal_review --no-clean --replay-scene-interval 20 --metric-log-interval 10
```

```bash
/home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py --scene simple_hospital_1f__spread_device --steps 1600 --only no_robot --robots 0 --humans 3 --no-clean --replay-scene-interval 20 --metric-log-interval 10
```

```bash
VLLM_MODEL=qwen35-9b VLLM_BASE_URL=http://127.0.0.1:8000/v1 /home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py --scene simple_hospital_1f__spread_device --steps 1600 --only with_robot --robots 1 --humans 3 --agent-model vllm-qwen3.5-9b --agent-mode goal_review --no-clean --replay-scene-interval 20 --metric-log-interval 10
```

## Supermarket variants

```bash
/home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py --scene simple_supermarket_1f__compact_cleaning --steps 1600 --only no_robot --robots 0 --humans 3 --no-clean --replay-scene-interval 20 --metric-log-interval 10
```

```bash
VLLM_MODEL=qwen35-9b VLLM_BASE_URL=http://127.0.0.1:8000/v1 /home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py --scene simple_supermarket_1f__compact_cleaning --steps 1600 --only with_robot --robots 1 --humans 3 --agent-model vllm-qwen3.5-9b --agent-mode goal_review --no-clean --replay-scene-interval 20 --metric-log-interval 10
```

```bash
/home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py --scene simple_supermarket_1f__normal_logistics --steps 1600 --only no_robot --robots 0 --humans 3 --no-clean --replay-scene-interval 20 --metric-log-interval 10
```

```bash
VLLM_MODEL=qwen35-9b VLLM_BASE_URL=http://127.0.0.1:8000/v1 /home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py --scene simple_supermarket_1f__normal_logistics --steps 1600 --only with_robot --robots 1 --humans 3 --agent-model vllm-qwen3.5-9b --agent-mode goal_review --no-clean --replay-scene-interval 20 --metric-log-interval 10
```

```bash
/home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py --scene simple_supermarket_1f__spread_device --steps 1600 --only no_robot --robots 0 --humans 3 --no-clean --replay-scene-interval 20 --metric-log-interval 10
```

```bash
VLLM_MODEL=qwen35-9b VLLM_BASE_URL=http://127.0.0.1:8000/v1 /home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py --scene simple_supermarket_1f__spread_device --steps 1600 --only with_robot --robots 1 --humans 3 --agent-model vllm-qwen3.5-9b --agent-mode goal_review --no-clean --replay-scene-interval 20 --metric-log-interval 10
```

## Office variants

```bash
/home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py --scene simple_office_1f__compact_cleaning --steps 1600 --only no_robot --robots 0 --humans 3 --no-clean --replay-scene-interval 20 --metric-log-interval 10
```

```bash
VLLM_MODEL=qwen35-9b VLLM_BASE_URL=http://127.0.0.1:8000/v1 /home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py --scene simple_office_1f__compact_cleaning --steps 1600 --only with_robot --robots 1 --humans 3 --agent-model vllm-qwen3.5-9b --agent-mode goal_review --no-clean --replay-scene-interval 20 --metric-log-interval 10
```

```bash
/home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py --scene simple_office_1f__normal_logistics --steps 1600 --only no_robot --robots 0 --humans 3 --no-clean --replay-scene-interval 20 --metric-log-interval 10
```

```bash
VLLM_MODEL=qwen35-9b VLLM_BASE_URL=http://127.0.0.1:8000/v1 /home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py --scene simple_office_1f__normal_logistics --steps 1600 --only with_robot --robots 1 --humans 3 --agent-model vllm-qwen3.5-9b --agent-mode goal_review --no-clean --replay-scene-interval 20 --metric-log-interval 10
```

```bash
/home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py --scene simple_office_1f__spread_device --steps 1600 --only no_robot --robots 0 --humans 3 --no-clean --replay-scene-interval 20 --metric-log-interval 10
```

```bash
VLLM_MODEL=qwen35-9b VLLM_BASE_URL=http://127.0.0.1:8000/v1 /home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py --scene simple_office_1f__spread_device --steps 1600 --only with_robot --robots 1 --humans 3 --agent-model vllm-qwen3.5-9b --agent-mode goal_review --no-clean --replay-scene-interval 20 --metric-log-interval 10
```

## Factory variants

```bash
/home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py --scene simple_factory_1f__compact_cleaning --steps 1600 --only no_robot --robots 0 --humans 3 --no-clean --replay-scene-interval 20 --metric-log-interval 10
```

```bash
VLLM_MODEL=qwen35-9b VLLM_BASE_URL=http://127.0.0.1:8000/v1 /home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py --scene simple_factory_1f__compact_cleaning --steps 1600 --only with_robot --robots 1 --humans 3 --agent-model vllm-qwen3.5-9b --agent-mode goal_review --no-clean --replay-scene-interval 20 --metric-log-interval 10
```

```bash
/home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py --scene simple_factory_1f__normal_logistics --steps 1600 --only no_robot --robots 0 --humans 3 --no-clean --replay-scene-interval 20 --metric-log-interval 10
```

```bash
VLLM_MODEL=qwen35-9b VLLM_BASE_URL=http://127.0.0.1:8000/v1 /home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py --scene simple_factory_1f__normal_logistics --steps 1600 --only with_robot --robots 1 --humans 3 --agent-model vllm-qwen3.5-9b --agent-mode goal_review --no-clean --replay-scene-interval 20 --metric-log-interval 10
```

```bash
/home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py --scene simple_factory_1f__spread_device --steps 1600 --only no_robot --robots 0 --humans 3 --no-clean --replay-scene-interval 20 --metric-log-interval 10
```

```bash
VLLM_MODEL=qwen35-9b VLLM_BASE_URL=http://127.0.0.1:8000/v1 /home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py --scene simple_factory_1f__spread_device --steps 1600 --only with_robot --robots 1 --humans 3 --agent-model vllm-qwen3.5-9b --agent-mode goal_review --no-clean --replay-scene-interval 20 --metric-log-interval 10
```

---

# 2. 补充方法实验：20 commands

## Calendar schedule: reactive/single_round

## calendar schedule: reactive/single_round

```bash
VLLM_MODEL=qwen35-9b VLLM_BASE_URL=http://127.0.0.1:8000/v1 /home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py --scene simple_home_1f --steps 1600 --only with_robot --robots 1 --humans 1 --agent-model vllm-qwen3.5-9b --agent-mode reactive --schedule-mode calendar --schedule-seed 0 --no-clean --replay-scene-interval 20 --metric-log-interval 10
```

```bash
VLLM_MODEL=qwen35-9b VLLM_BASE_URL=http://127.0.0.1:8000/v1 /home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py --scene simple_home_1f --steps 1600 --only with_robot --robots 1 --humans 1 --agent-model vllm-qwen3.5-9b --agent-mode single_round --schedule-mode calendar --schedule-seed 0 --no-clean --replay-scene-interval 20 --metric-log-interval 10
```

```bash
VLLM_MODEL=qwen35-9b VLLM_BASE_URL=http://127.0.0.1:8000/v1 /home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py --scene simple_hospital_1f --steps 1600 --only with_robot --robots 1 --humans 3 --agent-model vllm-qwen3.5-9b --agent-mode reactive --schedule-mode calendar --schedule-seed 0 --no-clean --replay-scene-interval 20 --metric-log-interval 10
```

```bash
VLLM_MODEL=qwen35-9b VLLM_BASE_URL=http://127.0.0.1:8000/v1 /home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py --scene simple_hospital_1f --steps 1600 --only with_robot --robots 1 --humans 3 --agent-model vllm-qwen3.5-9b --agent-mode single_round --schedule-mode calendar --schedule-seed 0 --no-clean --replay-scene-interval 20 --metric-log-interval 10
```

```bash
VLLM_MODEL=qwen35-9b VLLM_BASE_URL=http://127.0.0.1:8000/v1 /home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py --scene simple_supermarket_1f --steps 1600 --only with_robot --robots 1 --humans 3 --agent-model vllm-qwen3.5-9b --agent-mode reactive --schedule-mode calendar --schedule-seed 0 --no-clean --replay-scene-interval 20 --metric-log-interval 10
```

```bash
VLLM_MODEL=qwen35-9b VLLM_BASE_URL=http://127.0.0.1:8000/v1 /home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py --scene simple_supermarket_1f --steps 1600 --only with_robot --robots 1 --humans 3 --agent-model vllm-qwen3.5-9b --agent-mode single_round --schedule-mode calendar --schedule-seed 0 --no-clean --replay-scene-interval 20 --metric-log-interval 10
```

```bash
VLLM_MODEL=qwen35-9b VLLM_BASE_URL=http://127.0.0.1:8000/v1 /home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py --scene simple_office_1f --steps 1600 --only with_robot --robots 1 --humans 3 --agent-model vllm-qwen3.5-9b --agent-mode reactive --schedule-mode calendar --schedule-seed 0 --no-clean --replay-scene-interval 20 --metric-log-interval 10
```

```bash
VLLM_MODEL=qwen35-9b VLLM_BASE_URL=http://127.0.0.1:8000/v1 /home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py --scene simple_office_1f --steps 1600 --only with_robot --robots 1 --humans 3 --agent-model vllm-qwen3.5-9b --agent-mode single_round --schedule-mode calendar --schedule-seed 0 --no-clean --replay-scene-interval 20 --metric-log-interval 10
```

```bash
VLLM_MODEL=qwen35-9b VLLM_BASE_URL=http://127.0.0.1:8000/v1 /home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py --scene simple_factory_1f --steps 1600 --only with_robot --robots 1 --humans 3 --agent-model vllm-qwen3.5-9b --agent-mode reactive --schedule-mode calendar --schedule-seed 0 --no-clean --replay-scene-interval 20 --metric-log-interval 10
```

```bash
VLLM_MODEL=qwen35-9b VLLM_BASE_URL=http://127.0.0.1:8000/v1 /home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py --scene simple_factory_1f --steps 1600 --only with_robot --robots 1 --humans 3 --agent-model vllm-qwen3.5-9b --agent-mode single_round --schedule-mode calendar --schedule-seed 0 --no-clean --replay-scene-interval 20 --metric-log-interval 10
```

## stochastic schedule: reactive/single_round

```bash
VLLM_MODEL=qwen35-9b VLLM_BASE_URL=http://127.0.0.1:8000/v1 /home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py --scene simple_home_1f --steps 1600 --only with_robot --robots 1 --humans 1 --agent-model vllm-qwen3.5-9b --agent-mode reactive --schedule-mode stochastic --schedule-seed 42 --no-clean --replay-scene-interval 20 --metric-log-interval 10
```

```bash
VLLM_MODEL=qwen35-9b VLLM_BASE_URL=http://127.0.0.1:8000/v1 /home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py --scene simple_home_1f --steps 1600 --only with_robot --robots 1 --humans 1 --agent-model vllm-qwen3.5-9b --agent-mode single_round --schedule-mode stochastic --schedule-seed 42 --no-clean --replay-scene-interval 20 --metric-log-interval 10
```

```bash
VLLM_MODEL=qwen35-9b VLLM_BASE_URL=http://127.0.0.1:8000/v1 /home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py --scene simple_hospital_1f --steps 1600 --only with_robot --robots 1 --humans 3 --agent-model vllm-qwen3.5-9b --agent-mode reactive --schedule-mode stochastic --schedule-seed 42 --no-clean --replay-scene-interval 20 --metric-log-interval 10
```

```bash
VLLM_MODEL=qwen35-9b VLLM_BASE_URL=http://127.0.0.1:8000/v1 /home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py --scene simple_hospital_1f --steps 1600 --only with_robot --robots 1 --humans 3 --agent-model vllm-qwen3.5-9b --agent-mode single_round --schedule-mode stochastic --schedule-seed 42 --no-clean --replay-scene-interval 20 --metric-log-interval 10
```

```bash
VLLM_MODEL=qwen35-9b VLLM_BASE_URL=http://127.0.0.1:8000/v1 /home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py --scene simple_supermarket_1f --steps 1600 --only with_robot --robots 1 --humans 3 --agent-model vllm-qwen3.5-9b --agent-mode reactive --schedule-mode stochastic --schedule-seed 42 --no-clean --replay-scene-interval 20 --metric-log-interval 10
```

```bash
VLLM_MODEL=qwen35-9b VLLM_BASE_URL=http://127.0.0.1:8000/v1 /home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py --scene simple_supermarket_1f --steps 1600 --only with_robot --robots 1 --humans 3 --agent-model vllm-qwen3.5-9b --agent-mode single_round --schedule-mode stochastic --schedule-seed 42 --no-clean --replay-scene-interval 20 --metric-log-interval 10
```

```bash
VLLM_MODEL=qwen35-9b VLLM_BASE_URL=http://127.0.0.1:8000/v1 /home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py --scene simple_office_1f --steps 1600 --only with_robot --robots 1 --humans 3 --agent-model vllm-qwen3.5-9b --agent-mode reactive --schedule-mode stochastic --schedule-seed 42 --no-clean --replay-scene-interval 20 --metric-log-interval 10
```

```bash
VLLM_MODEL=qwen35-9b VLLM_BASE_URL=http://127.0.0.1:8000/v1 /home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py --scene simple_office_1f --steps 1600 --only with_robot --robots 1 --humans 3 --agent-model vllm-qwen3.5-9b --agent-mode single_round --schedule-mode stochastic --schedule-seed 42 --no-clean --replay-scene-interval 20 --metric-log-interval 10
```

```bash
VLLM_MODEL=qwen35-9b VLLM_BASE_URL=http://127.0.0.1:8000/v1 /home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py --scene simple_factory_1f --steps 1600 --only with_robot --robots 1 --humans 3 --agent-model vllm-qwen3.5-9b --agent-mode reactive --schedule-mode stochastic --schedule-seed 42 --no-clean --replay-scene-interval 20 --metric-log-interval 10
```

```bash
VLLM_MODEL=qwen35-9b VLLM_BASE_URL=http://127.0.0.1:8000/v1 /home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py --scene simple_factory_1f --steps 1600 --only with_robot --robots 1 --humans 3 --agent-model vllm-qwen3.5-9b --agent-mode single_round --schedule-mode stochastic --schedule-seed 42 --no-clean --replay-scene-interval 20 --metric-log-interval 10
```
