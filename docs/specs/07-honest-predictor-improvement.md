# Honest Predictor Improvement

## Purpose

Improve benchmark prediction quality under the anti-leakage constraints without reading answer keys or proxy target fields.

## Required Behavior

- Predictions must run without `actual_targets` or equivalent answer-bearing structures.
- Prediction-time code must not read `human_reference_summary`, `calibration_clues`, `registry_summary`, or equivalent proxy fields.
- Improvements must come from legitimate predictor logic, aggregation, feature extraction, or prompt/protocol design that does not consume evaluation answers.
- Any suspicious score jump requires explicit leakage review before the result may be treated as valid evidence.
- Development and validation reruns after predictor changes must be reported as the new valid baseline even if scores remain materially below prior contaminated results.

## Acceptance Criteria

- Targeted predictor tests cover absence of answer keys and forbidden proxy fields.
- Honest development benchmark rerun is produced after predictor changes.
- Honest validation benchmark rerun is produced after predictor changes.
- Leakage review notes are recorded whenever score movement is unusually large.

## Agent Allocation

- Assigned model: `gpt-5.4`
- Reason: leakage-sensitive benchmark changes require policy judgment and explicit scientific conservatism.
