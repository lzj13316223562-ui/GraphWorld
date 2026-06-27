#!/usr/bin/env bash
set -euo pipefail

cd /home/swzz/data/GraphWorld

unset HTTP_PROXY HTTPS_PROXY ALL_PROXY http_proxy https_proxy all_proxy

PYTHON_BIN="${PYTHON_BIN:-/home/swzz/anaconda3/gra/bin/python}"
STEPS="${STEPS:-800}"
AGENT_MODEL="${AGENT_MODEL:-claude-opus-4.8}"
ANTHROPIC_BASE_URL="${ANTHROPIC_BASE_URL:-https://sub.100xlabs.space}"
ANTHROPIC_MODEL="${ANTHROPIC_MODEL:-claude-opus-4.8}"
RUN_NO_ROBOT="${RUN_NO_ROBOT:-1}"
RUN_AGENTS="${RUN_AGENTS:-1}"
SCHEDULES_CSV="${SCHEDULES_CSV:-fixed calendar stochastic}"
read -r -a SCHEDULES <<< "$SCHEDULES_CSV"

if [[ "$RUN_AGENTS" == "1" && -z "${ANTHROPIC_AUTH_TOKEN:-}" ]]; then
  echo "Missing ANTHROPIC_AUTH_TOKEN. Export it before running Claude agent runs." >&2
  exit 2
fi

export PYTHONUNBUFFERED=1
export MPLCONFIGDIR="${MPLCONFIGDIR:-/tmp/matplotlib-graphworld}"
export ANTHROPIC_BASE_URL
export ANTHROPIC_MODEL
export CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC="${CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC:-1}"
export CLAUDE_CODE_ATTRIBUTION_HEADER="${CLAUDE_CODE_ATTRIBUTION_HEADER:-0}"
export NO_PROXY="${NO_PROXY:-127.0.0.1,localhost}"
export no_proxy="${no_proxy:-127.0.0.1,localhost}"

SCENES=(
  simple_home_1f:1
  simple_hospital_1f:3
  simple_supermarket_1f:3
  simple_office_1f:3
  simple_factory_1f:3
)

AGENT_MODES=(
  reactive
  single_round
  goal_review
)

schedule_seed() {
  local schedule="$1"
  if [[ "$schedule" == "stochastic" ]]; then
    echo 42
  else
    echo 0
  fi
}

run_no_robot() {
  local scene="$1"
  local humans="$2"
  local schedule="$3"
  local seed="$4"

  echo "===== $(date -Is) no_robot ${scene} schedule=${schedule} seed=${seed} humans=${humans} ====="
  "$PYTHON_BIN" backend/run_experiment.py \
    --scene "$scene" \
    --steps "$STEPS" \
    --only no_robot \
    --robots 0 \
    --humans "$humans" \
    --agent-model "$AGENT_MODEL" \
    --schedule-mode "$schedule" \
    --schedule-seed "$seed" \
    --no-clean \
    --replay-scene-interval 20 \
    --metric-log-interval 20
}

run_agent() {
  local scene="$1"
  local humans="$2"
  local schedule="$3"
  local seed="$4"
  local mode="$5"

  echo "===== $(date -Is) with_robot ${scene} mode=${mode} schedule=${schedule} seed=${seed} humans=${humans} ====="
  ANTHROPIC_MODEL="$ANTHROPIC_MODEL" \
  ANTHROPIC_BASE_URL="$ANTHROPIC_BASE_URL" \
  "$PYTHON_BIN" backend/run_experiment.py \
    --scene "$scene" \
    --steps "$STEPS" \
    --only with_robot \
    --robots 1 \
    --humans "$humans" \
    --agent-model "$AGENT_MODEL" \
    --agent-mode "$mode" \
    --schedule-mode "$schedule" \
    --schedule-seed "$seed" \
    --no-clean \
    --replay-scene-interval 20 \
    --metric-log-interval 10
}

echo "GraphWorld Claude Opus 4.8 800-step grid: steps=${STEPS}, schedules=${SCHEDULES_CSV}, agent_model=${AGENT_MODEL}, anthropic_model=${ANTHROPIC_MODEL}"

for item in "${SCENES[@]}"; do
  scene="${item%%:*}"
  humans="${item##*:}"

  for schedule in "${SCHEDULES[@]}"; do
    seed="$(schedule_seed "$schedule")"

    if [[ "$RUN_NO_ROBOT" == "1" ]]; then
      run_no_robot "$scene" "$humans" "$schedule" "$seed"
    fi

    if [[ "$RUN_AGENTS" == "1" ]]; then
      for mode in "${AGENT_MODES[@]}"; do
        run_agent "$scene" "$humans" "$schedule" "$seed" "$mode"
      done
    fi
  done
done

echo "===== finished claude opus 4.8 800-step grid $(date -Is) ====="
