from __future__ import annotations

import json
from pathlib import Path

from synthetix.benchmarking.loop import BenchmarkLoop, LoopState


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _program_manifest() -> dict[str, object]:
    return {
        "splits": {
            "development": {"path": "research/benchmark_program/development"},
            "validation": {"path": "research/benchmark_program/validation"},
            "holdout": {"path": "research/source_of_truth/holdout_papers"},
        }
    }


def _development_manifest() -> dict[str, object]:
    return {
        "fixtures": [
            {
                "fixture_id": "dev_fixture_1",
                "path": "research/benchmark_program/development/dev_fixture_1.json",
            }
        ]
    }


def _holdout_manifest() -> dict[str, object]:
    return {
        "policy": {
            "forbidden_uses": [
                "training",
                "self_improvement_against_same_holdout",
            ]
        }
    }


def test_benchmark_loop_detects_next_task_from_repo_state(tmp_path: Path) -> None:
    _write_json(tmp_path / "research/benchmark_program/manifest.json", _program_manifest())
    _write_json(
        tmp_path / "research/benchmark_program/development/manifest.json",
        _development_manifest(),
    )
    _write_json(
        tmp_path / "research/benchmark_program/development/dev_fixture_1.json",
        {"fixture_id": "dev_fixture_1", "instance_status": "authoring_complete"},
    )
    _write_json(tmp_path / "research/source_of_truth/manifest.json", _holdout_manifest())

    loop = BenchmarkLoop.for_workspace(tmp_path)
    packet = loop.next_packet()

    assert packet.task_id == "create_validation_fixtures"
    assert "holdout" in packet.forbidden_targets
    assert "validation" in packet.allowed_targets


def test_benchmark_loop_advances_after_completion(tmp_path: Path) -> None:
    _write_json(tmp_path / "research/benchmark_program/manifest.json", _program_manifest())
    _write_json(
        tmp_path / "research/benchmark_program/development/manifest.json",
        _development_manifest(),
    )
    _write_json(
        tmp_path / "research/benchmark_program/development/dev_fixture_1.json",
        {"fixture_id": "dev_fixture_1", "instance_status": "authoring_complete"},
    )
    _write_json(
        tmp_path / "research/benchmark_program/validation/val_fixture_1.json",
        {"fixture_id": "val_fixture_1", "instance_status": "authoring_complete"},
    )
    _write_json(tmp_path / "research/source_of_truth/manifest.json", _holdout_manifest())

    loop = BenchmarkLoop.for_workspace(tmp_path)
    packet = loop.next_packet()
    assert packet.task_id == "implement_benchmark_runtime"

    advanced = loop.complete(packet.task_id)

    assert isinstance(advanced, LoopState)
    assert advanced.completed_tasks == ["implement_benchmark_runtime"]
    assert advanced.next_task_id == "compare_development_predictions"


def test_benchmark_loop_persists_state(tmp_path: Path) -> None:
    _write_json(tmp_path / "research/benchmark_program/manifest.json", _program_manifest())
    _write_json(
        tmp_path / "research/benchmark_program/development/manifest.json",
        _development_manifest(),
    )
    _write_json(
        tmp_path / "research/benchmark_program/development/dev_fixture_1.json",
        {"fixture_id": "dev_fixture_1", "instance_status": "authoring_complete"},
    )
    _write_json(tmp_path / "research/source_of_truth/manifest.json", _holdout_manifest())
    state_path = tmp_path / "data/benchmark-loop-state.json"

    loop = BenchmarkLoop.for_workspace(tmp_path, state_path=state_path)
    loop.complete(loop.next_packet().task_id)

    saved = json.loads(state_path.read_text(encoding="utf-8"))
    assert saved["completed_tasks"] == ["create_validation_fixtures"]
    assert saved["next_task_id"] == "implement_benchmark_runtime"


def test_benchmark_loop_detects_development_comparison_task(tmp_path: Path) -> None:
    _write_json(tmp_path / "research/benchmark_program/manifest.json", _program_manifest())
    _write_json(
        tmp_path / "research/benchmark_program/development/manifest.json",
        _development_manifest(),
    )
    _write_json(
        tmp_path / "research/benchmark_program/development/dev_fixture_1.json",
        {"fixture_id": "dev_fixture_1", "instance_status": "authoring_complete"},
    )
    _write_json(
        tmp_path / "research/benchmark_program/validation/val_fixture_1.json",
        {"fixture_id": "val_fixture_1", "instance_status": "authoring_complete"},
    )
    _write_json(tmp_path / "research/source_of_truth/manifest.json", _holdout_manifest())
    state_path = tmp_path / "data/benchmark-loop-state.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps(
            {
                "completed_tasks": ["implement_benchmark_runtime"],
                "next_task_id": "compare_development_predictions",
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    loop = BenchmarkLoop.for_workspace(tmp_path, state_path=state_path)
    packet = loop.next_packet()

    assert packet.task_id == "compare_development_predictions"
