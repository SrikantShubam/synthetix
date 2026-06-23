from __future__ import annotations

import json
from collections import Counter
from hashlib import sha256
from pathlib import Path

import synthetix.benchmarking.golden_path as golden_path_module
from pytest import MonkeyPatch

from synthetix.benchmarking.golden_path import (
    _build_blueprint_from_fixture,
    _build_run_result_from_fixture,
    generate_golden_path_proof,
    load_golden_path_fixtures,
    validate_golden_path_fixture_set,
)


def test_golden_path_fixtures_cover_required_contract_cases() -> None:
    fixtures = load_golden_path_fixtures(Path("research/benchmark_program/validation"))
    manifest = json.loads(
        Path("research/benchmark_program/validation/manifest.json").read_text(encoding="utf-8")
    )
    by_id = {fixture.fixture_id: fixture for fixture in fixtures}
    novice_warning = by_id["val_golden_path_novice_segmentation_warning_v1"]
    professional_manual_intake = by_id["val_golden_path_professional_manual_intake_v1"]
    professional = by_id["val_golden_path_professional_dry_run_v1"]
    bad_input = by_id["val_golden_path_bad_input_scanned_v1"]
    professional_contract_fields = {
        field.field: set(field.expected_markers) for field in professional.expected_contract_fields
    }

    assert not validate_golden_path_fixture_set(fixtures)
    assert {fixture.fixture_class for fixture in fixtures} == {
        "novice_concept_test",
        "professional_survey_dry_run",
        "bad_input_document",
    }
    assert {
        item["fixture_id"]
        for item in manifest["fixtures"]
    } == {
        "val_registry_access_policy_v1",
        "val_professional_survey_metadata_v1",
        "val_golden_path_novice_concept_v1",
        "val_golden_path_novice_segmentation_warning_v1",
        "val_golden_path_professional_dry_run_v1",
        "val_golden_path_professional_manual_intake_v1",
        "val_golden_path_bad_input_scanned_v1",
    }
    assert len(fixtures) == 5
    assert novice_warning.expected_study_plan.question_roles["q1"] == "primary_outcome"
    assert novice_warning.expected_study_plan.question_roles["q5"] == "qualitative_probe"
    assert novice_warning.expected_question_rationales[0].role == "primary_outcome"
    assert professional_manual_intake.expected_research_intake.extraction_confidence_expectation == "n/a"
    assert professional_manual_intake.expected_research_intake.source_sample_size == 240
    assert {
        "region",
        "disability status",
        "tenure band",
    }.issubset(set(professional_manual_intake.expected_research_intake.segment_variables))
    assert {
        "accessibility barrier topline",
        "region cut",
        "tenure cut",
        "open-text friction themes",
    }.issubset(
        {
            marker
            for field in professional_manual_intake.expected_contract_fields
            for marker in field.expected_markers
        }
    )
    assert professional.source_material.title == "EEA Professional Climate Survey Report"
    assert "fleet workflow" not in professional.source_material.body.casefold()
    assert "861 respondents" in professional.source_material.body
    assert professional.test_case_source_document is not None
    assert professional.test_case_source_document.path.endswith(
        "2508.04302_eea_professional_climate_survey_report.pdf"
    )
    assert professional.expected_research_intake.source_sample_size == 861
    assert professional.expected_research_intake.target_population_size is None
    novice = by_id["val_golden_path_novice_concept_v1"]
    novice_warning = by_id["val_golden_path_novice_segmentation_warning_v1"]
    assert novice.expected_study_plan.question_roles == {
        "q1": "primary_outcome",
        "q5": "qualitative_probe",
    }
    assert novice_warning.expected_study_plan.question_roles == {
        "q1": "primary_outcome",
        "q5": "qualitative_probe",
    }
    assert {
        "gender",
        "ethnic minority status",
        "LGBTQ+ status",
        "disability status",
        "country/region group",
    }.issubset(set(professional.expected_research_intake.segment_variables))
    assert {
        "general climate",
        "opinions and perceptions",
        "experiences of discrimination",
        "actions taken to avoid possible harassment",
        "experiences of exclusion and harassment",
    }.issubset(professional_contract_fields["expected_analyses"])
    assert any("representat" in warning.casefold() for warning in professional.expected_report_warnings)
    assert bad_input.expected_contract_fields
    assert bad_input.expected_research_intake.professional_mode_blocked_without_gemini is True
    assert {
        field.field for field in bad_input.expected_contract_fields
    } == {"blocked_intake_contract", "source_title"}
    assert bad_input.expected_chart_decisions[0].status == "suppressed"
    assert "low-confidence" in bad_input.expected_chart_decisions[0].reason_contains


