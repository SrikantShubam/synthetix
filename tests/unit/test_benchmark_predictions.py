from __future__ import annotations

import json
from pathlib import Path

from synthetix.benchmarking.predictions import DevelopmentPredictionEmitter


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_prediction_emitter_creates_payload_without_copying_actual_values(tmp_path: Path) -> None:
    fixture_dir = tmp_path / "fixtures"
    output_dir = tmp_path / "predictions"
    _write_json(
        fixture_dir / "fixture.json",
        {
            "fixture_id": "dev_fixture",
            "population_definition": {"target_sample_size": 123},
            "prediction_contract": {
                "metrics": [
                    {"metric_id": "overall_sample_size", "unit": "count"},
                    {"metric_id": "satisfaction_ratio", "unit": "ratio"},
                ]
            },
            "actual_targets": [
                {
                    "metric_id": "overall_sample_size",
                    "label": "Sample size",
                    "value": 999.0,
                    "unit": "count",
                },
                {
                    "metric_id": "satisfaction_ratio",
                    "label": "Satisfaction",
                    "value": 0.77,
                    "unit": "ratio",
                },
            ],
        },
    )

    summary = DevelopmentPredictionEmitter.emit_directory(
        fixture_dir=fixture_dir,
        output_dir=output_dir,
    )

    payload = json.loads((output_dir / "fixture.json").read_text(encoding="utf-8"))
    assert summary["fixture_count"] == 1
    assert payload["fixture_id"] == "dev_fixture"
    assert payload["predicted_metrics"][0] == {
        "metric_id": "overall_sample_size",
        "value": 123.0,
    }
    assert payload["predicted_metrics"][1] == {
        "metric_id": "satisfaction_ratio",
        "value": 0.24,
    }


def test_prediction_emitter_ignores_reference_values_in_fixture_text() -> None:
    fixture = {
        "fixture_id": "dev_reference_text",
        "population_definition": {"target_sample_size": 861},
        "prediction_contract": {
            "metrics": [
                {"metric_id": "women_satisfaction", "unit": "ratio"},
                {"metric_id": "men_satisfaction", "unit": "ratio"},
                {"metric_id": "nordic_climate_score", "unit": "likert_6"},
                {"metric_id": "lgbtq_discrimination", "unit": "ratio"},
            ]
        },
        "actual_targets": [
            {
                "metric_id": "women_satisfaction",
                "label": "Women satisfied with professional climate",
                "value": 0.15,
                "unit": "ratio",
            },
            {
                "metric_id": "men_satisfaction",
                "label": "Men satisfied with professional climate",
                "value": 0.31,
                "unit": "ratio",
            },
            {
                "metric_id": "nordic_climate_score",
                "label": "Nordic climate score",
                "value": 4.18,
                "unit": "likert_6",
            },
            {
                "metric_id": "lgbtq_discrimination",
                "label": "LGBTQ+ respondents reporting discrimination",
                "value": 0.26,
                "unit": "ratio",
            },
        ],
        "human_reference_summary": {
            "key_results": [
                "15% of women versus 31% of men satisfied with the overall professional climate",
                "over 30% of ethnic minorities and 26% of LGBTQ+ respondents reported discrimination",
                "Nordic countries reported the highest climate score at 4.18 on a 6-point scale",
            ]
        },
    }

    payload = DevelopmentPredictionEmitter.emit_fixture(fixture)

    assert payload["predicted_metrics"] == [
        {"metric_id": "women_satisfaction", "value": 0.19},
        {"metric_id": "men_satisfaction", "value": 0.29},
        {"metric_id": "nordic_climate_score", "value": 4.1},
        {"metric_id": "lgbtq_discrimination", "value": 0.28},
    ]


def test_prediction_emitter_ignores_calibration_clues() -> None:
    fixture = {
        "fixture_id": "dev_subgroup",
        "prediction_contract": {
            "metrics": [
                {"metric_id": "women_satisfaction_gap_vs_men", "unit": "delta_ratio"}
            ]
        },
        "actual_targets": [
            {
                "metric_id": "women_satisfaction_gap_vs_men",
                "label": "Women-vs-men satisfaction gap",
                "value": -0.16,
                "unit": "delta_ratio",
            }
        ],
        "calibration_clues": {
            "women_satisfaction_gap_vs_men": -0.16,
        },
    }

    payload = DevelopmentPredictionEmitter.emit_fixture(fixture)

    assert payload["predicted_metrics"] == [
        {"metric_id": "women_satisfaction_gap_vs_men", "value": -0.12}
    ]


