# Current Experiment Status and Remaining Runs

This file tracks the current paper experiment state. The paper now uses 800-step
runs unless explicitly marked as a 500-step diagnostic subset.

## Completed

### Qwen Main Fixed Experiment

```text
5 base scenes x (1 no-robot baseline + 3 robot methods) x 800 steps = 20 runs
methods: no_robot, reactive, single_round, goal_review
```

The no-robot fixed baseline has been rerun at 800 steps for all five base
scenes. The main curve/table now use raw no-robot metrics instead of cached
reference values.

Note: `simple_office_1f` goal-review has a valid final summary at step 799, but
the current `metrics.csv`/action log only contains the resumed segment
(`646..799`). The paper therefore uses its final cumulative summary in tables,
while curves/action profiles treat that run as partially logged.

### Qwen Profile Diversity

```text
5 base scenes x 3 profiles x 800 steps = 15 goal-review runs
profiles: compact_cleaning, normal, spread_device
```

`normal` reuses the fixed base-scene goal-review runs. The 10 additional
compact/spread runs are complete. Profile no-robot baselines have not been
rerun and are not shown in the current paper figure.

### Qwen Schedule Diversity

```text
5 base scenes x 3 schedules x 800 steps = 15 goal-review runs
schedules: fixed, calendar, stochastic
```

`fixed` reuses the fixed base-scene goal-review runs. The 10 additional
calendar/stochastic runs are complete. The fixed office goal-review condition
inherits the partial-log caveat from the main fixed experiment.

### Model Backbone Comparison

```text
2 completed backbones x 5 base scenes x 3 methods x 800 steps = 30 with-robot runs
completed backbones: Qwen3.5-9B, DeepSeek-R1-14B
incomplete backbone: Llama-3.1-8B
methods: reactive, single_round, goal_review
```

Qwen and DeepSeek are complete and the model comparison figure has been
regenerated from complete 800-step raw summaries. Llama-3.1-8B currently has 15
run directories, but all are short runs and do not reach step 799, so they are
excluded from the formal paper figure/table until rerun or resumed to 800 steps.

### Human Blocking Recovery Diagnostic

```text
5 base scenes x 3 methods x 500 steps = 15 with-robot diagnostic runs
methods: reactive, single_round, goal_review
```

This is a separate fixed-schedule diagnostic subset and should not be mixed
with the 800-step main score tables.

## Remaining Before Final Submission

### Required To Include Llama In Model Comparison

```text
5 base scenes x 3 methods x 800 steps = 15 Llama-3.1-8B runs
```

Purpose: replace the current short Llama runs with complete 800-step summaries
so that Llama can be added back into the model-backbone comparison.

### Optional if We Want Profile Baseline Curves

```text
5 base scenes x 3 profiles x 1 no-robot baseline x 800 steps = 15 runs
```

Purpose: add no-robot curves back into the profile diversity figure. The current
paper intentionally shows only goal-review across profiles because these raw
profile baselines are not present in the current workspace.