def test_professional_golden_path_fixtures_below_minimum_panel_size_fail_validation() -> None:
    fixtures = load_golden_path_fixtures(Path("research/benchmark_program/validation"))
    by_id = {fixture.fixture_id: fixture for fixture in fixtures}
    professional = by_id["val_golden_path_professional_dry_run_v1"]
    undersized_professional = professional.model_copy(
        update={
            "expected_research_intake": professional.expected_research_intake.model_copy(
                update={"intended_synthetic_panel_size": 99}
            )
        }
    )

    findings = validate_golden_path_fixture_set([undersized_professional])

    assert any("minimum synthetic panel size" in finding for finding in findings)


def test_professional_golden_path_fixtures_require_segmentation_and_handoff_contracts() -> None:
    fixtures = load_golden_path_fixtures(Path("research/benchmark_program/validation"))
    by_id = {fixture.fixture_id: fixture for fixture in fixtures}
    professional = by_id["val_golden_path_professional_manual_intake_v1"]
    broken_professional = professional.model_copy(
        update={
            "expected_segmentation_behavior": {
                **professional.expected_segmentation_behavior,
                "minimum_base_rule": "",
                "suppression_rule": "",
            },
            "expected_human_fieldwork_handoff": [],
        }
    )

    findings = validate_golden_path_fixture_set([broken_professional])

    assert any("minimum_base_rule" in finding for finding in findings)
    assert any("suppression_rule" in finding for finding in findings)
    assert any("expected_human_fieldwork_handoff" in finding for finding in findings)


def test_golden_path_fixture_role_and_question_type_alignment() -> None:
    fixtures = load_golden_path_fixtures(Path("research/benchmark_program/validation"))
    by_id = {fixture.fixture_id: fixture for fixture in fixtures}

    professional_manual_intake = by_id["val_golden_path_professional_manual_intake_v1"]
    novice_warning = by_id["val_golden_path_novice_segmentation_warning_v1"]

    professional_blueprint = _build_blueprint_from_fixture(professional_manual_intake)

    professional_question_types = {question.id: question.type for question in professional_blueprint.questions}

    assert professional_question_types["q1"] == "likert"
    assert professional_question_types["q5"] == "open_text"
    assert professional_blueprint.research_design.question_role_map["q5"] == "qualitative_probe"
    assert "accessibility" in professional_blueprint.research_intake.question_rationales["q5"].casefold()
    assert novice_warning.expected_study_plan.question_roles["q1"] == "primary_outcome"
    assert novice_warning.expected_study_plan.question_roles["q5"] == "qualitative_probe"
    assert "plain language" in novice_warning.expected_question_rationales[1].rationale.casefold()

    for question_id, role in professional_blueprint.research_design.question_role_map.items():
        assert role in {
            "screening",
            "primary_outcome",
            "driver",
            "diagnostic",
            "qualitative_probe",
            "metadata",
        }
        if professional_question_types[question_id] == "open_text":
            assert role == "qualitative_probe"


