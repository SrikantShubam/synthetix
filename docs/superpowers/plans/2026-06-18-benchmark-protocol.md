# Benchmark Protocol Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a contamination-safe benchmark protocol that fixes deterministic registry-policy predictions, defines locked holdout target fixtures, and records evaluation cycles honestly.

**Architecture:** Keep the existing benchmark comparator and frozen evaluator. Add a deterministic registry metric emitter used before generic prediction fallbacks, a holdout fixture contract, and cycle metadata in frozen manifests and quality summaries.

**Tech Stack:** Python 3.12, Pydantic 2, Typer CLI, pytest, Ruff, mypy.

---

### Task 1: Deterministic Registry Metrics

**Files:**
- Create: `src/synthetix/benchmarking/metrics.py`
- Modify: `src/synthetix/benchmarking/predictions.py`
- Test: `tests/unit/test_registry_metrics.py`

- [ ] Write tests proving registry metadata computes exact policy counts without reading `actual_targets`.
- [ ] Add `RegistryPolicyMetricEmitter` with support for registry entry, restricted, public, download-permitted, and registration-required counts.
- [ ] Route prediction generation through the emitter before neutral fallback.
- [ ] Run focused tests.

### Task 2: Holdout Fixture Contract

**Files:**
- Create: `src/synthetix/benchmarking/fixtures.py`
- Test: `tests/unit/test_holdout_fixtures.py`

- [ ] Write tests for accepted and rejected locked holdout fixture payloads.
- [ ] Add `HoldoutTargetFixture` and `SourceReference` Pydantic contracts.
- [ ] Require source paper hash, extraction notes, actual targets, and `evaluation_only=true`.
- [ ] Run focused tests.

### Task 3: Evaluation Cycle Metadata

**Files:**
- Modify: `src/synthetix/benchmarking/frozen.py`
- Test: `tests/unit/test_frozen_evaluation.py`

- [ ] Write tests that freeze manifests include `cycle_id` and quality summaries flag validation reruns as non-proof.
- [ ] Add cycle ID support with default `cycle_001`.
- [ ] Include cycle ID in CLI freeze/evaluate outputs.
- [ ] Run focused tests.

### Task 4: Real Validation Rerun And Evidence

**Files:**
- Modify: `docs/progress/frozen-evaluation-progress.md`

- [ ] Re-freeze validation as a new development cycle.
- [ ] Emit predictions and evaluate validation.
- [ ] Record exact score and whether it passes.
- [ ] Run full `pytest`, `ruff`, and `mypy`.
- [ ] Commit only after verification passes.
