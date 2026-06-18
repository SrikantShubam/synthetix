from __future__ import annotations

import json
from pathlib import Path

from synthetix.benchmarking.frozen import FrozenEvaluation


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_freeze_creates_manifest_with_code_and_policy_hashes(tmp_path: Path) -> None:
    workspace = tmp_path
    _write_json(workspace / "goals.md", {"goal": "sandbox"})
    _write_json(workspace / "research/source_of_truth/manifest.json", {"policy": {"forbidden_uses": ["training"]}})
    _write_json(
        workspace / "research/benchmark_program/validation/fixture.json",
        {
            "fixture_id": "validation_fixture",
            "actual_targets": [
                {"metric_id": "m1", "label": "Metric 1", "value": 0.5, "tolerance": 0.1}
            ],
        },
    )

    manifest = FrozenEvaluation.for_workspace(workspace).freeze(
        split="validation",
        output_path=workspace / "data/frozen-evaluations/validation/freeze-manifest.json",
    )

    assert manifest.split == "validation"
    assert manifest.status == "frozen"
    assert "research/source_of_truth/manifest.json" in manifest.artifact_hashes
    assert "research/benchmark_program/validation/fixture.json" in manifest.artifact_hashes
    assert manifest.forbidden_after_freeze == [
        "prediction_logic",
        "benchmark_thresholds",
        "prompt_templates",
        "fixtures",
        "source_of_truth",
    ]


def test_holdout_prediction_requires_existing_freeze_manifest(tmp_path: Path) -> None:
    workspace = tmp_path
    _write_json(
        workspace / "research/source_of_truth/holdout_papers/holdout_fixture.json",
        {
            "fixture_id": "holdout_fixture",
            "actual_targets": [
                {"metric_id": "m1", "label": "Metric 1", "value": 0.5, "tolerance": 0.1}
            ],
        },
    )

    try:
        FrozenEvaluation.for_workspace(workspace).emit_predictions(
            split="holdout",
            output_dir=workspace / "data/benchmark-predictions/holdout",
        )
    except ValueError as exc:
        assert "freeze manifest" in str(exc)
    else:
        raise AssertionError("Expected holdout prediction without freeze to fail")


def test_evaluate_writes_comparison_and_quality_summary(tmp_path: Path) -> None:
    workspace = tmp_path
    _write_json(workspace / "research/source_of_truth/manifest.json", {"policy": {"forbidden_uses": ["training"]}})
    _write_json(
        workspace / "research/benchmark_program/validation/fixture.json",
        {
            "fixture_id": "validation_fixture",
            "population_definition": {"target_sample_size": 10},
            "actual_targets": [
                {"metric_id": "overall_sample_size", "label": "Sample size", "value": 10, "tolerance": 0, "unit": "count"}
            ],
        },
    )
    evaluator = FrozenEvaluation.for_workspace(workspace)
    evaluator.freeze(
        split="validation",
        output_path=workspace / "data/frozen-evaluations/validation/freeze-manifest.json",
    )
    evaluator.emit_predictions(
        split="validation",
        output_dir=workspace / "data/benchmark-predictions/validation",
    )

    result = evaluator.evaluate(
        split="validation",
        predicted_dir=workspace / "data/benchmark-predictions/validation",
        output_dir=workspace / "data/benchmark-results/validation",
        quality_output=workspace / "data/frozen-evaluations/validation/quality-summary.json",
    )

    assert result.quality_status == "passed"
    assert result.average_score == 1.0
    assert result.min_fixture_score == 1.0
    assert (workspace / "data/benchmark-results/validation/summary.json").exists()
    quality = json.loads(
        (workspace / "data/frozen-evaluations/validation/quality-summary.json").read_text(
            encoding="utf-8"
        )
    )
    assert quality["scientific_proof_ready"] is False
    assert "consumer_report_quality" in quality["remaining_review_gates"]


def test_evaluate_rejects_changed_frozen_artifacts(tmp_path: Path) -> None:
    workspace = tmp_path
    prediction_logic = workspace / "src/synthetix/benchmarking/predictions.py"
    prediction_logic.parent.mkdir(parents=True)
    prediction_logic.write_text("version = 1\n", encoding="utf-8")
    _write_json(workspace / "research/source_of_truth/manifest.json", {"policy": {}})
    _write_json(
        workspace / "research/benchmark_program/validation/fixture.json",
        {
            "fixture_id": "validation_fixture",
            "population_definition": {"target_sample_size": 10},
            "actual_targets": [
                {"metric_id": "overall_sample_size", "label": "Sample size", "value": 10, "tolerance": 0, "unit": "count"}
            ],
        },
    )
    evaluator = FrozenEvaluation.for_workspace(workspace)
    evaluator.freeze(
        split="validation",
        output_path=workspace / "data/frozen-evaluations/validation/freeze-manifest.json",
    )
    prediction_logic.write_text("version = 2\n", encoding="utf-8")

    try:
        evaluator.emit_predictions(
            split="validation",
            output_dir=workspace / "data/benchmark-predictions/validation",
        )
    except ValueError as exc:
        assert "changed after freeze" in str(exc)
    else:
        raise AssertionError("Expected changed frozen artifact to block prediction")


def test_holdout_freeze_hashes_pdf_assets(tmp_path: Path) -> None:
    workspace = tmp_path
    _write_json(workspace / "research/source_of_truth/manifest.json", {"policy": {}})
    pdf_path = workspace / "research/source_of_truth/holdout_papers/paper.pdf"
    pdf_path.parent.mkdir(parents=True)
    pdf_path.write_bytes(b"%PDF-1.4\n")

    manifest = FrozenEvaluation.for_workspace(workspace).freeze(
        split="holdout",
        output_path=workspace / "data/frozen-evaluations/holdout/freeze-manifest.json",
    )

    assert "research/source_of_truth/holdout_papers/paper.pdf" in manifest.artifact_hashes
