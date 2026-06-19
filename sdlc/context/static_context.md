# Static Context

## Active Constraints
{
  "active": [
    {
      "id": "C001",
      "source": "README.md, goals.md, docs/protocols/scientific-boundary.md",
      "text": "Synthetix outputs are synthetic scenario evidence only. The product must not claim representative human research, prevalence, confidence intervals, causality, statistical significance, or replacement of human surveys."
    },
    {
      "id": "C002",
      "source": "docs/architecture/baseline.md",
      "text": "Keep the application a modular monolith until measured workload or validated research requirements justify Redis, distributed workers, PostgreSQL, vectors, or semantic projection."
    },
    {
      "id": "C003",
      "source": "README.md, docs/architecture/baseline.md",
      "text": "Only openrouter-default is certified in the baseline. Additional model support requires a capability profile and conformance tests."
    },
    {
      "id": "C004",
      "source": "docs/architecture/baseline.md",
      "text": "OpenRouter is the primary research gateway. Groq may be used as an explicit, verified fallback only when the user enables fallback, the capability profile exists, provider use is recorded in the manifest, and locked benchmark or holdout runs do not silently switch providers."
    },
    {
      "id": "C005",
      "source": "docs/operations/security.md",
      "text": "Model-assisted document parsing requires explicit external-transmission confirmation, and OpenRouter API keys must be read from environment variables and never written to manifests."
    },
    {
      "id": "C006",
      "source": "docs/operations/security.md",
      "text": "Uploaded files must be constrained by size, suffix, encoding, and PDF page count. Report rendering must reject remote assets and escape model output through Jinja."
    },
    {
      "id": "C007",
      "source": "goals.md, docs/specs/01-benchmark-thresholds.md, docs/specs/05-validation-and-holdout-readiness.md",
      "text": "Holdout/source-of-truth papers are evaluation-only. They cannot be used for training, prompt tuning, few-shot examples, model selection on the same set, or self-improvement."
    },
    {
      "id": "C008",
      "source": "docs/specs/01-benchmark-thresholds.md",
      "text": "Unsupported survey domains must be marked not_benchmarkable; the system must not invent benchmark confidence."
    },
    {
      "id": "C009",
      "source": "docs/progress/frozen-evaluation-progress.md",
      "text": "The cycle_002 validation result passed, but holdout actual-vs-predicted evaluation remains blocked until locked holdout target JSON fixtures are authored and reviewed."
    },
    {
      "id": "C010",
      "source": "pyproject.toml",
      "text": "Maintain Python 3.12 compatibility, strict mypy intent, pytest-based tests, and Typer/FastAPI shared service paths."
    },
    {
      "id": "C011",
      "source": "AGENTS.md, CLAUDE.md, SDLC governor",
      "text": "AI implementation work must pass SDLC gates: accepted plan, constraints, acceptance criteria, test strategy, subagent split, readiness eval, and generated context."
    },
    {
      "id": "C012",
      "source": "docs/specs/08-professional-echarts-analytics.md",
      "text": "Dashboard charts must be driven by backend-generated analytics JSON and rendered with Apache ECharts; raw narrative responses must never be used as axis labels."
    },
    {
      "id": "C013",
      "source": "Leakage review, benchmark integrity policy",
      "text": "Benchmark prediction logic must not require or read actual_targets, answer keys, or any target-bearing structure in order to generate predictions. Prediction-time code must operate without ground-truth outcome values being present."
    },
    {
      "id": "C014",
      "source": "Leakage review, benchmark integrity policy",
      "text": "Prediction logic must not derive benchmark outputs from benchmark-answer-bearing fixture fields such as human_reference_summary, calibration_clues, registry_summary, or equivalent proxy fields that encode target values, toplines, or benchmark outcomes."
    },
    {
      "id": "C015",
      "source": "Leakage review, benchmark integrity policy",
      "text": "If removing leakage causes benchmark scores to collapse, the prior high scores must be treated as invalid contaminated results, not as proof of model quality. Agents must explicitly record that the earlier result was not trustworthy."
    },
    {
      "id": "C016",
      "source": "Leakage review, benchmark integrity policy",
      "text": "Agents must not game benchmark or report-quality evaluation by optimizing for fixture-specific artifacts, hidden answer cues, raw leaked text labels, or direct reuse of expected report outputs. Improvements must come from legitimate prediction logic, backend analytics contracts, or presentation logic that does not consume answer-bearing evaluation data."
    },
    {
      "id": "C017",
      "source": "docs/specs/09-research-design-study-plan.md, docs/protocols/research-design-standards-alignment.md",
      "text": "Professional report acceptance requires a complete explicit or confirmed ResearchDesign. Shallow reports, unmapped objectives, missing assumptions, missing target population definitions, missing analysis plans, missing qualitative coding plans, missing disclosure appendices, or broad benchmark accuracy claims cannot pass professional quality gates."
    }
  ],
  "non_negotiable": [
    "C001",
    "C004",
    "C005",
    "C007",
    "C008",
    "C009",
    "C011",
    "C012",
    "C013",
    "C014",
    "C015",
    "C016",
    "C017"
  ],
  "retired": []
}

## Accepted Plan
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

