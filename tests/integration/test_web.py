from pathlib import Path

from fastapi.testclient import TestClient

from synthetix.web.app import create_app


def test_minimal_ui_exposes_four_workflow_views(tmp_path: Path) -> None:
    client = TestClient(create_app(data_dir=tmp_path))
    assert client.get("/").status_code == 200
    assert "New run" in client.get("/").text
    assert client.get("/runs/demo/preflight").status_code == 200
    assert client.get("/runs/demo/status").status_code == 200
    results = client.get("/runs/demo/results")
    assert results.status_code == 200
    assert "echart-host" in results.text
    assert "application/json" in results.text


def test_ingest_rejects_professional_blueprint_with_question_quality_errors(tmp_path: Path) -> None:
    client = TestClient(create_app(data_dir=tmp_path))
    payload = """
title: Bad pricing survey
purpose: Assess pricing.
population:
  size: 2
  seed: 1
questions:
  - type: choice
    id: q1
    prompt: "Do you feel the value proposition of the new sandwich at $9.49 is fair?"
    options: ["Yes", "No"]
research_design:
  study_type: concept_test
  research_objectives: [Measure fit]
  decision_questions: ["Should the concept proceed?"]
  assumptions: [Synthetic only]
  target_population_definition:
    inclusion_rules: [Adults]
    exclusion_rules: [None]
    geography: US
    timeframe: Current
    unit_of_analysis: Decision-maker
  sampling_or_simulation_frame:
    persona_generation_frame: Declared attribute grid
    quotas_or_weights: [No weighting]
    uncovered_groups: [Undeclared]
  segmentation_plan:
    segment_variables: [region]
    planned_cuts: [region]
    minimum_base_rule: Suppress cuts below n=2
    suppression_rule: Mark suppressed cuts
  question_role_map:
    q1: primary_outcome
  analysis_plan:
    toplines: [Primary topline]
    cross_tabs: [By region]
    likert_summaries: []
    rankings: []
    theme_coding: []
    sensitivity_checks: [Review invalid attempts]
    benchmark_checks: [Use selected metric pass rate wording only]
  qualitative_coding_plan:
    coding_mode: deterministic
    theme_granularity: Barrier themes
    quote_evidence_required: true
    minimum_theme_count: 1
  report_requirements:
    report_tier: professional
    required_sections: [research_design, objective_coverage, standards_alignment_appendix]
    minimum_figures: 1
    minimum_tables: 2
    appendix_requirements: [Planned-vs-delivered appendix]
    audience_level: professional
  disclosure_plan:
    synthetic_only_warning: true
    non_inferential_limits: true
    model_provider_provenance: true
    data_quality_notes: [Synthetic only]
  standards_alignment:
    iso_20252: [Purpose disclosure]
    aapor_disclosure: [Questionnaire disclosure]
    icc_esomar: [Transparency disclosure]
""".strip()
    response = client.post(
        "/ingest",
        files={"file": ("bad-survey.yaml", payload, "application/x-yaml")},
        data={"confirm_transmission": "false"},
    )

    assert response.status_code == 400
    assert "Question quality guardrails failed" in response.text
