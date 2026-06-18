# Agent Orchestrator Loop Spec

## Purpose

Create a gated autonomous loop that assigns work to GPT-5.4 or GPT-5.4-mini agents, reviews outputs, runs checks, and records state.

## Required Behavior

- Read `goals.md` and all `docs/specs/*.md`.
- Select the next incomplete spec based on the fixed dependency order.
- Generate task packets containing `spec_id`, `task_id`, `assigned_model`, `allowed_paths`, `forbidden_paths`, `acceptance_checks`, `status`, `review_notes`, and `artifact_paths`.
- Reject changes that contaminate holdout data, weaken guardrails, fail checks, or skip required artifacts.
- Persist state to `data/orchestrator-loop-state.json`.

## Acceptance Criteria

- Loop can show the next task.
- Loop records failed verification without advancing.
- Loop records passed verification and advances.
- GPT-5.4-mini cannot own benchmark policy, product positioning, professional report design, holdout governance, or final review tasks.
- Holdout paths are rejected unless the active spec is holdout-readiness.

## Agent Allocation

- Assigned model: `gpt-5.4`
- Reason: orchestration, review, and policy enforcement require high judgment.
