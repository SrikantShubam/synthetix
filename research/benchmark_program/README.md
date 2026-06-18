# Benchmark Program

This directory defines the benchmark split policy for Synthetix.

## Recommended workflow

Use three splits:

1. `development`
   Purpose: build ingestion fixtures, prompt templates, scoring logic, and report contracts.
   Allowed: debugging, fixture authoring, analysis development, prompt iteration.
   Forbidden: final claims about generalization.

2. `validation`
   Purpose: gated iteration during development.
   Allowed: score candidate changes before release.
   Forbidden: repeated manual optimization on individual examples after every failure.

3. `holdout`
   Purpose: final scorekeeping only.
   Allowed: final benchmark runs, comparison tables, release evidence.
   Forbidden: training, prompt tuning, few-shot examples, benchmark-driven iteration on the same assets.

## Decision

The current `research/source_of_truth/holdout_papers/` set remains locked as `holdout`.

Do not run the self-improvement loop against it yet.

First create:

- `research/benchmark_program/development/`
- `research/benchmark_program/validation/`

These should be populated with benchmark fixtures derived from separate sources or separate non-overlapping tasks. They may be inspired by the holdout papers, but they cannot reuse the same exact question/result targets as optimization material.

## Immediate next step

Populate `development` with 5-10 benchmark fixtures that are structurally similar but not identical to the holdout set:

- privacy-decision survey replication fixture
- consumer-choice distributional replication fixture
- attitude/values survey fixture
- binary plus open-text mixed questionnaire fixture
- subgroup-comparison fixture

Then populate `validation` with 2-4 additional fixtures from different sources.

Only after the system is stable on `development` and `validation` should it be evaluated on the locked `holdout`.

## Actual vs predicted workflow

Development fixtures now contain locked `actual_targets`. The pipeline should emit one predicted payload per fixture into:

- `data/benchmark-predictions/development/<fixture_filename>.json`

Predicted payload shape:

```json
{
  "fixture_id": "dev_privacy_decision_replication_v1",
  "predicted_metrics": [
    {"metric_id": "human_accuracy", "value": 0.81},
    {"metric_id": "best_model_accuracy", "value": 0.59}
  ]
}
```

Compare one fixture:

```bash
synthetix benchmark-compare research/benchmark_program/development/privacy_decision_replication_v1.json data/benchmark-predictions/development/privacy_decision_replication_v1.json --output data/benchmark-results/development/privacy_decision_replication_v1.json
```

Compare the full development split:

```bash
synthetix benchmark-compare-development --fixtures research/benchmark_program/development --predicted-dir data/benchmark-predictions/development --output-dir data/benchmark-results/development
```

This produces:

- one report per fixture in `data/benchmark-results/development/`
- `data/benchmark-results/development/summary.json`

The persistent task loop advances to `compare_development_predictions` after the benchmark runtime is implemented and before validation runs begin.
