from __future__ import annotations

import json
from pathlib import Path

from synthetix.orchestration.quality_loop import QualityLoop, QualityTarget


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_quality_loop_blocks_until_benchmark_scores_meet_target(tmp_path: Path) -> None:
    summary_path = tmp_path / "data/benchmark-results/development/summary.json"
    _write_json(
        summary_path,
        {
            "fixture_count": 2,
            "reports": [
                {"fixture_id": "a", "summary": {"score": 0.5, "mean_absolute_error": 0.2}},
                {"fixture_id": "b", "summary": {"score": 1.0, "mean_absolute_error": 0.0}},
            ],
        },
    )
    loop = QualityLoop.for_workspace(
        tmp_path,
        state_path=tmp_path / "data/quality-loop-state.json",
        progress_path=tmp_path / "docs/progress/quality-loop-progress.md",
        target=QualityTarget(
            min_average_score=0.8,
            min_fixture_score=0.7,
            require_report_artifacts=False,
        ),
    )

    result = loop.run_once()

    assert result.passed is False
    assert result.next_task is not None
    assert result.next_task.task_id == "improve-predicted-metrics"
    assert result.next_task.assigned_model == "gpt-5.4-mini"
    assert "below target" in result.reason
    assert (tmp_path / "docs/progress/quality-loop-progress.md").exists()


def test_quality_loop_passes_when_benchmark_scores_meet_target(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "data/benchmark-results/development/summary.json",
        {
            "fixture_count": 2,
            "reports": [
                {"fixture_id": "a", "summary": {"score": 0.9, "mean_absolute_error": 0.02}},
                {"fixture_id": "b", "summary": {"score": 0.8, "mean_absolute_error": 0.04}},
            ],
        },
    )
    loop = QualityLoop.for_workspace(
        tmp_path,
        state_path=tmp_path / "data/quality-loop-state.json",
        progress_path=tmp_path / "docs/progress/quality-loop-progress.md",
        target=QualityTarget(
            min_average_score=0.8,
            min_fixture_score=0.7,
            require_report_artifacts=False,
        ),
    )

    result = loop.run_once()

    assert result.passed is True
    assert result.next_task is None
    assert result.metrics.average_score == 0.85


def test_quality_loop_uses_report_task_when_report_artifacts_missing(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "data/benchmark-results/development/summary.json",
        {
            "fixture_count": 1,
            "reports": [{"fixture_id": "a", "summary": {"score": 1.0, "mean_absolute_error": 0.0}}],
        },
    )
    loop = QualityLoop.for_workspace(
        tmp_path,
        state_path=tmp_path / "data/quality-loop-state.json",
        progress_path=tmp_path / "docs/progress/quality-loop-progress.md",
        target=QualityTarget(require_report_artifacts=True),
    )

    result = loop.run_once()

    assert result.passed is False
    assert result.next_task is not None
    assert result.next_task.task_id == "improve-professional-report"
    assert result.next_task.assigned_model == "gpt-5.4"


def test_quality_loop_creates_repair_task_for_failed_report_hard_gates(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "data/benchmark-results/development/summary.json",
        {
            "fixture_count": 1,
            "reports": [{"fixture_id": "a", "summary": {"score": 1.0, "mean_absolute_error": 0.0}}],
        },
    )
    report_dir = tmp_path / "data/run-1"
    report_dir.mkdir(parents=True)
    for name in ("report.json", "report.html", "report.pdf", "checksums.json"):
        (report_dir / name).write_text("present", encoding="utf-8")
    _write_json(
        report_dir / "quality.json",
        {
            "accepted": False,
            "hard_gates": [
                {"name": "typed_answer_integrity", "passed": True},
                {"name": "professional_report_depth", "passed": False},
                {"name": "qualitative_reasoning_depth", "passed": False},
            ],
        },
    )
    loop = QualityLoop.for_workspace(
        tmp_path,
        state_path=tmp_path / "data/quality-loop-state.json",
        progress_path=tmp_path / "docs/progress/quality-loop-progress.md",
        target=QualityTarget(require_report_artifacts=True),
    )

    result = loop.run_once()

    assert result.passed is False
    assert result.next_task is not None
    assert result.next_task.task_id == "repair-professional-report-quality"
    assert result.next_task.assigned_model == "gpt-5.4"
    assert result.metrics.failed_report_gates == [
        "professional_report_depth",
        "qualitative_reasoning_depth",
    ]
    assert "professional_report_depth" in result.reason
