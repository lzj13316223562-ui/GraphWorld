# Experiment Coverage Audit

This file tracks experiment coverage for the paper. The paper uses 800-step
runs unless explicitly marked as a 500-step diagnostic subset. No required
experiment matrix is missing for the figures and tables listed below.

## Covered Matrices

### Qwen Main Fixed Experiment

```text
5 base scenes x (1 no-robot baseline + 3 robot methods) x 800 steps = 20 runs
methods: no_robot, reactive, single_round, goal_review
```

The no-robot fixed baseline has been rerun at 800 steps for all five base
scenes. The main curve/table now use raw no-robot metrics instead of cached
reference values. All Qwen fixed main metrics used by the paper cover steps
0..799.

### Qwen Profile Diversity

```text
5 base scenes x 3 profiles x 800 steps = 15 goal-review runs
5 base scenes x 3 profiles x 800 steps = 15 no-robot baseline curves
profiles: compact_cleaning, normal, spread_device
```

`normal` reuses the fixed base-scene goal-review runs. The 10 additional
compact/spread goal-review runs are complete. The profile no-robot baselines
are also complete: `normal` reuses the fixed base-scene no-robot runs, and the
10 compact/spread no-robot runs were rerun at 800 steps. The current profile
diversity figure shows goal-review as solid lines and no-robot as dashed lines.

### Qwen Schedule Diversity

```text
5 base scenes x 3 schedules x 800 steps = 15 goal-review runs
schedules: fixed, calendar, stochastic
```

`fixed` reuses the fixed base-scene goal-review runs. The 10 additional
calendar/stochastic runs are complete. All schedule curves used by the paper
cover steps 0..799.

### Model Backbone Comparison

```text
3 completed backbones x 5 base scenes x 3 methods x 800 steps = 45 with-robot runs
completed backbones: Qwen3.5-9B, DeepSeek-R1-14B, Llama-3.1-8B
methods: reactive, single_round, goal_review
```

Qwen, DeepSeek and Llama are complete and the model comparison figure has been
regenerated from complete 800-step raw summaries.

### Human Blocking Recovery Diagnostic

```text
5 base scenes x 3 methods x 500 steps = 15 with-robot diagnostic runs
methods: reactive, single_round, goal_review
```

This is a separate fixed-schedule diagnostic subset and should not be mixed
with the 800-step main score tables.

## Required Additional Runs

None for the paper figures tracked in this file.
