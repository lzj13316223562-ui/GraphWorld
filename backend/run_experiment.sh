#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${PYTHON_BIN:-}" ]]; then
  if [[ "${CONDA_DEFAULT_ENV:-}" == "gra" && -n "${CONDA_PREFIX:-}" && -x "${CONDA_PREFIX}/bin/python" ]]; then
    PYTHON_BIN="${CONDA_PREFIX}/bin/python"
  elif [[ -x "/home/swzz/anaconda3/gra/bin/python" ]]; then
    PYTHON_BIN="/home/swzz/anaconda3/gra/bin/python"
  elif [[ -n "${CONDA_PREFIX:-}" && -x "${CONDA_PREFIX}/bin/python" ]]; then
    PYTHON_BIN="${CONDA_PREFIX}/bin/python"
  else
    PYTHON_BIN="$(command -v python)"
  fi
fi
STEPS="${STEPS:-100}"
AGENT_MODEL="${AGENT_MODEL:-vllm-qwen3.5-4b}"
ROBOTS="${ROBOTS:-1}"
HUMANS="${HUMANS:-1}"
ONLY="${ONLY:-both}"
LLM="${LLM:-0}"
CLEAN="${CLEAN:-0}"
MATRIX_VIZ="${MATRIX_VIZ:-0}"
REPLAY_SCENE_INTERVAL="${REPLAY_SCENE_INTERVAL:-100}"
METRIC_LOG_INTERVAL="${METRIC_LOG_INTERVAL:-1}"

args=(
  "$(dirname "$0")/run_experiment.py"
  --steps "$STEPS"
  --agent-model "$AGENT_MODEL"
  --robots "$ROBOTS"
  --humans "$HUMANS"
  --only "$ONLY"
  --replay-scene-interval "$REPLAY_SCENE_INTERVAL"
  --metric-log-interval "$METRIC_LOG_INTERVAL"
)

if [[ "$LLM" != "1" ]]; then
  args+=(--no-llm)
fi

if [[ "$CLEAN" != "1" ]]; then
  args+=(--no-clean)
fi

if [[ "$MATRIX_VIZ" == "1" ]]; then
  args+=(--matrix-viz)
fi

exec "$PYTHON_BIN" "${args[@]}"
