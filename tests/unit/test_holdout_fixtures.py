from __future__ import annotations

from pydantic import ValidationError

from synthetix.benchmarking.fixtures import HoldoutFixtureAuthor, HoldoutTargetFixture


def test_holdout_target_fixture_requires_source_hash_and_actual_targets() -> None:
    fixture = HoldoutTargetFixture.model_validate(
        {
            "fixture_id": "holdout_privacy_accuracy_v1",
            "data_partition": "holdout",
            "evaluation_only": True,
            "training_allowed": False,
            "source_reference": {
                "paper_id": "privacy_personas",
                "path": "research/source_of_truth/holdout_papers/ai_persona/privacy.pdf",
                "sha256": "a" * 64,
                "citation": "Privacy Personas Paper.",
                "extraction_notes": "Reported top-line predictive accuracy.",
            },
            "population_definition": {
                "target_population": "privacy survey respondents",
                "unit_of_analysis": "respondent-item decision",
            },
            "questionnaire_or_task": {
                "task_type": "privacy_decision_prediction",
            },
            "segment_variables": ["persona"],
            "actual_targets": [
                {
                    "metric_id": "best_model_accuracy",
                    "label": "Best model accuracy",
                    "value": 0.88,
                    "tolerance": 0.05,
                    "unit": "ratio",
                }
            ],
        }
    )

    assert fixture.data_partition == "holdout"
    assert fixture.evaluation_only is True
    assert fixture.training_allowed is False
    assert fixture.source_reference.sha256 == "a" * 64


def test_holdout_target_fixture_rejects_training_allowed_payload() -> None:
    payload = {
        "fixture_id": "bad_holdout",
        "data_partition": "holdout",
        "evaluation_only": True,
        "training_allowed": True,
        "source_reference": {
            "paper_id": "paper",
            "path": "paper.pdf",
            "sha256": "b" * 64,
            "citation": "Paper.",
            "extraction_notes": "Notes.",
        },
        "population_definition": {},
        "questionnaire_or_task": {},
        "actual_targets": [{"metric_id": "m1", "label": "Metric", "value": 1.0}],
    }

    try:
        HoldoutTargetFixture.model_validate(payload)
    except ValidationError as exc:
        assert "training_allowed" in str(exc)
    else:
        raise AssertionError("Expected training_allowed holdout fixture to fail")


def test_holdout_target_fixture_rejects_missing_targets() -> None:
    payload = {
        "fixture_id": "bad_holdout",
        "data_partition": "holdout",
        "evaluation_only": True,
        "training_allowed": False,
        "source_reference": {
            "paper_id": "paper",
            "path": "paper.pdf",
            "sha256": "c" * 64,
            "citation": "Paper.",
            "extraction_notes": "Notes.",
        },
        "population_definition": {},
        "questionnaire_or_task": {},
        "actual_targets": [],
    }

    try:
        HoldoutTargetFixture.model_validate(payload)
    except ValidationError as exc:
        assert "actual_targets" in str(exc)
    else:
        raise AssertionError("Expected empty holdout targets to fail")


def test_holdout_fixture_author_writes_validated_fixture_with_matching_source_hash(
    tmp_path,
) -> None:
    pdf_path = tmp_path / "research/source_of_truth/holdout_papers/paper.pdf"
    pdf_path.parent.mkdir(parents=True)
    pdf_path.write_bytes(b"%PDF-1.4\n")
    payload = {
        "fixture_id": "holdout_accuracy",
        "data_partition": "holdout",
        "evaluation_only": True,
        "training_allowed": False,
        "source_reference": {
            "paper_id": "paper",
            "path": "research/source_of_truth/holdout_papers/paper.pdf",
            "sha256": "e5c62df5dab5c87b6a015ef3d43597074d1eec433b15f51aec63b8582d0e4ab4",
            "citation": "Paper.",
            "extraction_notes": "Top-line reported result.",
        },
        "population_definition": {},
        "questionnaire_or_task": {},
        "actual_targets": [{"metric_id": "m1", "label": "Metric", "value": 1.0}],
    }

    fixture = HoldoutFixtureAuthor(tmp_path).write_fixture(
        payload=payload,
        output_path=tmp_path / "research/benchmark_program/holdout_targets/holdout_accuracy.json",
    )

    assert fixture.fixture_id == "holdout_accuracy"
    assert (tmp_path / "research/benchmark_program/holdout_targets/holdout_accuracy.json").exists()


def test_holdout_fixture_author_rejects_hash_mismatch(tmp_path) -> None:
    pdf_path = tmp_path / "research/source_of_truth/holdout_papers/paper.pdf"
    pdf_path.parent.mkdir(parents=True)
    pdf_path.write_bytes(b"%PDF-1.4\n")
    payload = {
        "fixture_id": "holdout_accuracy",
        "data_partition": "holdout",
        "evaluation_only": True,
        "training_allowed": False,
        "source_reference": {
            "paper_id": "paper",
            "path": "research/source_of_truth/holdout_papers/paper.pdf",
            "sha256": "0" * 64,
            "citation": "Paper.",
            "extraction_notes": "Top-line reported result.",
        },
        "population_definition": {},
        "questionnaire_or_task": {},
        "actual_targets": [{"metric_id": "m1", "label": "Metric", "value": 1.0}],
    }

    try:
        HoldoutFixtureAuthor(tmp_path).write_fixture(
            payload=payload,
            output_path=tmp_path / "research/benchmark_program/holdout_targets/holdout_accuracy.json",
        )
    except ValueError as exc:
        assert "hash mismatch" in str(exc)
    else:
        raise AssertionError("Expected hash mismatch to fail")
