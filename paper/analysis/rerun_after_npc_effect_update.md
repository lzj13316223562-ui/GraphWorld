# NPC Effect 更新后的重跑命令

NPC event effect 更新后，世界动态和 no_robot baseline 都变了。旧的 agent 曲线不要和新 baseline 混用。

核心 base-scene 对比需要：

```text
5 scenes x (no_robot + reactive + single_round + goal_review) = 20 runs
```

其中 5 个 `no_robot` 已经重跑过。现在主要补下面 15 个机器人实验。

## 断网后的续跑命令

下面这些是当前已经中断、可以继续的 15 个 run。每条命令可以单独开一个终端跑。

### resume goal_review

```bash
cd /home/jansen/GraphWorld

VLLM_MODEL=qwen35-9b VLLM_BASE_URL=http://127.0.0.1:8000/v1 /home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py --resume --resume-run 20260514T141430Z_1a293e95 --no-clean
VLLM_MODEL=qwen35-9b VLLM_BASE_URL=http://127.0.0.1:8000/v1 /home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py --resume --resume-run 20260514T141434Z_fbd9c1d6 --no-clean
VLLM_MODEL=qwen35-9b VLLM_BASE_URL=http://127.0.0.1:8000/v1 /home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py --resume --resume-run 20260514T141440Z_4615b176 --no-clean
VLLM_MODEL=qwen35-9b VLLM_BASE_URL=http://127.0.0.1:8000/v1 /home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py --resume --resume-run 20260514T141445Z_fa90d1ea --no-clean
VLLM_MODEL=qwen35-9b VLLM_BASE_URL=http://127.0.0.1:8000/v1 /home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py --resume --resume-run 20260514T141449Z_f8261eaa --no-clean
```

### resume single_round

```bash
cd /home/jansen/GraphWorld

VLLM_MODEL=qwen35-9b VLLM_BASE_URL=http://127.0.0.1:8000/v1 /home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py --resume --resume-run 20260514T141401Z_3bea66ca --no-clean
VLLM_MODEL=qwen35-9b VLLM_BASE_URL=http://127.0.0.1:8000/v1 /home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py --resume --resume-run 20260514T141406Z_1cb20a62 --no-clean
VLLM_MODEL=qwen35-9b VLLM_BASE_URL=http://127.0.0.1:8000/v1 /home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py --resume --resume-run 20260514T141411Z_6b63bdb7 --no-clean
VLLM_MODEL=qwen35-9b VLLM_BASE_URL=http://127.0.0.1:8000/v1 /home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py --resume --resume-run 20260514T141416Z_a80c3f0e --no-clean
VLLM_MODEL=qwen35-9b VLLM_BASE_URL=http://127.0.0.1:8000/v1 /home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py --resume --resume-run 20260514T141424Z_440782d8 --no-clean
```

### resume reactive

```bash
cd /home/jansen/GraphWorld

VLLM_MODEL=qwen35-9b VLLM_BASE_URL=http://127.0.0.1:8000/v1 /home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py --resume --resume-run 20260514T141336Z_5515846a --no-clean
VLLM_MODEL=qwen35-9b VLLM_BASE_URL=http://127.0.0.1:8000/v1 /home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py --resume --resume-run 20260514T141338Z_63dc644b --no-clean
VLLM_MODEL=qwen35-9b VLLM_BASE_URL=http://127.0.0.1:8000/v1 /home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py --resume --resume-run 20260514T141344Z_f095baaf --no-clean
VLLM_MODEL=qwen35-9b VLLM_BASE_URL=http://127.0.0.1:8000/v1 /home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py --resume --resume-run 20260514T141349Z_b5645817 --no-clean
VLLM_MODEL=qwen35-9b VLLM_BASE_URL=http://127.0.0.1:8000/v1 /home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py --resume --resume-run 20260514T141355Z_ace74ae6 --no-clean
```

## reactive

```bash
cd /home/jansen/GraphWorld

VLLM_MODEL=qwen35-9b VLLM_BASE_URL=http://127.0.0.1:8000/v1 /home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py --scene simple_home_1f --steps 1600 --only with_robot --robots 1 --humans 1 --agent-model vllm-qwen3.5-9b --agent-mode reactive --no-clean --replay-scene-interval 20 --metric-log-interval 10
VLLM_MODEL=qwen35-9b VLLM_BASE_URL=http://127.0.0.1:8000/v1 /home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py --scene simple_hospital_1f --steps 1600 --only with_robot --robots 1 --humans 3 --agent-model vllm-qwen3.5-9b --agent-mode reactive --no-clean --replay-scene-interval 20 --metric-log-interval 10
VLLM_MODEL=qwen35-9b VLLM_BASE_URL=http://127.0.0.1:8000/v1 /home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py --scene simple_supermarket_1f --steps 1600 --only with_robot --robots 1 --humans 3 --agent-model vllm-qwen3.5-9b --agent-mode reactive --no-clean --replay-scene-interval 20 --metric-log-interval 10
VLLM_MODEL=qwen35-9b VLLM_BASE_URL=http://127.0.0.1:8000/v1 /home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py --scene simple_office_1f --steps 1600 --only with_robot --robots 1 --humans 3 --agent-model vllm-qwen3.5-9b --agent-mode reactive --no-clean --replay-scene-interval 20 --metric-log-interval 10
VLLM_MODEL=qwen35-9b VLLM_BASE_URL=http://127.0.0.1:8000/v1 /home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py --scene simple_factory_1f --steps 1600 --only with_robot --robots 1 --humans 3 --agent-model vllm-qwen3.5-9b --agent-mode reactive --no-clean --replay-scene-interval 20 --metric-log-interval 10
```

