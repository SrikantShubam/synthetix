# Pipeline Predicted Metrics Spec

## Purpose

Make actual-vs-predicted benchmark comparison automatic by having the pipeline emit predicted metric payloads.

## Required Behavior

- For each benchmark fixture, emit `data/benchmark-predictions/<split>/<fixture_filename>.json`.
- Payloads contain `fixture_id` and `predicted_metrics`.
- Use the existing benchmark comparator to produce per-fixture reports and split summaries.
- Development comparison must run without hand-authored prediction JSON.

## Acceptance Criteria

- Development fixtures can produce prediction payloads automatically.
- `benchmark-compare-development` can score the generated payloads.
- Missing predicted metrics fail loudly.
- Generated payloads do not read from or tune against holdout assets.

## Agent Allocation

- Assigned model: `gpt-5.4-mini`
- Reason: bounded data-contract and CLI plumbing work.
