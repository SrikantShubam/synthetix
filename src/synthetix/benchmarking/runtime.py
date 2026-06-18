from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field, model_validator


class ActualTarget(BaseModel):
    metric_id: str
    label: str
    value: float
    tolerance: float = 0.05
    unit: str = "ratio"


class PredictedMetric(BaseModel):
    metric_id: str
    value: float


class BenchmarkFixture(BaseModel):
    fixture_id: str
    actual_targets: list[ActualTarget] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_targets(self) -> "BenchmarkFixture":
        if not self.actual_targets:
            raise ValueError("Fixture must include at least one actual target")
        return self


class PredictedOutcome(BaseModel):
    fixture_id: str
    predicted_metrics: list[PredictedMetric] = Field(default_factory=list)


class MetricComparison(BaseModel):
    metric_id: str
    label: str
    unit: str
    tolerance: float
    actual_value: float
    predicted_value: float
    signed_error: float
    absolute_error: float
    within_tolerance: bool


class ComparisonSummary(BaseModel):
    total_metrics: int
    within_tolerance_count: int
    mean_absolute_error: float
    max_absolute_error: float
    score: float


class BenchmarkComparisonReport(BaseModel):
    fixture_id: str
    comparisons: list[MetricComparison]
    summary: ComparisonSummary


class BenchmarkComparator:
    @classmethod
    def compare_files(
        cls,
        *,
        fixture_path: Path,
        predicted_path: Path,
        output_path: Path | None = None,
    ) -> BenchmarkComparisonReport:
        fixture = BenchmarkFixture.model_validate_json(fixture_path.read_text(encoding="utf-8"))
        predicted = PredictedOutcome.model_validate_json(
            predicted_path.read_text(encoding="utf-8")
        )
        report = cls.compare(fixture=fixture, predicted=predicted)
        if output_path is not None:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
        return report

    @staticmethod
    def compare(
        *,
        fixture: BenchmarkFixture,
        predicted: PredictedOutcome,
    ) -> BenchmarkComparisonReport:
        if fixture.fixture_id != predicted.fixture_id:
            raise ValueError(
                f"Fixture id mismatch: expected '{fixture.fixture_id}', got '{predicted.fixture_id}'"
            )
        predicted_map = {metric.metric_id: metric for metric in predicted.predicted_metrics}
        comparisons: list[MetricComparison] = []

        for target in fixture.actual_targets:
            prediction = predicted_map.get(target.metric_id)
            if prediction is None:
                raise ValueError(
                    f"Missing predicted metric '{target.metric_id}' for fixture '{fixture.fixture_id}'"
                )
            signed_error = round(prediction.value - target.value, 6)
            absolute_error = round(abs(signed_error), 6)
            comparisons.append(
                MetricComparison(
                    metric_id=target.metric_id,
                    label=target.label,
                    unit=target.unit,
                    tolerance=target.tolerance,
                    actual_value=target.value,
                    predicted_value=prediction.value,
                    signed_error=signed_error,
                    absolute_error=absolute_error,
                    within_tolerance=absolute_error <= target.tolerance,
                )
            )

        total_metrics = len(comparisons)
        within_tolerance_count = sum(1 for item in comparisons if item.within_tolerance)
        mean_absolute_error = round(
            sum(item.absolute_error for item in comparisons) / total_metrics, 4
        )
        max_absolute_error = round(max(item.absolute_error for item in comparisons), 4)
        score = round(within_tolerance_count / total_metrics, 4)
        return BenchmarkComparisonReport(
            fixture_id=fixture.fixture_id,
            comparisons=comparisons,
            summary=ComparisonSummary(
                total_metrics=total_metrics,
                within_tolerance_count=within_tolerance_count,
                mean_absolute_error=mean_absolute_error,
                max_absolute_error=max_absolute_error,
                score=score,
            ),
        )

    @classmethod
    def compare_directory(
        cls,
        *,
        fixture_dir: Path,
        predicted_dir: Path,
        output_dir: Path,
    ) -> dict[str, object]:
        reports: list[BenchmarkComparisonReport] = []
        output_dir.mkdir(parents=True, exist_ok=True)
        for fixture_path in sorted(fixture_dir.glob("*.json")):
            payload = read_json(fixture_path)
            if "fixture_id" not in payload:
                continue
            fixture = BenchmarkFixture.model_validate_json(fixture_path.read_text(encoding="utf-8"))
            predicted_path = predicted_dir / fixture_path.name
            if not predicted_path.exists():
                raise ValueError(
                    f"Missing predicted payload '{predicted_path.name}' for fixture '{fixture.fixture_id}'"
                )
            report = cls.compare_files(
                fixture_path=fixture_path,
                predicted_path=predicted_path,
                output_path=output_dir / fixture_path.name,
            )
            reports.append(report)

        summary = {
            "fixture_count": len(reports),
            "reports": [report.model_dump(mode="json") for report in reports],
        }
        (output_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        return summary


def read_json(path: Path) -> dict[str, object]:
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError(f"Expected JSON object in '{path}'")
    return {str(key): value for key, value in loaded.items()}
