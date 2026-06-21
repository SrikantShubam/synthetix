# Accepted Plan: Synthetix Existing Project SDLC Baseline

## Product

Synthetix is a self-hosted synthetic scenario-exploration and survey simulation sandbox. It helps users explore likely response patterns, segment differences, weak questions, benchmark support, and human-survey handoff needs before running real fieldwork.

## Current Architecture

- Modular monolith.
- Typer CLI and FastAPI web app share the same `RunService`.
- Blueprints are immutable and validated before execution.
- Runs create manifests, enforce preflight token/cost ceilings, execute through bounded `RunExecutor`, persist attempts in SQLite, and render `ReportModel` artifacts to HTML/PDF.
- OpenRouter is a transport gateway with allowlisted capability profiles, pinned provider order, and no automatic fallback for research runs.
- Redis, distributed workers, PostgreSQL, vectors, and semantic projection are intentionally out of scope until justified by measured workload or validated research need.

## Accepted Spec Progress

- `00-product-goals`: accepted.
- `01-benchmark-thresholds`: accepted.
- `02-pipeline-predicted-metrics`: accepted after benchmark comparison passed.
- `03-professional-report-pdf`: accepted.
- `04-transparent-simulation-dashboard`: accepted.
- `05-validation-and-holdout-readiness`: accepted for validation readiness.
- `06-agent-orchestrator-loop`: accepted.
- `07-honest-predictor-improvement`: active; leakage-sensitive predictor work remains under review.
- `08-rich-reporting-upgrade`: active; professional report depth criteria are stricter but rich generation is not complete.
- `09-research-design-study-plan`: active and now executed through an intake-first vertical slice. `ResearchIntake` precedes `ResearchDesign` for document/questionnaire ingestion, professional PDF intake enforces explicit OCR confidence rules, and reports now disclose intake scale, chart decisions, and fieldwork handoff.
- `10-golden-path-intake-reset`: active; golden-path proof artifacts now use real renderer paths and fixture-backed intake proof instead of placeholder proof outputs.
- `11-report-chart-quality-recovery`: active; professional report quality now requires honest renderer evidence, hard-gate-capped scores, and explicit chart-type decisions instead of a bar-only fallback.

## Current Evaluation State

- Development quality loop reached target in iteration 2 with average score `1.0` and minimum fixture score `1.0`.
- Frozen validation cycle 001 failed and must not be tuned against as proof.
- Frozen validation cycle 002 passed with fixture count `2`, average score `1.0`, minimum fixture score `1.0`, and no failing fixtures.
- Holdout PDFs are frozen and hashed for cycle 002.
- Holdout actual-vs-predicted comparison remains blocked until locked holdout target JSON fixtures are authored and reviewed.

## Next High-Value Work

1. Replace remaining weak examples and benchmark-adjacent fixtures with golden-path intake fixtures that explicitly cover novice, professional, and bad-input document cases.
2. Continue rich reporting only after the intake-first contract is used by the shipped examples and objective-coverage/report-depth outputs remain strong under those fixtures.
3. Keep production or structured PDF proof honest and prevent fallback plaintext artifacts from passing as professional output.
4. Expand chart selection beyond bar-only defaults and preserve evidence-panel suppression for qualitative questions.
5. Author and review locked holdout target JSON fixtures with source PDF hash validation.
6. Run holdout actual-vs-predicted only after the target fixtures are locked.
7. Keep all benchmark and report changes inside the scientific boundary.
8. Harden the SDLC governor by running live Promptfoo gates once provider credentials are configured.
9. Use Gryph evidence during future Codex/Claude Code sessions to generate dynamic context and review agent actions.

## Non-Goals

- Do not claim synthetic responses are representative human survey results.
- Do not infer prevalence, statistical significance, confidence intervals, or causality.
- Do not use holdout/source-of-truth papers for training, prompt tuning, few-shot examples, model selection, or self-improvement.
- Do not add distributed infrastructure before measurable need exists.
- Do not claim ISO, AAPOR, ICC, ESOMAR, or WAPOR certification; only claim standards-aligned disclosure behavior.
- Do not describe selected benchmark metric pass rates as full survey-paper, table, chart, wording, qualitative-code, or report replication.

## Required Checks For Future Implementation

- `uv run pytest`
- targeted unit tests for changed modules
- benchmark comparison commands for benchmark changes
- frozen validation/holdout commands only when the active task permits those paths
- SDLC context refresh with `python tools/sdlc/sdlc.py ingest-gryph --since 1d` and `python tools/sdlc/sdlc.py context`
- ResearchDesign work must include schema tests, prompt contract tests, report objective-coverage tests, orchestrator loop tests, and standards-alignment disclosure checks.
