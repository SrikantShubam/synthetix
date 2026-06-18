from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from synthetix.benchmarking.runtime import BenchmarkComparator


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_benchmark_comparator_reports_actual_vs_predicted(tmp_path: Path) -> None:
    fixture_path = tmp_path / "fixture.json"
    predicted_path = tmp_path / "predicted.json"
    output_path = tmp_path / "comparison.json"

    _write_json(
        fixture_path,
        {
            "fixture_id": "dev_fixture_accuracy",
            "actual_targets": [
                {
                    "metric_id": "human_accuracy",
                    "label": "Human benchmark accuracy",
                    "value": 0.87,
                    "tolerance": 0.05,
                },
                {
                    "metric_id": "best_model_accuracy",
                    "label": "Best model accuracy",
                    "value": 0.617,
                    "tolerance": 0.05,
                },
            ],
        },
    )
    _write_json(
        predicted_path,
        {
            "fixture_id": "dev_fixture_accuracy",
            "predicted_metrics": [
                {"metric_id": "human_accuracy", "value": 0.84},
                {"metric_id": "best_model_accuracy", "value": 0.60},
            ],
        },
    )

    report = BenchmarkComparator.compare_files(
        fixture_path=fixture_path,
        predicted_path=predicted_path,
        output_path=output_path,
    )

    assert report.fixture_id == "dev_fixture_accuracy"
    assert report.summary.total_metrics == 2
    assert report.summary.within_tolerance_count == 2
    assert report.summary.mean_absolute_error == 0.0235
    assert output_path.exists()

    saved = json.loads(output_path.read_text(encoding="utf-8"))
    assert saved["summary"]["mean_absolute_error"] == 0.0235
    assert saved["comparisons"][0]["actual_value"] == 0.87
    assert saved["comparisons"][0]["predicted_value"] == 0.84


def test_benchmark_comparator_rejects_missing_predicted_metric(tmp_path: Path) -> None:
    fixture_path = tmp_path / "fixture.json"
    predicted_path = tmp_path / "predicted.json"

    _write_json(
        fixture_path,
        {
            "fixture_id": "dev_fixture_accuracy",
            "actual_targets": [
                {"metric_id": "human_accuracy", "label": "Human benchmark accuracy", "value": 0.87}
            ],
        },
    )
    _write_json(
        predicted_path,
        {"fixture_id": "dev_fixture_accuracy", "predicted_metrics": []},
    )

    try:
        BenchmarkComparator.compare_files(
            fixture_path=fixture_path,
            predicted_path=predicted_path,
        )
    except ValueError as exc:
        assert "human_accuracy" in str(exc)
    else:
        raise AssertionError("Expected comparator to reject missing predicted metric")


def test_benchmark_comparator_batch_compares_a_directory(tmp_path: Path) -> None:
    fixture_dir = tmp_path / "fixtures"
    predicted_dir = tmp_path / "predicted"
    output_dir = tmp_path / "comparisons"
    _write_json(
        fixture_dir / "dev_fixture_1.json",
        {
            "fixture_id": "dev_fixture_1",
            "actual_targets": [
                {"metric_id": "m1", "label": "Metric 1", "value": 0.5, "tolerance": 0.1}
            ],
        },
    )
    _write_json(
        predicted_dir / "dev_fixture_1.json",
        {"fixture_id": "dev_fixture_1", "predicted_metrics": [{"metric_id": "m1", "value": 0.45}]},
    )

    batch = BenchmarkComparator.compare_directory(
        fixture_dir=fixture_dir,
        predicted_dir=predicted_dir,
        output_dir=output_dir,
    )
    reports = cast(list[dict[str, object]], batch["reports"])

    assert batch["fixture_count"] == 1
    assert reports[0]["fixture_id"] == "dev_fixture_1"
    assert cast(dict[str, object], reports[0]["summary"])["mean_absolute_error"] == 0.05
    assert (output_dir / "dev_fixture_1.json").exists()
    assert (output_dir / "summary.json").exists()


def test_benchmark_comparator_batch_skips_manifest_files(tmp_path: Path) -> None:
    fixture_dir = tmp_path / "fixtures"
    predicted_dir = tmp_path / "predicted"
    output_dir = tmp_path / "comparisons"
    _write_json(fixture_dir / "manifest.json", {"fixtures": []})
    _write_json(
        fixture_dir / "dev_fixture_1.json",
        {
            "fixture_id": "dev_fixture_1",
            "actual_targets": [
                {"metric_id": "m1", "label": "Metric 1", "value": 0.5, "tolerance": 0.1}
            ],
        },
    )
    _write_json(
        predicted_dir / "dev_fixture_1.json",
        {"fixture_id": "dev_fixture_1", "predicted_metrics": [{"metric_id": "m1", "value": 0.45}]},
    )

    batch = BenchmarkComparator.compare_directory(
        fixture_dir=fixture_dir,
        predicted_dir=predicted_dir,
        output_dir=output_dir,
    )

    assert batch["fixture_count"] == 1
    assert not (output_dir / "manifest.json").exists()
