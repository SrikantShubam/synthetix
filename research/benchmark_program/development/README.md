# Development Fixtures

These fixtures are for development-time iteration only.

## Hard rule

They must not reuse the exact holdout papers, exact holdout questionnaires, or exact holdout reported-result targets from:

- `research/source_of_truth/holdout_papers/ai_persona/`
- `research/source_of_truth/holdout_papers/survey_benchmarks/`

They may be inspired by the same problem classes, but they must come from different sources, different tasks, or different target outputs.

## Required fields

- `fixture_id`
- `data_partition`
- `evaluation_only`
- `training_allowed`
- `source_strategy`
- `forbidden_source_refs`
- `population_definition`
- `questionnaire_or_task`
- `segment_variables`
- `reported_findings_template`
- `comparison_metric`
- `actual_targets`

## Policy

- `data_partition` must be `development`
- `evaluation_only` must be `false`
- `training_allowed` may be `true` only for prompt and fixture design work outside the locked holdout path
- no fixture here may point at a file under `research/source_of_truth/holdout_papers/`
- `actual_targets` are the locked quantitative reference values used for actual-vs-predicted comparison