def test_prediction_emitter_ignores_registry_policy_metrics() -> None:
    fixture = {
        "fixture_id": "val_registry",
        "population_definition": {"target_sample_size": 4},
        "prediction_contract": {
            "metrics": [
                {"metric_id": "registry_entry_count", "unit": "count"},
                {"metric_id": "restricted_registry_entries", "unit": "count"},
                {"metric_id": "public_registry_entries", "unit": "count"},
                {"metric_id": "download_permitted_entries", "unit": "count"},
                {"metric_id": "registration_required_entries", "unit": "count"},
            ]
        },
        "registry_summary": {
            "registry_entry_count": 4,
            "restricted_registry_entries": 3,
            "public_registry_entries": 1,
            "download_permitted_entries": 0,
            "registration_required_entries": 3,
        },
        "actual_targets": [
            {"metric_id": "registry_entry_count", "label": "Entries", "value": 4, "unit": "count"},
            {
                "metric_id": "restricted_registry_entries",
                "label": "Restricted",
                "value": 3,
                "unit": "count",
            },
            {"metric_id": "public_registry_entries", "label": "Public", "value": 1, "unit": "count"},
            {
                "metric_id": "download_permitted_entries",
                "label": "Download permitted",
                "value": 0,
                "unit": "count",
            },
            {
                "metric_id": "registration_required_entries",
                "label": "Registration required",
                "value": 3,
                "unit": "count",
            },
        ],
    }

    payload = DevelopmentPredictionEmitter.emit_fixture(fixture)

    assert payload["predicted_metrics"] == [
        {"metric_id": "registry_entry_count", "value": 4.0},
        {"metric_id": "restricted_registry_entries", "value": 4.0},
        {"metric_id": "public_registry_entries", "value": 4.0},
        {"metric_id": "download_permitted_entries", "value": 4.0},
        {"metric_id": "registration_required_entries", "value": 4.0},
    ]


def test_prediction_emitter_rejects_fixture_without_prediction_contract(tmp_path: Path) -> None:
    fixture_dir = tmp_path / "fixtures"
    output_dir = tmp_path / "predictions"
    _write_json(fixture_dir / "fixture.json", {"fixture_id": "dev_fixture"})

    try:
        DevelopmentPredictionEmitter.emit_directory(
            fixture_dir=fixture_dir,
            output_dir=output_dir,
        )
    except ValueError as exc:
        assert "prediction_contract" in str(exc)
    else:
        raise AssertionError("Expected fixture without prediction_contract to fail")


def test_prediction_emitter_skips_manifest_files(tmp_path: Path) -> None:
    fixture_dir = tmp_path / "fixtures"
    output_dir = tmp_path / "predictions"
    _write_json(fixture_dir / "manifest.json", {"fixtures": []})
    _write_json(
        fixture_dir / "fixture.json",
        {
            "fixture_id": "dev_fixture",
            "prediction_contract": {"metrics": [{"metric_id": "ratio_metric", "unit": "ratio"}]},
            "actual_targets": [{"metric_id": "ratio_metric", "label": "Ratio", "value": 0.2, "unit": "ratio"}],
        },
    )

    summary = DevelopmentPredictionEmitter.emit_directory(
        fixture_dir=fixture_dir,
        output_dir=output_dir,
    )

    assert summary["fixture_count"] == 1
    assert not (output_dir / "manifest.json").exists()


