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
- `09-research-design-study-plan`: planned as the next high-judgment task before professional report quality can be accepted.

## Current Evaluation State

- Development quality loop reached target in iteration 2 with average score `1.0` and minimum fixture score `1.0`.
- Frozen validation cycle 001 failed and must not be tuned against as proof.
- Frozen validation cycle 002 passed with fixture count `2`, average score `1.0`, minimum fixture score `1.0`, and no failing fixtures.
- Holdout PDFs are frozen and hashed for cycle 002.
- Holdout actual-vs-predicted comparison remains blocked until locked holdout target JSON fixtures are authored and reviewed.

## Next High-Value Work

1. Implement `09-research-design-study-plan` so every professional report is driven by objectives, assumptions, target population, segmentation, analysis plan, qualitative coding plan, and standards-aligned disclosure.
2. Continue rich reporting only after the ResearchDesign contract exists, so report depth is judged against planned objectives and analyses rather than headings alone.
3. Author and review locked holdout target JSON fixtures with source PDF hash validation.
4. Run holdout actual-vs-predicted only after the target fixtures are locked.
5. Keep all benchmark and report changes inside the scientific boundary.
6. Harden the SDLC governor by running live Promptfoo gates once provider credentials are configured.
7. Use Gryph evidence during future Codex/Claude Code sessions to generate dynamic context and review agent actions.

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
