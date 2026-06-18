# Validation Fixtures

Validation fixtures are the release gate before holdout. They must not reuse development fixture targets or holdout paper targets.

These fixtures are intentionally lightweight in this phase. They prove the loop has a separate validation split and can enforce holdout readiness without touching `research/source_of_truth/holdout_papers/`.

## Policy

- `data_partition` must be `validation`.
- `evaluation_only` must be `true`.
- Fixtures may use public registry metadata or separately sourced aggregate references.
- Fixtures must not be used for prompt tuning after every individual failure.
- Holdout assets remain final scorekeeping only.
