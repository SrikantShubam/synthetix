# SDLC Agent Brief

Read this first. Open larger SDLC files only when the active task needs detail.

## State

- phase: `implementation`
- active feature: `existing-project-sdlc-baseline`
- implementation allowed: `True`

## Non-Negotiable Constraints

- `C001`: Synthetix outputs are synthetic scenario evidence only. The product must not claim representative human research, prevalence, confidence intervals, causality, statistical significa
- `C004`: OpenRouter is the primary research gateway. Groq may be used as an explicit, verified fallback only when the user enables fallback, the capability profile exists, provider use is r
- `C005`: Model-assisted document parsing requires explicit external-transmission confirmation, and OpenRouter API keys must be read from environment variables and never written to manifests
- `C007`: Holdout/source-of-truth papers are evaluation-only. They cannot be used for training, prompt tuning, few-shot examples, model selection on the same set, or self-improvement.
- `C008`: Unsupported survey domains must be marked not_benchmarkable; the system must not invent benchmark confidence.
- `C009`: The cycle_002 validation result passed, but holdout actual-vs-predicted evaluation remains blocked until locked holdout target JSON fixtures are authored and reviewed.
- `C011`: AI implementation work must pass SDLC gates: accepted plan, constraints, acceptance criteria, test strategy, subagent split, readiness eval, and generated context.
- `C012`: Dashboard charts must be driven by backend-generated analytics JSON and rendered with Apache ECharts; raw narrative responses must never be used as axis labels.
- `C013`: Benchmark prediction logic must not require or read actual_targets, answer keys, or any target-bearing structure in order to generate predictions. Prediction-time code must operate
- `C014`: Prediction logic must not derive benchmark outputs from benchmark-answer-bearing fixture fields such as human_reference_summary, calibration_clues, registry_summary, or equivalent 
- `C015`: If removing leakage causes benchmark scores to collapse, the prior high scores must be treated as invalid contaminated results, not as proof of model quality. Agents must explicitl
- `C016`: Agents must not game benchmark or report-quality evaluation by optimizing for fixture-specific artifacts, hidden answer cues, raw leaked text labels, or direct reuse of expected re
- `C017`: Professional report acceptance requires a complete explicit or confirmed ResearchDesign. Shallow reports, unmapped objectives, missing assumptions, missing target population defini
- `C018`: Professional proof artifacts must use the real report renderer path and may not substitute plaintext fallback PDFs. Report quality scoring must cap failed hard-gate results below t

## Current Accepted Direction

## Product
Synthetix is a self-hosted synthetic scenario-exploration and survey simulation sandbox. It helps users explore likely response patterns, segment differences, weak questions, bench
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
- `09-research-design-study-plan`: active and now executed through an intake-first vertical slice. `ResearchIntake` precedes `ResearchDesign` for document/questionnaire ingestion, 
- `10-golden-path-intake-reset`: active; golden-path proof artifacts now use real renderer paths and fixture-backed intake proof instead of placeholder proof outputs.
- `11-report-chart-quality-recovery`: active; professional report quality now requires honest renderer evidence, hard-gate-capped scores, and explicit chart-type decisions instead 
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

## Current Dynamic State

# Dynamic Context
Generated at: 2026-06-21T19:07:39.596677+00:00
Current phase: implementation
Active feature: existing-project-sdlc-baseline
Implementation allowed: True
## Blocked Reasons
## Gryph Summary
- Events: 0
- Sessions: 0
- Files written: 0
- Commands: 0
- Failures: 0
## Recent Files Written
## Recent Commands


## Model Routing

role: "senior_planner_policy_reviewer_final_reviewer"
    role: "bounded_implementer_test_writer_plumbing_agent"
hard_rules:
  - "GPT-5.4-mini must not edit holdout/source-of-truth paths."
  - "GPT-5.4-mini must not change scientific-boundary, security, or product-positioning policy files."
  - "No model may claim implementation success without verification evidence."
  - "No model may manually invent audit history; Gryph evidence must be ingested when available."