def test_golden_path_deterministic_proof_builds_varied_professional_panel() -> None:
    fixtures = load_golden_path_fixtures(Path("research/benchmark_program/validation"))
    by_id = {fixture.fixture_id: fixture for fixture in fixtures}
    professional = by_id["val_golden_path_professional_dry_run_v1"]
    large_professional = professional.model_copy(
        update={
            "expected_research_intake": professional.expected_research_intake.model_copy(
                update={"intended_synthetic_panel_size": 120}
            )
        }
    )

    result = _build_run_result_from_fixture(large_professional)

    assert len(result.respondents) == 120
    unique_attribute_profiles = {
        tuple(sorted(respondent.attributes.items())) for respondent in result.respondents
    }
    assert len(unique_attribute_profiles) > 12

    gender_counts = Counter(respondent.attributes["gender"] for respondent in result.respondents)
    minority_counts = Counter(
        respondent.attributes["ethnic_minority_status"] for respondent in result.respondents
    )
    disability_counts = Counter(
        respondent.attributes["disability_status"] for respondent in result.respondents
    )
    region_counts = Counter(
        respondent.attributes["country_region_group"] for respondent in result.respondents
    )

    assert gender_counts == {"women": 57, "men": 63}
    assert minority_counts == {"yes": 38, "no": 82}
    assert disability_counts == {"yes": 17, "no": 103}
    assert region_counts == {"Nordics": 26, "Italy": 19, "UK/Ireland": 31, "Iberia": 44}

    q2_counts = Counter(respondent.answers["q2"] for respondent in result.respondents)
    q3_counts = Counter(respondent.answers["q3"] for respondent in result.respondents)
    assert q2_counts != q3_counts
    assert all(count % 10 != 0 for count in q2_counts.values())


def test_golden_path_deterministic_answers_scale_to_source_sized_panel() -> None:
    fixtures = load_golden_path_fixtures(Path("research/benchmark_program/validation"))
    by_id = {fixture.fixture_id: fixture for fixture in fixtures}
    professional = by_id["val_golden_path_professional_dry_run_v1"]
    source_sized_professional = professional.model_copy(
        update={
            "expected_research_intake": professional.expected_research_intake.model_copy(
                update={"intended_synthetic_panel_size": 861}
            )
        }
    )

    result = _build_run_result_from_fixture(source_sized_professional)

    assert len(result.respondents) == 861
    q1_counts = Counter(respondent.answers["q1"] for respondent in result.respondents)
    q2_counts = Counter(respondent.answers["q2"] for respondent in result.respondents)
    q3_counts = Counter(respondent.answers["q3"] for respondent in result.respondents)
    q4_counts = Counter(respondent.answers["q4"] for respondent in result.respondents)

    assert q1_counts == {1: 50, 2: 129, 3: 223, 4: 280, 5: 157, 6: 22}
    assert q2_counts == {"Never": 151, "Rarely": 265, "Sometimes": 309, "Often": 136}
    assert q3_counts == {"Never": 136, "Rarely": 294, "Sometimes": 237, "Often": 194}
    assert q4_counts == {"Chart every region": 115, "Use suppressed tables": 595, "Skip regional cut": 151}


