# Benchmark Thresholds Spec

## Purpose

Classify each survey simulation into a benchmark family and attach published threshold evidence when available.

## Required Behavior

- Supported benchmark families: privacy decisions, values surveys, consumer choice, subgroup comparison, social reactions, and mixed open-text surveys.
- Each supported run receives threshold metadata from the benchmark registry.
- Unsupported domains are marked `not_benchmarkable`; the system must not invent confidence.
- Outputs use one of: `passes_threshold`, `near_threshold`, `below_threshold`, `not_benchmarkable`.

## Ground-Truth Policy

Holdout papers are evaluation-only. They cannot be used for training, prompt tuning, few-shot examples, model selection on the same set, or self-improvement against holdout targets.

## Acceptance Criteria

- Classifier behavior is deterministic for known benchmark families.
- Unsupported surveys do not receive fake thresholds.
- Holdout paths are rejected by implementation tasks unless the task is explicitly holdout-readiness review.

## Agent Allocation

- Assigned model: `gpt-5.4`
- Reason: benchmark policy, scientific claims, and holdout boundaries require high judgment.
