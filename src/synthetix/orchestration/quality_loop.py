from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field


class QualityTarget(BaseModel):
    min_average_score: float = 0.8
    min_fixture_score: float = 0.7
    require_report_artifacts: bool = True


class QualityMetrics(BaseModel):
    fixture_count: int
    average_score: float
    min_fixture_score: float
    failing_fixtures: list[str] = Field(default_factory=list)
    report_artifacts_present: bool


class QualityTask(BaseModel):
    task_id: str
    assigned_model: str
    goal: str
    allowed_paths: list[str]
    forbidden_paths: list[str]
    acceptance_checks: list[str]


class QualityLoopState(BaseModel):
    iterations: int = 0
    status: str = "pending"
    last_reason: str = ""
    active_task: QualityTask | None = None
    metrics: QualityMetrics | None = None


class QualityLoopResult(BaseModel):
    passed: bool
    reason: str
    metrics: QualityMetrics
    next_task: QualityTask | None
    state: QualityLoopState


class QualityLoop:
    def __init__(
        self,
        *,
        workspace: Path,
        state_path: Path,
        progress_path: Path,
        target: QualityTarget | None = None,
    ) -> None:
        self.workspace = workspace
        self.state_path = state_path
        self.progress_path = progress_path
        self.target = target or QualityTarget()
        self.state = self._load_state()

    @classmethod
    def for_workspace(
        cls,
        workspace: Path,
        *,
        state_path: Path,
        progress_path: Path,
        target: QualityTarget | None = None,
    ) -> "QualityLoop":
        return cls(
            workspace=workspace,
            state_path=state_path,
            progress_path=progress_path,
            target=target,
        )

    def run_once(self) -> QualityLoopResult:
        metrics = self._load_metrics()
        next_task = self._next_task(metrics)
        passed = next_task is None
        reason = "Quality target met" if passed else self._reason(metrics, next_task)
        self.state.iterations += 1
        self.state.status = "passed" if passed else "active"
        self.state.last_reason = reason
        self.state.active_task = next_task
        self.state.metrics = metrics
        self._save_state()
        self._append_progress(metrics, reason, next_task)
        return QualityLoopResult(
            passed=passed,
            reason=reason,
            metrics=metrics,
            next_task=next_task,
            state=self.state,
        )

    def _next_task(self, metrics: QualityMetrics) -> QualityTask | None:
        if metrics.average_score < self.target.min_average_score:
            return self._prediction_task()
        if metrics.min_fixture_score < self.target.min_fixture_score:
            return self._prediction_task()
        if self.target.require_report_artifacts and not metrics.report_artifacts_present:
            return QualityTask(
                task_id="improve-professional-report",
                assigned_model="gpt-5.4",
                goal="Produce complete professional report artifacts and quality evidence.",
                allowed_paths=["src/synthetix/reporting", "src/synthetix/analysis", "tests"],
                forbidden_paths=["research/source_of_truth", "data/benchmark-results/holdout"],
                acceptance_checks=["report_artifacts", "report_quality", "unit_tests"],
            )
        return None

    def _prediction_task(self) -> QualityTask:
        return QualityTask(
            task_id="improve-predicted-metrics",
            assigned_model="gpt-5.4-mini",
            goal=(
                "Replace neutral development predictions with simulation-derived predicted_metrics "
                "until benchmark scores meet the configured quality target."
            ),
            allowed_paths=[
                "src/synthetix/benchmarking",
                "src/synthetix/analysis",
                "tests",
                "data/benchmark-predictions",
                "data/benchmark-results",
            ],
            forbidden_paths=["research/source_of_truth", "data/benchmark-results/holdout"],
            acceptance_checks=["benchmark_comparison", "quality_target", "unit_tests", "integration_tests"],
        )

    def _reason(self, metrics: QualityMetrics, task: QualityTask | None) -> str:
        if task is None:
            return "Quality target met"
        reasons: list[str] = []
        if metrics.average_score < self.target.min_average_score:
            reasons.append(
                f"average score {metrics.average_score} below target {self.target.min_average_score}"
            )
        if metrics.min_fixture_score < self.target.min_fixture_score:
            reasons.append(
                f"minimum fixture score {metrics.min_fixture_score} below target "
                f"{self.target.min_fixture_score}"
            )
        if self.target.require_report_artifacts and not metrics.report_artifacts_present:
            reasons.append("professional report artifacts missing")
        return "; ".join(reasons)

    def _load_metrics(self) -> QualityMetrics:
        summary_path = self.workspace / "data/benchmark-results/development/summary.json"
        if not summary_path.exists():
            return QualityMetrics(
                fixture_count=0,
                average_score=0.0,
                min_fixture_score=0.0,
                failing_fixtures=["development_summary_missing"],
                report_artifacts_present=self._report_artifacts_present(),
            )
        summary = self._read_json(summary_path)
        reports = summary.get("reports", [])
        if not isinstance(reports, list) or not reports:
            return QualityMetrics(
                fixture_count=0,
                average_score=0.0,
                min_fixture_score=0.0,
                failing_fixtures=["development_reports_missing"],
                report_artifacts_present=self._report_artifacts_present(),
            )
        scores: list[float] = []
        failing: list[str] = []
        for report in reports:
            if not isinstance(report, dict):
                continue
            fixture_id = str(report.get("fixture_id", "unknown"))
            report_summary = report.get("summary")
            if not isinstance(report_summary, dict):
                failing.append(fixture_id)
                scores.append(0.0)
                continue
            score = float(report_summary.get("score", 0.0))
            scores.append(score)
            if score < self.target.min_fixture_score:
                failing.append(fixture_id)
        average_score = round(sum(scores) / len(scores), 4)
        return QualityMetrics(
            fixture_count=len(scores),
            average_score=average_score,
            min_fixture_score=round(min(scores), 4),
            failing_fixtures=failing,
            report_artifacts_present=self._report_artifacts_present(),
        )

    def _report_artifacts_present(self) -> bool:
        required = {"report.json", "report.html", "report.pdf", "checksums.json"}
        data_dir = self.workspace / "data"
        if not data_dir.exists():
            return False
        return any(
            required.issubset({path.name for path in run_dir.iterdir() if path.is_file()})
            for run_dir in data_dir.glob("**")
            if run_dir.is_dir()
        )

    def _load_state(self) -> QualityLoopState:
        if self.state_path.exists():
            return QualityLoopState.model_validate_json(self.state_path.read_text(encoding="utf-8"))
        return QualityLoopState()

    def _save_state(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(self.state.model_dump_json(indent=2), encoding="utf-8")

    def _append_progress(
        self,
        metrics: QualityMetrics,
        reason: str,
        task: QualityTask | None,
    ) -> None:
        self.progress_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.progress_path.exists():
            self.progress_path.write_text("# Quality Loop Progress\n\n", encoding="utf-8")
        with self.progress_path.open("a", encoding="utf-8") as progress_file:
            progress_file.write(f"## Iteration {self.state.iterations}\n\n")
            progress_file.write(f"- average score: `{metrics.average_score}`\n")
            progress_file.write(f"- minimum fixture score: `{metrics.min_fixture_score}`\n")
            progress_file.write(f"- failing fixtures: `{', '.join(metrics.failing_fixtures)}`\n")
            progress_file.write(f"- report artifacts present: `{metrics.report_artifacts_present}`\n")
            progress_file.write(f"- reason: {reason}\n")
            if task is not None:
                progress_file.write(f"- next task: `{task.task_id}`\n")
                progress_file.write(f"- assigned model: `{task.assigned_model}`\n")
            progress_file.write("\n")

    @staticmethod
    def _read_json(path: Path) -> dict[str, object]:
        loaded = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            raise ValueError(f"Expected JSON object in '{path}'")
        return {str(key): value for key, value in loaded.items()}
