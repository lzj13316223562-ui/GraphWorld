#!/usr/bin/env bash
set -euo pipefail

cd /home/swzz/data/GraphWorld

SCHEDULES_CSV="${SCHEDULES_CSV:-calendar stochastic}" \
  bash scripts/run_main_800_llama31.sh "$@"