def test_prediction_emitter_uses_registry_source_document_instead_of_registry_summary(
    tmp_path: Path,
) -> None:
    workspace = tmp_path
    registry_path = workspace / "docs/benchmarks/registry.json"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(
        json.dumps(
            {
                "version": "1.0",
                "entries": [
                    {
                        "benchmark_id": "public",
                        "access_tier": "public",
                        "restricted_data": False,
                        "download_permitted": False,
                    },
                    {
                        "benchmark_id": "restricted_a",
                        "access_tier": "registration_required",
                        "restricted_data": True,
                        "download_permitted": False,
                    },
                    {
                        "benchmark_id": "restricted_b",
                        "access_tier": "registration_required",
                        "restricted_data": True,
                        "download_permitted": False,
                    },
                    {
                        "benchmark_id": "restricted_c",
                        "access_tier": "registration_required",
                        "restricted_data": True,
                        "download_permitted": False,
                    },
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    fixture = {
        "fixture_id": "val_registry",
        "source_documents": ["docs/benchmarks/registry.json"],
        "prediction_contract": {
            "metrics": [
                {"metric_id": "registry_entry_count", "unit": "count"},
                {"metric_id": "restricted_registry_entries", "unit": "count"},
                {"metric_id": "public_registry_entries", "unit": "count"},
                {"metric_id": "download_permitted_entries", "unit": "count"},
                {"metric_id": "registration_required_entries", "unit": "count"},
            ]
        },
        "registry_summary": {
            "registry_entry_count": 999,
            "restricted_registry_entries": 999,
            "public_registry_entries": 999,
            "download_permitted_entries": 999,
            "registration_required_entries": 999,
        },
    }

    payload = DevelopmentPredictionEmitter.emit_fixture(fixture, workspace=workspace)

    assert payload["predicted_metrics"] == [
        {"metric_id": "registry_entry_count", "value": 4.0},
        {"metric_id": "restricted_registry_entries", "value": 3.0},
        {"metric_id": "public_registry_entries", "value": 1.0},
        {"metric_id": "download_permitted_entries", "value": 0.0},
        {"metric_id": "registration_required_entries", "value": 3.0},
    ]


def test_prediction_emitter_uses_conservative_semantic_priors_without_answer_keys() -> None:
    fixture = {
        "fixture_id": "dev_privacy",
        "questionnaire_or_task": {
            "task_type": "persona-conditioned survey response replication",
        },
        "reported_findings_template": [
            "persona prompting does not yield a clear aggregate improvement",
            "some items and underrepresented subgroups experience disproportionate distortions",
        ],
        "prediction_contract": {
            "metrics": [
                {"metric_id": "human_accuracy", "unit": "ratio"},
                {"metric_id": "best_model_accuracy", "unit": "ratio"},
                {"metric_id": "women_satisfaction_gap_vs_men", "unit": "delta_ratio"},
                {"metric_id": "lgbtq_discrimination", "unit": "ratio"},
                {"metric_id": "nordic_climate_score", "unit": "likert_6"},
            ]
        },
        "actual_targets": [
            {"metric_id": "human_accuracy", "label": "Human", "value": 0.99, "unit": "ratio"},
            {"metric_id": "best_model_accuracy", "label": "Model", "value": 0.01, "unit": "ratio"},
            {"metric_id": "women_satisfaction_gap_vs_men", "label": "Gap", "value": -0.99, "unit": "delta_ratio"},
            {"metric_id": "lgbtq_discrimination", "label": "Discrimination", "value": 0.99, "unit": "ratio"},
            {"metric_id": "nordic_climate_score", "label": "Score", "value": 1.0, "unit": "likert_6"},
        ],
    }

    payload = DevelopmentPredictionEmitter.emit_fixture(fixture)

    assert payload["predicted_metrics"] == [
        {"metric_id": "human_accuracy", "value": 0.82},
        {"metric_id": "best_model_accuracy", "value": 0.62},
        {"metric_id": "women_satisfaction_gap_vs_men", "value": -0.12},
        {"metric_id": "lgbtq_discrimination", "value": 0.28},
        {"metric_id": "nordic_climate_score", "value": 4.1},
    ]


def test_prediction_emitter_uses_wvs_value_question_prior_without_answer_keys() -> None:
    fixture = {
        "fixture_id": "dev_wvs_values",
        "source_strategy": "development-only WVS-derived values survey",
        "population_definition": {
            "target_population": "cross-cultural respondents represented through WVS wave 7",
            "target_sample_size": 93312,
        },
        "questionnaire_or_task": {
            "task_type": "survey_response_replication",
            "example_constructs": [
                "institutional trust",
                "technology optimism",
                "fairness perceptions",
                "religiosity and traditional versus secular-rational orientation",
                "survival versus self-expression values",
            ],
        },
        "prediction_contract": {
            "metrics": [
                {"metric_id": "value_question_count", "unit": "count"},
            ]
        },
        "actual_targets": [
            {"metric_id": "value_question_count", "label": "Value question count", "value": 999, "unit": "count"}
        ],
        "human_reference_summary": {
            "reported_sample_or_scale": "answer-bearing text must be ignored"
        },
    }

    payload = DevelopmentPredictionEmitter.emit_fixture(fixture)

    assert payload["predicted_metrics"] == [
        {"metric_id": "value_question_count", "value": 36.0},
    ]
