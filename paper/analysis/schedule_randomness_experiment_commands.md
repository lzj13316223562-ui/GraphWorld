# Schedule Diversity Experiment Commands

Current paper setting:

```text
Qwen3.5-9B goal-review
5 base scenes x 3 schedules x 800 steps
```

The fixed schedule runs are reused from the Qwen fixed main experiment. The
additional schedule diversity runs are therefore:

```text
5 scenes x 2 schedules(calendar, stochastic) = 10 runs
```

All current runs use `--schedule-seed 0`.

## Calendar

```bash
VLLM_MODEL=qwen3.5-9b VLLM_BASE_URL=http://127.0.0.1:8000/v1 /home/swzz/anaconda3/gra/bin/python backend/run_experiment.py --scene simple_home_1f --steps 800 --only with_robot --robots 1 --humans 1 --agent-model vllm-qwen3.5-9b --agent-mode goal_review --schedule-mode calendar --schedule-seed 0 --no-clean --replay-scene-interval 20 --metric-log-interval 10
```

```bash
VLLM_MODEL=qwen3.5-9b VLLM_BASE_URL=http://127.0.0.1:8000/v1 /home/swzz/anaconda3/gra/bin/python backend/run_experiment.py --scene simple_hospital_1f --steps 800 --only with_robot --robots 1 --humans 3 --agent-model vllm-qwen3.5-9b --agent-mode goal_review --schedule-mode calendar --schedule-seed 0 --no-clean --replay-scene-interval 20 --metric-log-interval 10
```

```bash
VLLM_MODEL=qwen3.5-9b VLLM_BASE_URL=http://127.0.0.1:8000/v1 /home/swzz/anaconda3/gra/bin/python backend/run_experiment.py --scene simple_office_1f --steps 800 --only with_robot --robots 1 --humans 3 --agent-model vllm-qwen3.5-9b --agent-mode goal_review --schedule-mode calendar --schedule-seed 0 --no-clean --replay-scene-interval 20 --metric-log-interval 10
```

```bash
VLLM_MODEL=qwen3.5-9b VLLM_BASE_URL=http://127.0.0.1:8000/v1 /home/swzz/anaconda3/gra/bin/python backend/run_experiment.py --scene simple_supermarket_1f --steps 800 --only with_robot --robots 1 --humans 3 --agent-model vllm-qwen3.5-9b --agent-mode goal_review --schedule-mode calendar --schedule-seed 0 --no-clean --replay-scene-interval 20 --metric-log-interval 10
```

```bash
VLLM_MODEL=qwen3.5-9b VLLM_BASE_URL=http://127.0.0.1:8000/v1 /home/swzz/anaconda3/gra/bin/python backend/run_experiment.py --scene simple_factory_1f --steps 800 --only with_robot --robots 1 --humans 3 --agent-model vllm-qwen3.5-9b --agent-mode goal_review --schedule-mode calendar --schedule-seed 0 --no-clean --replay-scene-interval 20 --metric-log-interval 10
```

## Stochastic

```bash
VLLM_MODEL=qwen3.5-9b VLLM_BASE_URL=http://127.0.0.1:8000/v1 /home/swzz/anaconda3/gra/bin/python backend/run_experiment.py --scene simple_home_1f --steps 800 --only with_robot --robots 1 --humans 1 --agent-model vllm-qwen3.5-9b --agent-mode goal_review --schedule-mode stochastic --schedule-seed 0 --no-clean --replay-scene-interval 20 --metric-log-interval 10
```

```bash
VLLM_MODEL=qwen3.5-9b VLLM_BASE_URL=http://127.0.0.1:8000/v1 /home/swzz/anaconda3/gra/bin/python backend/run_experiment.py --scene simple_hospital_1f --steps 800 --only with_robot --robots 1 --humans 3 --agent-model vllm-qwen3.5-9b --agent-mode goal_review --schedule-mode stochastic --schedule-seed 0 --no-clean --replay-scene-interval 20 --metric-log-interval 10
```

```bash
VLLM_MODEL=qwen3.5-9b VLLM_BASE_URL=http://127.0.0.1:8000/v1 /home/swzz/anaconda3/gra/bin/python backend/run_experiment.py --scene simple_office_1f --steps 800 --only with_robot --robots 1 --humans 3 --agent-model vllm-qwen3.5-9b --agent-mode goal_review --schedule-mode stochastic --schedule-seed 0 --no-clean --replay-scene-interval 20 --metric-log-interval 10
```

```bash
VLLM_MODEL=qwen3.5-9b VLLM_BASE_URL=http://127.0.0.1:8000/v1 /home/swzz/anaconda3/gra/bin/python backend/run_experiment.py --scene simple_supermarket_1f --steps 800 --only with_robot --robots 1 --humans 3 --agent-model vllm-qwen3.5-9b --agent-mode goal_review --schedule-mode stochastic --schedule-seed 0 --no-clean --replay-scene-interval 20 --metric-log-interval 10
```

```bash
VLLM_MODEL=qwen3.5-9b VLLM_BASE_URL=http://127.0.0.1:8000/v1 /home/swzz/anaconda3/gra/bin/python backend/run_experiment.py --scene simple_factory_1f --steps 800 --only with_robot --robots 1 --humans 3 --agent-model vllm-qwen3.5-9b --agent-mode goal_review --schedule-mode stochastic --schedule-seed 0 --no-clean --replay-scene-interval 20 --metric-log-interval 10
```
