from pathlib import Path

from _pytest.monkeypatch import MonkeyPatch
from typer.testing import CliRunner

from synthetix.cli.app import app


def test_cli_validates_blueprint(tmp_path: Path) -> None:
    path = tmp_path / "survey.yaml"
    path.write_text(
        """
title: CLI survey
purpose: Verify CLI validation.
population:
  size: 2
  seed: 1
questions:
  - type: open_text
    id: q1
    prompt: What matters?
""".strip(),
        encoding="utf-8",
    )
    result = CliRunner().invoke(app, ["validate", str(path)])
    assert result.exit_code == 0
    assert "valid" in result.stdout.lower()


def test_cli_benchmark_loop_commands_persist_and_advance(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "research/benchmark_program/development").mkdir(parents=True)
    (tmp_path / "research/benchmark_program/validation").mkdir(parents=True)
    (tmp_path / "research/source_of_truth").mkdir(parents=True)
    (tmp_path / "research/benchmark_program/manifest.json").write_text(
        """
{
  "splits": {
    "development": {"path": "research/benchmark_program/development"},
    "validation": {"path": "research/benchmark_program/validation"},
    "holdout": {"path": "research/source_of_truth/holdout_papers"}
  }
}
""".strip(),
        encoding="utf-8",
    )
    (tmp_path / "research/benchmark_program/development/manifest.json").write_text(
        """
{
  "fixtures": [
    {
      "fixture_id": "dev_fixture_1",
      "path": "research/benchmark_program/development/dev_fixture_1.json"
    }
  ]
}
""".strip(),
        encoding="utf-8",
    )
    (tmp_path / "research/benchmark_program/development/dev_fixture_1.json").write_text(
        '{"fixture_id":"dev_fixture_1","instance_status":"authoring_complete"}',
        encoding="utf-8",
    )
    (tmp_path / "research/source_of_truth/manifest.json").write_text(
        '{"policy":{"forbidden_uses":["training"]}}',
        encoding="utf-8",
    )

    runner = CliRunner()
    state_path = tmp_path / "loop-state.json"

    init_result = runner.invoke(app, ["benchmark-loop-init", "--state", str(state_path)])
    assert init_result.exit_code == 0
    assert "create_validation_fixtures" in init_result.stdout

    next_result = runner.invoke(app, ["benchmark-loop-next", "--state", str(state_path)])
    assert next_result.exit_code == 0
    assert "create_validation_fixtures" in next_result.stdout

    complete_result = runner.invoke(
        app,
        ["benchmark-loop-complete", "create_validation_fixtures", "--state", str(state_path)],
    )
    assert complete_result.exit_code == 0
    assert "implement_benchmark_runtime" in complete_result.stdout


def test_cli_benchmark_compare_generates_actual_vs_predicted_report(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    fixture_path = tmp_path / "fixture.json"
    predicted_path = tmp_path / "predicted.json"
    output_path = tmp_path / "comparison.json"
    fixture_path.write_text(
        """
{
  "fixture_id": "dev_fixture_accuracy",
  "actual_targets": [
    {"metric_id": "human_accuracy", "label": "Human accuracy", "value": 0.87, "tolerance": 0.05}
  ]
}
""".strip(),
        encoding="utf-8",
    )
    predicted_path.write_text(
        """
{
  "fixture_id": "dev_fixture_accuracy",
  "predicted_metrics": [
    {"metric_id": "human_accuracy", "value": 0.83}
  ]
}
""".strip(),
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        app,
        [
            "benchmark-compare",
            str(fixture_path),
            str(predicted_path),
            "--output",
            str(output_path),
        ],
    )

    assert result.exit_code == 0
    assert "dev_fixture_accuracy" in result.stdout
    assert "mean_absolute_error" in result.stdout
    assert output_path.exists()


def test_cli_benchmark_compare_development_batches_reports(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    fixture_dir = tmp_path / "fixtures"
    predicted_dir = tmp_path / "predicted"
    output_dir = tmp_path / "comparisons"
    fixture_dir.mkdir()
    predicted_dir.mkdir()
    (fixture_dir / "dev_fixture_1.json").write_text(
        """
{
  "fixture_id": "dev_fixture_1",
  "actual_targets": [
    {"metric_id": "m1", "label": "Metric 1", "value": 0.5, "tolerance": 0.1}
  ]
}
""".strip(),
        encoding="utf-8",
    )
    (predicted_dir / "dev_fixture_1.json").write_text(
        """
{
  "fixture_id": "dev_fixture_1",
  "predicted_metrics": [
    {"metric_id": "m1", "value": 0.45}
  ]
}
""".strip(),
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        app,
        [
            "benchmark-compare-development",
            "--fixtures",
            str(fixture_dir),
            "--predicted-dir",
            str(predicted_dir),
            "--output-dir",
            str(output_dir),
        ],
    )

    assert result.exit_code == 0
    assert "fixture_count" in result.stdout
    assert (output_dir / "summary.json").exists()


def test_cli_benchmark_predict_development_emits_predictions(tmp_path: Path) -> None:
    runner = CliRunner()
    fixture_dir = tmp_path / "fixtures"
    output_dir = tmp_path / "predictions"
    fixture_dir.mkdir()
    (fixture_dir / "fixture.json").write_text(
        """
{
  "fixture_id": "dev_fixture",
  "population_definition": {"target_sample_size": 42},
  "actual_targets": [
    {"metric_id": "overall_sample_size", "label": "Sample size", "value": 42.0, "unit": "count"}
  ]
}
""".strip(),
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "benchmark-predict-development",
            "--fixtures",
            str(fixture_dir),
            "--output-dir",
            str(output_dir),
        ],
    )

    assert result.exit_code == 0
    assert "fixture_count" in result.stdout
    assert (output_dir / "fixture.json").exists()


def test_cli_orchestrator_loop_commands_persist_and_advance(tmp_path: Path) -> None:
    runner = CliRunner()
    state_path = tmp_path / "orchestrator-state.json"

    next_result = runner.invoke(app, ["orchestrator-next", "--state", str(state_path)])
    assert next_result.exit_code == 0
    assert "00-product-goals" in next_result.stdout
    assert "gpt-5.4" in next_result.stdout

    fail_result = runner.invoke(
        app,
        [
            "orchestrator-record",
            "00-product-goals",
            "--state",
            str(state_path),
            "--failed",
            "--note",
            "review failed",
        ],
    )
    assert fail_result.exit_code == 0
    assert "rejected_attempts" in fail_result.stdout

    pass_result = runner.invoke(
        app,
        [
            "orchestrator-record",
            "00-product-goals",
            "--state",
            str(state_path),
            "--artifact",
            "goals.md",
            "--artifact",
            "docs/specs/00-product-goals.md",
        ],
    )
    assert pass_result.exit_code == 0
    assert "completed_specs" in pass_result.stdout


def test_cli_orchestrator_run_writes_progress_until_blocked(tmp_path: Path) -> None:
    runner = CliRunner()
    state_path = tmp_path / "orchestrator-state.json"
    progress_path = tmp_path / "progress.md"

    result = runner.invoke(
        app,
        [
            "orchestrator-run",
            "--state",
            str(state_path),
            "--progress",
            str(progress_path),
            "--max-steps",
            "10",
        ],
    )

    assert result.exit_code == 0
    assert "blocked_task" in result.stdout
    assert "02-pipeline-predicted-metrics" in result.stdout
    assert progress_path.exists()
