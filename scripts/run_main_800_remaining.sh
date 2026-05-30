#!/usr/bin/env bash
set -euo pipefail

cd /home/swzz/data/GraphWorld

PYTHON_BIN="${PYTHON_BIN:-/home/swzz/anaconda3/gra/bin/python}"
STEPS="${STEPS:-800}"
AGENT_MODEL="${AGENT_MODEL:-vllm-qwen3.5-9b}"
VLLM_BASE_URL="${VLLM_BASE_URL:-http://127.0.0.1:8000/v1}"
VLLM_MODEL="${VLLM_MODEL:-qwen3.5-9b}"

export PYTHONUNBUFFERED=1
export MPLCONFIGDIR="${MPLCONFIGDIR:-/tmp/matplotlib-graphworld}"

SCENES=(
  simple_supermarket_1f:3
  simple_office_1f:3
  simple_factory_1f:3
)

AGENT_MODES=(
  reactive
  single_round
  goal_review
)

run_no_robot() {
  local scene="$1"
  local humans="$2"

  echo "===== $(date -Is) no_robot ${scene} humans=${humans} ====="
  "$PYTHON_BIN" backend/run_experiment.py \
    --scene "$scene" \
    --steps "$STEPS" \
    --only no_robot \
    --robots 0 \
    --humans "$humans" \
    --no-clean \
    --replay-scene-interval 20 \
    --metric-log-interval 20
}

run_agent() {
  local scene="$1"
  local humans="$2"
  local mode="$3"

  echo "===== $(date -Is) with_robot ${scene} mode=${mode} humans=${humans} ====="
  VLLM_MODEL="$VLLM_MODEL" \
  VLLM_BASE_URL="$VLLM_BASE_URL" \
  "$PYTHON_BIN" backend/run_experiment.py \
    --scene "$scene" \
    --steps "$STEPS" \
    --only with_robot \
    --robots 1 \
    --humans "$humans" \
    --agent-model "$AGENT_MODEL" \
    --agent-mode "$mode" \
    --no-clean \
    --replay-scene-interval 20 \
    --metric-log-interval 10
}

echo "===== resume unfinished main-800 batch $(date -Is) ====="
for item in "${SCENES[@]}"; do
  scene="${item%%:*}"
  humans="${item##*:}"
  run_no_robot "$scene" "$humans"
  for mode in "${AGENT_MODES[@]}"; do
    run_agent "$scene" "$humans" "$mode"
  done
done
echo "===== finished resume batch $(date -Is) ====="
