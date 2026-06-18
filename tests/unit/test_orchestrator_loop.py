from __future__ import annotations

import json
from pathlib import Path

import pytest

from synthetix.orchestration.loop import (
    AgentModel,
    OrchestratorLoop,
    OrchestratorTask,
    TaskStatus,
    VerificationResult,
)


REQUIRED_SPEC_IDS = [
    "00-product-goals",
    "01-benchmark-thresholds",
    "02-pipeline-predicted-metrics",
    "03-professional-report-pdf",
    "04-transparent-simulation-dashboard",
    "05-validation-and-holdout-readiness",
    "06-agent-orchestrator-loop",
]


def _write_minimal_orchestrator_workspace(path: Path) -> None:
    path.mkdir(parents=True)
    (path / "goals.md").write_text("# Goals\n", encoding="utf-8")
    (path / "docs/specs").mkdir(parents=True)
    for spec_id in REQUIRED_SPEC_IDS:
        (path / "docs/specs" / f"{spec_id}.md").write_text(
            f"# {spec_id}\n\n## Acceptance Criteria\n\n- Present.\n",
            encoding="utf-8",
        )
    (path / "src/synthetix/benchmarking").mkdir(parents=True)
    (path / "src/synthetix/benchmarking/classifier.py").write_text(
        "# classifier marker\n",
        encoding="utf-8",
    )
    (path / "src/synthetix/reporting").mkdir(parents=True)
    (path / "src/synthetix/reporting/quality.py").write_text(
        "# quality marker\n",
        encoding="utf-8",
    )
    (path / "src/synthetix/analysis").mkdir(parents=True)
    (path / "src/synthetix/web").mkdir(parents=True)
    (path / "tests/unit").mkdir(parents=True)
    (path / "tests/integration").mkdir(parents=True)


def test_required_goal_and_spec_files_exist() -> None:
    assert Path("goals.md").exists()
    for spec_id in REQUIRED_SPEC_IDS:
        path = Path("docs/specs") / f"{spec_id}.md"
        assert path.exists(), f"Missing {path}"
        text = path.read_text(encoding="utf-8")
        assert "# " in text
        assert "Acceptance" in text


def test_orchestrator_selects_first_incomplete_spec_task(tmp_path: Path) -> None:
    loop = OrchestratorLoop.for_workspace(Path.cwd(), state_path=tmp_path / "state.json")

    task = loop.next_task()

    assert task.spec_id == "00-product-goals"
    assert task.assigned_model == AgentModel.GPT_5_4
    assert task.allowed_paths == ["goals.md", "docs/specs/00-product-goals.md"]
    assert "research/source_of_truth" in task.forbidden_paths
    assert "spec_presence" in task.acceptance_checks


def test_orchestrator_rejects_holdout_paths_except_holdout_readiness() -> None:
    task = OrchestratorTask(
        spec_id="02-pipeline-predicted-metrics",
        task_id="02-pipeline-predicted-metrics",
        title="Pipeline predicted metrics",
        assigned_model=AgentModel.GPT_5_4_MINI,
        allowed_paths=["research/source_of_truth/holdout_papers/example.pdf"],
        forbidden_paths=[],
        acceptance_checks=["tests"],
    )

    with pytest.raises(ValueError, match="holdout"):
        OrchestratorLoop.validate_task_policy(task)


def test_orchestrator_rejects_mini_model_for_judgment_specs() -> None:
    task = OrchestratorTask(
        spec_id="01-benchmark-thresholds",
        task_id="01-benchmark-thresholds",
        title="Benchmark thresholds",
        assigned_model=AgentModel.GPT_5_4_MINI,
        allowed_paths=["docs/specs/01-benchmark-thresholds.md"],
        forbidden_paths=[],
        acceptance_checks=["tests"],
    )

    with pytest.raises(ValueError, match="GPT-5.4"):
        OrchestratorLoop.validate_task_policy(task)


def test_orchestrator_keeps_task_active_after_failed_verification(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"
    loop = OrchestratorLoop.for_workspace(Path.cwd(), state_path=state_path)
    task = loop.next_task()

    state = loop.record_verification(
        task.task_id,
        VerificationResult(
            passed=False,
            checks={"unit_tests": False},
            review_notes=["unit tests failed"],
            artifact_paths=[],
        ),
    )

    assert state.active_task_id == task.task_id
    assert state.completed_specs == []
    assert state.rejected_attempts[0].task_id == task.task_id
    assert "unit tests failed" in state.rejected_attempts[0].review_notes


def test_orchestrator_completes_task_after_passing_verification(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"
    loop = OrchestratorLoop.for_workspace(Path.cwd(), state_path=state_path)
    task = loop.next_task()

    state = loop.record_verification(
        task.task_id,
        VerificationResult(
            passed=True,
            checks={"spec_presence": True, "unit_tests": True},
            review_notes=["accepted"],
            artifact_paths=["goals.md", "docs/specs/00-product-goals.md"],
        ),
    )

    assert state.completed_specs == ["00-product-goals"]
    assert state.active_task_id is None
    assert state.accepted_artifacts == ["goals.md", "docs/specs/00-product-goals.md"]
    saved = json.loads(state_path.read_text(encoding="utf-8"))
    assert saved["completed_specs"] == ["00-product-goals"]


def test_orchestrator_run_until_blocked_writes_progress_and_stops_on_real_gap(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    _write_minimal_orchestrator_workspace(workspace)
    state_path = tmp_path / "state.json"
    progress_path = tmp_path / "progress.md"
    loop = OrchestratorLoop.for_workspace(
        workspace,
        state_path=state_path,
        progress_path=progress_path,
    )

    result = loop.run_until_blocked(max_steps=10)

    assert result.completed_count == 2
    assert result.blocked_task is not None
    assert result.blocked_task.spec_id == "02-pipeline-predicted-metrics"
    assert "benchmark_comparison" in result.blocked_reason
    assert loop.state.completed_specs == ["00-product-goals", "01-benchmark-thresholds"]
    assert loop.state.active_task_id == "02-pipeline-predicted-metrics"
    progress = progress_path.read_text(encoding="utf-8")
    assert "00-product-goals" in progress
    assert "02-pipeline-predicted-metrics" in progress
    assert "blocked" in progress.lower()


def test_orchestrator_dispatch_packet_contains_agent_runner_context(tmp_path: Path) -> None:
    loop = OrchestratorLoop.for_workspace(Path.cwd(), state_path=tmp_path / "state.json")

    packet = loop.dispatch_packet(loop.next_task())

    assert packet["assigned_model"] == "gpt-5.4"
    assert "implementation_prompt" in packet
    assert "spec_review_prompt" in packet
    assert "code_quality_prompt" in packet
    assert "allowed_paths" in packet
    assert "forbidden_paths" in packet


def test_orchestrator_marks_blocked_task_status_in_state(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    _write_minimal_orchestrator_workspace(workspace)
    loop = OrchestratorLoop.for_workspace(workspace, state_path=tmp_path / "state.json")

    result = loop.run_until_blocked(max_steps=10)

    assert result.blocked_task is not None
    assert result.blocked_task.status == TaskStatus.BLOCKED
    assert loop.state.last_verification is not None
    assert loop.state.last_verification.passed is False