## Subagent Split
models:
  gpt-5.4:
    role: "senior_planner_policy_reviewer_final_reviewer"
    purpose: "Own high-judgment work: product positioning, scientific boundary, benchmark/holdout governance, architecture decisions, final review, and SDLC gate decisions."
    owns_tasks:
      - "Extract and maintain non-negotiable constraints in sdlc/constraints.json."
      - "Create or approve accepted plans in sdlc/plans/accepted_plan.md."
      - "Review plan diffs for dropped constraints or changed assumptions."
      - "Review scientific-boundary language in product, report, benchmark, and UI changes."
      - "Approve benchmark/holdout governance changes."
      - "Review final compliance using Gryph evidence and test results."
      - "Decide whether GPT-5.4-mini output is safe to merge or needs rework."
    allowed_paths:
      - "AGENTS.md"
      - "CLAUDE.md"
      - "goals.md"
      - "docs/specs/**"
      - "docs/protocols/**"
      - "docs/operations/**"
      - "docs/progress/**"
      - "sdlc/**"
      - "evals/**"
      - "src/synthetix/**"
      - "tests/**"
      - "research/benchmark_program/validation/**"
    forbidden_paths:
      - "research/source_of_truth/**"
      - "data/benchmark-results/holdout/**"
    may_edit_code: true
    code_edit_rule: "Only for high-judgment policy, orchestration, benchmark governance, report semantics, or review fixes. Prefer delegating bounded plumbing to gpt-5.4-mini."

  gpt-5.4-mini:
    role: "bounded_implementer_test_writer_plumbing_agent"
    purpose: "Own scoped implementation, tests, fixtures, CLI plumbing, deterministic data contracts, and small refactors after GPT-5.4 has accepted the plan."
    owns_tasks:
      - "Implement accepted plans with narrow file scope."
      - "Write or update unit tests from sdlc/qa/acceptance_criteria.json."
      - "Maintain benchmark prediction payload plumbing when contracts are already defined."
      - "Run targeted verification commands and report results."
      - "Update low-risk progress notes after checks pass."
      - "Regenerate SDLC context after implementation using the governor commands."
    allowed_paths:
      - "src/synthetix/**"
      - "tests/**"
      - "examples/**"
      - "sdlc/context/**"
      - "sdlc/gryph_summary.json"
      - "docs/progress/**"
      - "data/benchmark-predictions/**"
    forbidden_paths:
      - "research/source_of_truth/**"
      - "data/benchmark-results/holdout/**"
      - "goals.md"
      - "docs/protocols/scientific-boundary.md"
      - "docs/operations/security.md"
      - "sdlc/constraints.json"
      - "sdlc/plans/accepted_plan.md"
    may_edit_code: true
    code_edit_rule: "Do not change product positioning, scientific claims, benchmark policy, holdout policy, provider fallback policy, or security rules."

task_routing:
  product_positioning:
    owner: "gpt-5.4"
    reason: "Requires careful scientific and user-facing claim boundaries."
  scientific_boundary:
    owner: "gpt-5.4"
    reason: "High risk if synthetic outputs are overstated."
  benchmark_threshold_policy:
    owner: "gpt-5.4"
    reason: "Unsupported domains and confidence language must stay conservative."
  holdout_readiness:
    owner: "gpt-5.4"
    reason: "Holdout/source-of-truth contamination is a hard governance risk."
  final_review:
    owner: "gpt-5.4"
    reason: "Final approval must compare plan, constraints, tests, and Gryph evidence."
  architecture_change:
    owner: "gpt-5.4"
    reason: "Architecture changes can violate the modular monolith constraint."
  report_semantics:
    owner: "gpt-5.4"
    reason: "Report language must avoid representative survey claims."
  orchestrator_policy:
    owner: "gpt-5.4"
    reason: "Agent model routing and forbidden paths are governance decisions."
  cli_plumbing:
    owner: "gpt-5.4-mini"
    reviewer: "gpt-5.4"
    reason: "Implementation is bounded once the contract is defined."
  deterministic_data_contract:
    owner: "gpt-5.4-mini"
    reviewer: "gpt-5.4"
    reason: "Mini can implement schemas/tests; GPT-5.4 reviews policy impact."
  unit_tests:
    owner: "gpt-5.4-mini"
    reviewer: "gpt-5.4"
    reason: "Test writing is bounded by accepted criteria."
  bugfix_with_known_root_cause:
    owner: "gpt-5.4-mini"
    reviewer: "gpt-5.4"
    reason: "Mini can fix narrow defects after root cause is documented."
  benchmark_prediction_plumbing:
    owner: "gpt-5.4-mini"
    reviewer: "gpt-5.4"
    reason: "Mini can emit/score payloads; GPT-5.4 checks benchmark policy."
  dashboard_ui_plumbing:
    owner: "gpt-5.4-mini"
    reviewer: "gpt-5.4"
    reason: "Mini can implement inspectable UI views after copy/claims are constrained."

workflow:
  planning:
    owner: "gpt-5.4"
    output_required:
      - "sdlc/plans/accepted_plan.md"
      - "sdlc/constraints.json"
      - "sdlc/qa/acceptance_criteria.json"
      - "sdlc/qa/test_strategy.md"
  implementation:
    owner: "gpt-5.4-mini"
    entry_conditions:
      - "current_phase is implementation"
      - "accepted plan exists"
      - "constraints exist"
      - "acceptance criteria exist"
      - "test strategy exists"
      - "readiness gate passed or explicit user override exists"
    output_required:
      - "code changes scoped to allowed paths"
      - "targeted tests"
      - "verification output"
      - "Gryph evidence ingested"
      - "dynamic context regenerated"
  review:
    owner: "gpt-5.4"
    input_required:
      - "accepted plan"
      - "constraints"
      - "test strategy"
      - "Gryph summary"
      - "test output"
    output_required:
      - "go/no-go decision"
      - "constraint regressions, if any"
      - "required fixes, if any"

hard_rules:
  - "GPT-5.4-mini must not edit holdout/source-of-truth paths."
  - "GPT-5.4-mini must not change scientific-boundary, security, or product-positioning policy files."
  - "GPT-5.4 owns all decisions that can affect external claims, benchmark governance, model/provider policy, or holdout readiness."
  - "No model may claim implementation success without verification evidence."
  - "No model may manually invent audit history; Gryph evidence must be ingested when available."