def test_golden_path_proof_uses_real_test_case_pdf_and_review_passes(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    if not hasattr(golden_path_module, "_select_report_fixture"):
        monkeypatch.setattr(
            golden_path_module,
            "_select_report_fixture",
            lambda fixtures: next(
                fixture
                for fixture in fixtures
                if fixture.fixture_class == "professional_survey_dry_run"
            ),
            raising=False,
        )
    if not hasattr(golden_path_module, "_sha256"):
        monkeypatch.setattr(
            golden_path_module,
            "_sha256",
            lambda path: sha256(Path(path).read_bytes()).hexdigest(),
            raising=False,
        )
    proof = generate_golden_path_proof(Path.cwd(), output_dir=tmp_path / "golden-path")
    proof_summary_path = tmp_path / "golden-path/intake-proof/proof-summary.json"

    professional = next(
        item
        for item in proof.proofs
        if item.fixture_id == "val_golden_path_professional_dry_run_v1"
    )
    professional_manual_intake = next(
        item
        for item in proof.proofs
        if item.fixture_id == "val_golden_path_professional_manual_intake_v1"
    )
    novice_warning = next(
        item
        for item in proof.proofs
        if item.fixture_id == "val_golden_path_novice_segmentation_warning_v1"
    )
    bad_input = next(
        item
        for item in proof.proofs
        if item.fixture_id == "val_golden_path_bad_input_scanned_v1"
    )

    assert professional.source_file.endswith("2508.04302_eea_professional_climate_survey_report.pdf")
    assert professional.extraction_confidence == "high"
    assert professional.comparison_path is not None
    assert professional_manual_intake.source_format == "markdown_brief"
    assert professional_manual_intake.extraction_confidence == "n/a"
    assert professional_manual_intake.comparison_path is None
    assert novice_warning.source_format == "markdown_brief"
    assert novice_warning.extraction_confidence == "n/a"
    assert novice_warning.comparison_path is None
    assert bad_input.extraction_confidence == "low"
    assert bad_input.professional_mode_blocked_without_gemini is True
    assert proof_summary_path.exists()

    professional_comparison = json.loads(
        (Path.cwd() / professional.comparison_path).read_text(encoding="utf-8")
    )
    bad_input_comparison = json.loads((Path.cwd() / bad_input.comparison_path).read_text(encoding="utf-8"))

    assert professional_comparison["passed"] is True
    assert {
        field["field"] for field in professional_comparison["fields"]
    } >= {"research_context", "source_sample_size", "segment_variables", "comparative_frame", "limitations"}
    assert bad_input_comparison["passed"] is True
    assert {
        field["field"] for field in bad_input_comparison["fields"]
    } == {"blocked_intake_contract", "source_title"}
    proof_summary = json.loads(proof_summary_path.read_text(encoding="utf-8"))
    assert proof_summary["fixture_count"] == 5
    assert proof_summary["classes_present"] == [
        "bad_input_document",
        "novice_concept_test",
        "professional_survey_dry_run",
    ]
    assert {
        proof_item["fixture_id"] for proof_item in proof_summary["proofs"]
    } == {
        "val_golden_path_bad_input_scanned_v1",
        "val_golden_path_novice_concept_v1",
        "val_golden_path_novice_segmentation_warning_v1",
        "val_golden_path_professional_dry_run_v1",
        "val_golden_path_professional_manual_intake_v1",
    }
    report_json_path = next(
        Path.cwd() / artifact
        for artifact in proof_summary["report_artifacts"]
        if artifact.endswith("report.json")
    )
    assert report_json_path.exists()

    fixture_report_proofs = {
        item["fixture_id"]: item for item in proof_summary["fixture_report_proofs"]
    }
    assert set(fixture_report_proofs) == {
        "val_golden_path_bad_input_scanned_v1",
        "val_golden_path_novice_concept_v1",
        "val_golden_path_novice_segmentation_warning_v1",
        "val_golden_path_professional_dry_run_v1",
        "val_golden_path_professional_manual_intake_v1",
    }
    assert fixture_report_proofs["val_golden_path_bad_input_scanned_v1"] == {
        "fixture_id": "val_golden_path_bad_input_scanned_v1",
        "fixture_class": "bad_input_document",
        "expected_report_tier": "blocked_intake",
        "expected_acceptance": "blocked",
        "generated": False,
        "accepted": False,
        "failed_hard_gates": ["professional_document_intake"],
        "report_artifacts": [],
        "report_quality_path": None,
    }
    assert fixture_report_proofs["val_golden_path_novice_concept_v1"]["expected_acceptance"] == "lightweight_only"
    assert fixture_report_proofs["val_golden_path_novice_concept_v1"]["generated"] is True
    assert fixture_report_proofs["val_golden_path_novice_segmentation_warning_v1"]["expected_acceptance"] == "lightweight_only"
    assert fixture_report_proofs["val_golden_path_professional_manual_intake_v1"]["expected_acceptance"] == "rejected"
    assert fixture_report_proofs["val_golden_path_professional_manual_intake_v1"]["accepted"] is False
    assert "professional_synthetic_panel_size" in fixture_report_proofs[
        "val_golden_path_professional_manual_intake_v1"
    ]["failed_hard_gates"]
    assert fixture_report_proofs["val_golden_path_professional_dry_run_v1"]["expected_acceptance"] == "accepted"
    assert fixture_report_proofs["val_golden_path_professional_dry_run_v1"]["accepted"] is True

    report_payload = json.loads(report_json_path.read_text(encoding="utf-8"))
    actual_chart_decisions = {
        item["question_id"]: item["status"]
        for item in report_payload["chart_decisions"]
    }
    assert actual_chart_decisions["q1"] == "rendered"
    assert actual_chart_decisions["q2"] == "rendered"
    assert actual_chart_decisions["q3"] == "rendered"
    assert actual_chart_decisions["q4"] == "replaced_with_table"
    assert actual_chart_decisions["q5"] == "replaced_with_evidence_panel"
