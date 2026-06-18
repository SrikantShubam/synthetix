from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field


class PromptPacket(BaseModel):
    task_id: str
    title: str
    instruction: str
    allowed_targets: list[str] = Field(default_factory=list)
    forbidden_targets: list[str] = Field(default_factory=list)


class LoopState(BaseModel):
    completed_tasks: list[str] = Field(default_factory=list)
    next_task_id: str


class BenchmarkLoop:
    def __init__(
        self,
        *,
        workspace: Path,
        state_path: Path | None = None,
    ) -> None:
        self.workspace = workspace
        self.state_path = state_path
        self.program_manifest = self._read_json(
            workspace / "research/benchmark_program/manifest.json"
        )
        self.development_manifest = self._read_json(
            workspace / "research/benchmark_program/development/manifest.json"
        )
        self.holdout_manifest = self._read_json(workspace / "research/source_of_truth/manifest.json")
        self.state = self._load_state()

    @classmethod
    def for_workspace(
        cls,
        workspace: Path,
        *,
        state_path: Path | None = None,
    ) -> "BenchmarkLoop":
        return cls(workspace=workspace, state_path=state_path)

    def next_packet(self) -> PromptPacket:
        task_id = self.state.next_task_id
        return _task_catalog()[task_id]

    def complete(self, task_id: str) -> LoopState:
        if task_id != self.state.next_task_id:
            raise ValueError(f"Expected task '{self.state.next_task_id}', got '{task_id}'")
        completed = [*self.state.completed_tasks, task_id]
        next_task_id = _next_task_after(task_id)
        self.state = LoopState(completed_tasks=completed, next_task_id=next_task_id)
        self._save_state()
        return self.state

    def _load_state(self) -> LoopState:
        if self.state_path and self.state_path.exists():
            return LoopState.model_validate_json(self.state_path.read_text(encoding="utf-8"))
        return LoopState(completed_tasks=[], next_task_id=self._detect_next_task())

    def _save_state(self) -> None:
        if self.state_path is None:
            return
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(self.state.model_dump_json(indent=2), encoding="utf-8")

    def _detect_next_task(self) -> str:
        development_done = self._all_fixtures_complete(
            self.development_manifest.get("fixtures", [])
        )
        validation_dir = self.workspace / "research/benchmark_program/validation"
        validation_files = list(validation_dir.glob("*.json"))
        development_result_dir = self.workspace / "data/benchmark-results/development"
        development_reports = list(development_result_dir.glob("*.json"))
        if not development_done:
            return "author_development_fixtures"
        if not validation_files:
            return "create_validation_fixtures"
        if "implement_benchmark_runtime" not in self._existing_state_tasks():
            return "implement_benchmark_runtime"
        if not development_reports:
            return "compare_development_predictions"
        return "run_validation_benchmarks"

    def _existing_state_tasks(self) -> list[str]:
        return list(self.state.completed_tasks) if hasattr(self, "state") else []

    def _all_fixtures_complete(self, fixtures: object) -> bool:
        if not isinstance(fixtures, list) or not fixtures:
            return False
        for fixture in fixtures:
            if not isinstance(fixture, dict):
                return False
            fixture_path = self.workspace / str(fixture.get("path", ""))
            if not fixture_path.exists():
                return False
            payload = self._read_json(fixture_path)
            if payload.get("instance_status") != "authoring_complete":
                return False
        return True

    @staticmethod
    def _read_json(path: Path) -> dict[str, object]:
        loaded = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            raise ValueError(f"Expected JSON object in '{path}'")
        return {str(key): value for key, value in loaded.items()}


def _task_catalog() -> dict[str, PromptPacket]:
    return {
        "author_development_fixtures": PromptPacket(
            task_id="author_development_fixtures",
            title="Author development fixtures",
            instruction=(
                "Populate development fixtures from non-holdout sources, ensuring each fixture "
                "has concrete population, subgroup, task, and reported-finding fields."
            ),
            allowed_targets=["development"],
            forbidden_targets=["holdout"],
        ),
        "create_validation_fixtures": PromptPacket(
            task_id="create_validation_fixtures",
            title="Create validation fixtures",
            instruction=(
                "Create 2-4 validation fixtures from sources that do not overlap with the locked "
                "holdout set and are not identical to development targets."
            ),
            allowed_targets=["validation"],
            forbidden_targets=["holdout"],
        ),
        "implement_benchmark_runtime": PromptPacket(
            task_id="implement_benchmark_runtime",
            title="Implement benchmark runtime",
            instruction=(
                "Implement benchmark ingestion, comparison, and report generation for development "
                "and validation fixtures without permitting training or optimization on holdout."
            ),
            allowed_targets=["src", "tests", "development", "validation"],
            forbidden_targets=["holdout"],
        ),
        "compare_development_predictions": PromptPacket(
            task_id="compare_development_predictions",
            title="Compare development predictions",
            instruction=(
                "Run the pipeline against development fixtures, record actual-vs-predicted metric "
                "comparisons, and write benchmark reports before touching validation or holdout."
            ),
            allowed_targets=["development", "data", "reports"],
            forbidden_targets=["holdout"],
        ),
        "run_validation_benchmarks": PromptPacket(
            task_id="run_validation_benchmarks",
            title="Run validation benchmarks",
            instruction=(
                "Run validation fixtures, record comparison metrics, and prepare the system for a "
                "future holdout evaluation without adapting against the holdout set."
            ),
            allowed_targets=["validation", "data", "reports"],
            forbidden_targets=["holdout"],
        ),
        "holdout_ready": PromptPacket(
            task_id="holdout_ready",
            title="Holdout ready",
            instruction=(
                "The benchmark loop has finished development and validation preparation. "
                "The next manual decision is whether to freeze the system and run the locked holdout."
            ),
            allowed_targets=["holdout"],
            forbidden_targets=[],
        ),
    }


def _next_task_after(task_id: str) -> str:
    order = [
        "author_development_fixtures",
        "create_validation_fixtures",
        "implement_benchmark_runtime",
        "compare_development_predictions",
        "run_validation_benchmarks",
        "holdout_ready",
    ]
    try:
        index = order.index(task_id)
    except ValueError as exc:
        raise ValueError(f"Unknown task '{task_id}'") from exc
    return order[min(index + 1, len(order) - 1)]
