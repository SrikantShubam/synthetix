from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from synthetix.benchmarking.predictions import DevelopmentPredictionEmitter
from synthetix.benchmarking.runtime import BenchmarkComparator

EvaluationSplit = Literal["validation", "holdout"]


class FrozenManifest(BaseModel):
    split: EvaluationSplit
    status: Literal["frozen"] = "frozen"
    manifest_path: str
    frozen_at_utc: str
    artifact_hashes: dict[str, str] = Field(default_factory=dict)
    forbidden_after_freeze: list[str] = Field(default_factory=list)
    policy: dict[str, object] = Field(default_factory=dict)


class FrozenQualitySummary(BaseModel):
    split: EvaluationSplit
    quality_status: Literal["passed", "failed"]
    fixture_count: int
    average_score: float
    min_fixture_score: float
    failing_fixtures: list[str]
    scientific_proof_ready: bool
    remaining_review_gates: list[str]
    comparison_summary_path: str
    freeze_manifest_path: str


class FrozenEvaluation:
    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace

    @classmethod
    def for_workspace(cls, workspace: Path) -> "FrozenEvaluation":
        return cls(workspace.resolve())

    def freeze(self, *, split: EvaluationSplit, output_path: Path) -> FrozenManifest:
        manifest = FrozenManifest(
            split=split,
            manifest_path=self._relative(output_path),
            frozen_at_utc=datetime.now(UTC).replace(microsecond=0).isoformat(),
            artifact_hashes=self._artifact_hashes(split),
            forbidden_after_freeze=[
                "prediction_logic",
                "benchmark_thresholds",
                "prompt_templates",
                "fixtures",
                "source_of_truth",
            ],
            policy=self._read_policy(),
        )
        self._write_model(output_path, manifest)
        return manifest

    def emit_predictions(self, *, split: EvaluationSplit, output_dir: Path) -> dict[str, object]:
        self._assert_freeze_integrity(split)
        fixture_dir = self._fixture_dir(split)
        return DevelopmentPredictionEmitter.emit_directory(
            fixture_dir=fixture_dir,
            output_dir=output_dir,
        )

    def evaluate(
        self,
        *,
        split: EvaluationSplit,
        predicted_dir: Path,
        output_dir: Path,
        quality_output: Path,
        min_average_score: float = 0.8,
        min_fixture_score: float = 0.7,
    ) -> FrozenQualitySummary:
        freeze_manifest = self._assert_freeze_integrity(split)
        summary = BenchmarkComparator.compare_directory(
            fixture_dir=self._fixture_dir(split),
            predicted_dir=predicted_dir,
            output_dir=output_dir,
        )
        quality = self._quality_summary(
            split=split,
            summary=summary,
            min_average_score=min_average_score,
            min_fixture_score=min_fixture_score,
            comparison_summary_path=output_dir / "summary.json",
            freeze_manifest_path=freeze_manifest,
        )
        self._write_model(quality_output, quality)
        return quality

    def _fixture_dir(self, split: EvaluationSplit) -> Path:
        if split == "validation":
            return self.workspace / "research/benchmark_program/validation"
        return self.workspace / "research/source_of_truth/holdout_papers"

    def _freeze_manifest_path(self, split: EvaluationSplit) -> Path:
        return self.workspace / f"data/frozen-evaluations/{split}/freeze-manifest.json"

    def _require_freeze(self, split: EvaluationSplit) -> Path:
        manifest_path = self._freeze_manifest_path(split)
        if not manifest_path.exists():
            raise ValueError(
                f"Cannot run {split} predictions or evaluation without a freeze manifest at "
                f"'{manifest_path}'. Freeze first and do not tune after seeing results."
            )
        return manifest_path

    def _assert_freeze_integrity(self, split: EvaluationSplit) -> Path:
        manifest_path = self._require_freeze(split)
        manifest = FrozenManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
        changed: list[str] = []
        missing: list[str] = []
        for relative_path, expected_hash in manifest.artifact_hashes.items():
            path = self.workspace / relative_path
            if not path.exists():
                missing.append(relative_path)
                continue
            actual_hash = hashlib.sha256(path.read_bytes()).hexdigest()
            if actual_hash != expected_hash:
                changed.append(relative_path)
        if changed or missing:
            details = []
            if changed:
                details.append(f"changed after freeze: {', '.join(changed)}")
            if missing:
                details.append(f"missing after freeze: {', '.join(missing)}")
            raise ValueError("; ".join(details))
        return manifest_path

    def _artifact_hashes(self, split: EvaluationSplit) -> dict[str, str]:
        paths = [
            self.workspace / "goals.md",
            self.workspace / "research/source_of_truth/manifest.json",
            self.workspace / "src/synthetix/benchmarking/predictions.py",
            self.workspace / "src/synthetix/benchmarking/runtime.py",
            self.workspace / "src/synthetix/benchmarking/frozen.py",
        ]
        paths.extend(sorted(path for path in self._fixture_dir(split).rglob("*") if path.is_file()))
        hashes: dict[str, str] = {}
        for path in paths:
            if path.exists() and path.is_file():
                hashes[self._relative(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
        return hashes

    def _read_policy(self) -> dict[str, object]:
        policy_path = self.workspace / "research/source_of_truth/manifest.json"
        if not policy_path.exists():
            return {}
        loaded = json.loads(policy_path.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            return {}
        policy = loaded.get("policy")
        return policy if isinstance(policy, dict) else {}

    def _quality_summary(
        self,
        *,
        split: EvaluationSplit,
        summary: dict[str, object],
        min_average_score: float,
        min_fixture_score: float,
        comparison_summary_path: Path,
        freeze_manifest_path: Path,
    ) -> FrozenQualitySummary:
        reports = summary.get("reports", [])
        if not isinstance(reports, list):
            reports = []
        scores: list[tuple[str, float]] = []
        for report in reports:
            if not isinstance(report, dict):
                continue
            fixture_id = str(report.get("fixture_id", "unknown"))
            report_summary = report.get("summary")
            if not isinstance(report_summary, dict):
                continue
            score = report_summary.get("score", 0.0)
            if isinstance(score, int | float):
                scores.append((fixture_id, float(score)))

        fixture_count = len(scores)
        average_score = round(sum(score for _, score in scores) / fixture_count, 4) if scores else 0.0
        min_score = round(min((score for _, score in scores), default=0.0), 4)
        failing = [fixture_id for fixture_id, score in scores if score < min_fixture_score]
        passed = fixture_count > 0 and average_score >= min_average_score and not failing
        remaining_review_gates = [
            "consumer_report_quality",
            "one_shot_holdout_interpretation",
            "no_post_result_tuning_attestation",
        ]
        return FrozenQualitySummary(
            split=split,
            quality_status="passed" if passed else "failed",
            fixture_count=fixture_count,
            average_score=average_score,
            min_fixture_score=min_score,
            failing_fixtures=failing,
            scientific_proof_ready=False,
            remaining_review_gates=remaining_review_gates,
            comparison_summary_path=self._relative(comparison_summary_path),
            freeze_manifest_path=self._relative(freeze_manifest_path),
        )

    def _write_model(self, path: Path, model: BaseModel) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(model.model_dump_json(indent=2), encoding="utf-8")

    def _relative(self, path: Path) -> str:
        try:
            return path.resolve().relative_to(self.workspace).as_posix()
        except ValueError:
            return path.as_posix()
