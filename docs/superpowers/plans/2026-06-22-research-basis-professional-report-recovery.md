# Research Basis Professional Report Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make professional golden-path proof fail unless Synthetix follows the actual digital-persona survey research basis, uses realistic professional fixture scale, emits standards-aligned disclosure, and exposes auditable chart decisions.

**Architecture:** Add a small research-basis alignment contract and feed it into report-quality scoring. Harden golden-path fixture validation and deterministic proof generation so professional runs can scale beyond hard-coded 12-person arrays. Extend chart decisions with explicit visual/replacement semantics and make report quality reject vague chart contracts.

**Tech Stack:** Python 3.12, Pydantic, pytest, existing Synthetix modular monolith, no new infrastructure.

---

## Files

- Create: `src/synthetix/research/basis_alignment.py`
- Create: `tests/unit/test_research_basis_alignment.py`
- Modify: `src/synthetix/reporting/models.py`
- Modify: `src/synthetix/analysis/reporting.py`
- Modify: `src/synthetix/reporting/quality.py`
- Modify: `src/synthetix/benchmarking/golden_path.py`
- Modify: `src/synthetix/orchestration/intake_review.py`
- Modify: `tests/unit/test_report_quality.py`
- Modify: `tests/unit/test_reporting_analytics.py`
- Modify: `tests/unit/test_golden_path.py`
- Modify: `research/benchmark_program/validation/golden_path_professional_dry_run_v1.json`
- Modify: `sdlc/constraints.json`
- Modify: `sdlc/qa/acceptance_criteria.json`
- Modify: `sdlc/plans/accepted_plan.md`

## Task 1: P1 Research Basis Alignment Gate

**Owner:** gpt-5.4-mini implementer, reviewed by gpt-5.4.

- [ ] Write `tests/unit/test_research_basis_alignment.py` proving professional quality fails when alignment omits distributional/equity/human-validation fields.
- [ ] Create `src/synthetix/research/basis_alignment.py` with a Pydantic model or helper that normalizes required basis markers from `research/golden_paper_contract.json`.
- [ ] Add `research_basis_alignment_texts` to `ReportQualityInput`.
- [ ] Add a `research_basis_alignment_complete` hard gate in `ReportQualityScorer`.
- [ ] Populate basis alignment texts in `build_quality_input()` from report methodology, research design analysis plan, disclosure notes, and fieldwork handoff.
- [ ] Run `uv run pytest tests/unit/test_research_basis_alignment.py tests/unit/test_report_quality.py -q`.

## Task 2: P2 Professional Fixture Scale and Deterministic Proof

**Owner:** gpt-5.4-mini implementer, reviewed by gpt-5.4.

- [ ] Add a failing test in `tests/unit/test_golden_path.py` proving professional fixtures with panel size below the professional minimum are invalid.
- [ ] Set professional minimum synthetic panel size to a named constant, initially `PROFESSIONAL_MIN_SYNTHETIC_PANEL_SIZE = 100`.
- [ ] Update `validate_golden_path_fixture_set()` so professional fixtures below that minimum fail fixture validation unless the fixture class is novice or bad-input.
- [ ] Replace the hard-coded 12-answer arrays in `_build_run_result_from_fixture()` with cyclic answer patterns so professional deterministic proof supports 100+ respondents.
- [ ] Update `golden_path_professional_dry_run_v1.json` to use an intended synthetic panel size of at least 120 and adjust expected panel-limit language.
- [ ] Run `uv run pytest tests/unit/test_golden_path.py -q`.

## Task 3: P3 Standards-Aligned Disclosure Adequacy Gate

**Owner:** gpt-5.4-mini implementer, reviewed by gpt-5.4.

- [ ] Add failing tests in `tests/unit/test_report_quality.py` showing generic standards text and missing weighting/nonresponse/base-size disclosures fail professional quality.
- [ ] Add disclosure keyword checks to `_check_standards_alignment()` for sample/source, synthetic panel, questionnaire/instrument, base-size/suppression, nonresponse or weighting, analysis plan, qualitative coding, limitations, provenance, and fieldwork handoff.
- [ ] Ensure the professional proof research design emits these disclosure phrases without claiming certification.
- [ ] Run `uv run pytest tests/unit/test_report_quality.py tests/unit/test_research_design_reporting.py -q`.

## Task 4: P4 Chart Decision Contract and Visual Breadth

**Owner:** gpt-5.4-mini implementer, reviewed by gpt-5.4.

- [ ] Add tests in `tests/unit/test_reporting_analytics.py` proving rendered chart decisions include `visual_type`, open-text replacements include `replacement_type`, and tiny-base decisions suppress charts.
- [ ] Extend `ChartDecision` with optional `visual_type` and `replacement_type`.
- [ ] Increase professional minimum chart base logic so global charts below the professional threshold are suppressed or replaced, while lightweight runs preserve backward compatibility.
- [ ] Populate chart decisions from actual chart outputs so status, reason, and visual type stay consistent.
- [ ] Update `build_quality_input()` and `_check_chart_decisions()` so professional rendered decisions missing a visual type fail.
- [ ] Run `uv run pytest tests/unit/test_reporting_analytics.py tests/unit/test_report_quality.py -q`.

## Task 5: Reviewer Loop and SDLC Context

**Owner:** gpt-5.4 final reviewer.

- [ ] Run `uv run pytest tests/unit/test_research_basis_alignment.py tests/unit/test_golden_path.py tests/unit/test_report_quality.py tests/unit/test_reporting_analytics.py -q`.
- [ ] Run `uv run pytest tests/integration/test_reporting.py -q`.
- [ ] Run `uv run python -m synthetix.benchmarking.golden_path --workspace .` or the existing golden-path proof command if exposed differently.
- [ ] Run `python tools/sdlc/sdlc.py ingest-gryph --since 1d`.
- [ ] Run `python tools/sdlc/sdlc.py context`.
- [ ] Review generated `data/golden-path/report-proof/report_quality.json` and `data/golden-path/review-latest.json`.
- [ ] Report remaining failures honestly; do not treat a high score as quality proof if the artifact still violates the research basis.

