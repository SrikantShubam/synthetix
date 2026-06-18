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
        "value": 0.5,
    }


def test_prediction_emitter_extracts_reference_values_from_fixture_text(tmp_path: Path) -> None:
    fixture = {
        "fixture_id": "dev_reference_text",
        "population_definition": {"target_sample_size": 861},
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
        {"metric_id": "women_satisfaction", "value": 0.15},
        {"metric_id": "men_satisfaction", "value": 0.31},
        {"metric_id": "nordic_climate_score", "value": 4.18},
        {"metric_id": "lgbtq_discrimination", "value": 0.26},
    ]


def test_prediction_emitter_uses_calibration_clues_without_actual_target_values() -> None:
    fixture = {
        "fixture_id": "dev_subgroup",
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
        {"metric_id": "women_satisfaction_gap_vs_men", "value": -0.16}
    ]


def test_prediction_emitter_rejects_fixture_without_targets(tmp_path: Path) -> None:
    fixture_dir = tmp_path / "fixtures"
    output_dir = tmp_path / "predictions"
    _write_json(fixture_dir / "fixture.json", {"fixture_id": "dev_fixture"})

    try:
        DevelopmentPredictionEmitter.emit_directory(
            fixture_dir=fixture_dir,
            output_dir=output_dir,
        )
    except ValueError as exc:
        assert "actual_targets" in str(exc)
    else:
        raise AssertionError("Expected fixture without targets to fail")


def test_prediction_emitter_skips_manifest_files(tmp_path: Path) -> None:
    fixture_dir = tmp_path / "fixtures"
    output_dir = tmp_path / "predictions"
    _write_json(fixture_dir / "manifest.json", {"fixtures": []})
    _write_json(
        fixture_dir / "fixture.json",
        {
            "fixture_id": "dev_fixture",
            "actual_targets": [
                {"metric_id": "ratio_metric", "label": "Ratio", "value": 0.2, "unit": "ratio"}
            ],
        },
    )

    summary = DevelopmentPredictionEmitter.emit_directory(
        fixture_dir=fixture_dir,
        output_dir=output_dir,
    )

    assert summary["fixture_count"] == 1
    assert not (output_dir / "manifest.json").exists()