## single_round

```bash
cd /home/jansen/GraphWorld

VLLM_MODEL=qwen35-9b VLLM_BASE_URL=http://127.0.0.1:8000/v1 /home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py --scene simple_home_1f --steps 1600 --only with_robot --robots 1 --humans 1 --agent-model vllm-qwen3.5-9b --agent-mode single_round --no-clean --replay-scene-interval 20 --metric-log-interval 10
VLLM_MODEL=qwen35-9b VLLM_BASE_URL=http://127.0.0.1:8000/v1 /home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py --scene simple_hospital_1f --steps 1600 --only with_robot --robots 1 --humans 3 --agent-model vllm-qwen3.5-9b --agent-mode single_round --no-clean --replay-scene-interval 20 --metric-log-interval 10
VLLM_MODEL=qwen35-9b VLLM_BASE_URL=http://127.0.0.1:8000/v1 /home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py --scene simple_supermarket_1f --steps 1600 --only with_robot --robots 1 --humans 3 --agent-model vllm-qwen3.5-9b --agent-mode single_round --no-clean --replay-scene-interval 20 --metric-log-interval 10
VLLM_MODEL=qwen35-9b VLLM_BASE_URL=http://127.0.0.1:8000/v1 /home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py --scene simple_office_1f --steps 1600 --only with_robot --robots 1 --humans 3 --agent-model vllm-qwen3.5-9b --agent-mode single_round --no-clean --replay-scene-interval 20 --metric-log-interval 10
VLLM_MODEL=qwen35-9b VLLM_BASE_URL=http://127.0.0.1:8000/v1 /home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py --scene simple_factory_1f --steps 1600 --only with_robot --robots 1 --humans 3 --agent-model vllm-qwen3.5-9b --agent-mode single_round --no-clean --replay-scene-interval 20 --metric-log-interval 10
```

## goal_review

```bash
cd /home/jansen/GraphWorld

VLLM_MODEL=qwen35-9b VLLM_BASE_URL=http://127.0.0.1:8000/v1 /home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py --scene simple_home_1f --steps 1600 --only with_robot --robots 1 --humans 1 --agent-model vllm-qwen3.5-9b --agent-mode goal_review --no-clean --replay-scene-interval 20 --metric-log-interval 10
VLLM_MODEL=qwen35-9b VLLM_BASE_URL=http://127.0.0.1:8000/v1 /home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py --scene simple_hospital_1f --steps 1600 --only with_robot --robots 1 --humans 3 --agent-model vllm-qwen3.5-9b --agent-mode goal_review --no-clean --replay-scene-interval 20 --metric-log-interval 10
VLLM_MODEL=qwen35-9b VLLM_BASE_URL=http://127.0.0.1:8000/v1 /home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py --scene simple_supermarket_1f --steps 1600 --only with_robot --robots 1 --humans 3 --agent-model vllm-qwen3.5-9b --agent-mode goal_review --no-clean --replay-scene-interval 20 --metric-log-interval 10
VLLM_MODEL=qwen35-9b VLLM_BASE_URL=http://127.0.0.1:8000/v1 /home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py --scene simple_office_1f --steps 1600 --only with_robot --robots 1 --humans 3 --agent-model vllm-qwen3.5-9b --agent-mode goal_review --no-clean --replay-scene-interval 20 --metric-log-interval 10
VLLM_MODEL=qwen35-9b VLLM_BASE_URL=http://127.0.0.1:8000/v1 /home/jansen/miniconda3/envs/gra/bin/python backend/run_experiment.py --scene simple_factory_1f --steps 1600 --only with_robot --robots 1 --humans 3 --agent-model vllm-qwen3.5-9b --agent-mode goal_review --no-clean --replay-scene-interval 20 --metric-log-interval 10
```

## 如果 variant 也要重跑

如果要把 graph variant 那组也同步更新，还要额外补：

```text
5 scenes x 3 graph profiles x no_robot = 15 runs
5 scenes x 3 graph profiles x goal_review = 15 runs
```

base-scene 主图优先跑上面 15 个机器人实验。
