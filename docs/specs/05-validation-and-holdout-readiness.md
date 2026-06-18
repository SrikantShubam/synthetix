# Validation And Holdout Readiness Spec

## Purpose

Prevent premature holdout use and define the evidence required before external performance claims.

## Required Behavior

- Create validation fixtures from sources distinct from development and holdout.
- Require development and validation evidence before holdout evaluation.
- Freeze the system version before holdout execution.
- Treat holdout results as final scorekeeping, not tuning input.

## Acceptance Criteria

- Validation fixtures exist before holdout readiness can be marked complete.
- Holdout evaluation is blocked until development and validation summaries exist.
- Loop state records the frozen system version before holdout approval.
- Holdout assets remain forbidden for training, prompt tuning, few-shot examples, and self-improvement.

## Agent Allocation

- Assigned model: `gpt-5.4`
- Reason: holdout governance and release evidence require high judgment.
