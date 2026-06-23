from __future__ import annotations

import json
from pathlib import Path

import pytest

from synthetix.benchmarking.golden_path import generate_golden_path_proof
from synthetix.orchestration.loop import (
    AgentModel,
    OrchestratorLoop,
    OrchestratorTask,
    TaskStatus,
    VerificationResult,
)
from synthetix.orchestration.intake_review import review_golden_path_workspace


REQUIRED_SPEC_IDS = [
    "00-product-goals",
    "01-benchmark-thresholds",
    "02-pipeline-predicted-metrics",
    "03-professional-report-pdf",
    "04-transparent-simulation-dashboard",
    "05-validation-and-holdout-readiness",
    "06-agent-orchestrator-loop",
    "07-honest-predictor-improvement",
    "08-rich-reporting-upgrade",
    "09-research-design-study-plan",
    "10-golden-path-intake-reset",
    "11-report-chart-quality-recovery",
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


def test_orchestrator_selects_first_new_packet_after_existing_specs_complete(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"
    state_path.write_text(
        json.dumps(
            {
                "completed_specs": REQUIRED_SPEC_IDS[:7],
                "active_task_id": None,
                "rejected_attempts": [],
                "accepted_artifacts": [],
                "last_verification": None,
            }
        ),
        encoding="utf-8",
    )
    loop = OrchestratorLoop.for_workspace(Path.cwd(), state_path=state_path)

    task = loop.next_task()

    assert task.spec_id == "07-honest-predictor-improvement"
    assert task.assigned_model == AgentModel.GPT_5_4
    assert "benchmark_comparison" in task.acceptance_checks
    assert "unit_tests" in task.acceptance_checks


def test_orchestrator_exposes_research_design_task_after_reporting_upgrade(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"
    state_path.write_text(
        json.dumps(
            {
                "completed_specs": REQUIRED_SPEC_IDS[:9],
                "active_task_id": None,
                "rejected_attempts": [],
                "accepted_artifacts": [],
                "last_verification": None,
            }
        ),
        encoding="utf-8",
    )
    loop = OrchestratorLoop.for_workspace(Path.cwd(), state_path=state_path)

    task = loop.next_task()

    assert task.spec_id == "09-research-design-study-plan"
    assert task.assigned_model == AgentModel.GPT_5_4
    assert task.acceptance_checks == [
        "research_design_schema",
        "study_plan_validation",
        "standards_alignment_checklist",
        "prompt_contract_tests",
        "report_objective_coverage",
        "professional_report_quality",
        "unit_tests",
        "integration_tests",
        "policy_gates",
    ]


def test_orchestrator_exposes_contract_fixture_proof_review_task(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"
    state_path.write_text(
        json.dumps(
            {
                "completed_specs": REQUIRED_SPEC_IDS[:10],
                "active_task_id": None,
                "rejected_attempts": [],
                "accepted_artifacts": [],
                "last_verification": None,
            }
        ),
        encoding="utf-8",
    )
    loop = OrchestratorLoop.for_workspace(Path.cwd(), state_path=state_path)

    task = loop.next_task()

    assert task.spec_id == "10-golden-path-intake-reset"
    assert task.assigned_model == AgentModel.GPT_5_4
    assert task.acceptance_checks == [
        "contract_extraction",
        "fixture_design",
        "proof_generation",
        "review",
        "unit_tests",
        "integration_tests",
        "policy_gates",
    ]


def test_orchestrator_exposes_report_chart_recovery_task_after_golden_path_reset(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"
    state_path.write_text(
        json.dumps(
            {
                "completed_specs": REQUIRED_SPEC_IDS[:11],
                "active_task_id": None,
                "rejected_attempts": [],
                "accepted_artifacts": [],
                "last_verification": None,
            }
        ),
        encoding="utf-8",
    )
    loop = OrchestratorLoop.for_workspace(Path.cwd(), state_path=state_path)

    task = loop.next_task()

    assert task.spec_id == "11-report-chart-quality-recovery"
    assert task.assigned_model == AgentModel.GPT_5_4
    assert task.acceptance_checks == [
        "report_quality",
        "report_artifacts",
        "unit_tests",
        "integration_tests",
        "policy_gates",
    ]


def test_orchestrator_rejects_example_golden_path_report_stub(tmp_path: Path) -> None:
    generate_golden_path_proof(Path.cwd(), output_dir=tmp_path / "golden-path")
    report_json = tmp_path / "golden-path" / "report-proof" / "report.json"
    report = json.loads(report_json.read_text(encoding="utf-8"))
    report["run_id"] = "example"
    report["title"] = "Synthetic scenario exploration"
    report["provenance"]["model_id"] = "example/model"
    report_json.write_text(json.dumps(report, indent=2), encoding="utf-8")

    loop = OrchestratorLoop.for_workspace(
        tmp_path / "golden-path",
        state_path=tmp_path / "golden-path" / "state.json",
    )

    assert loop._check_acceptance(
        loop._task_catalog()["10-golden-path-intake-reset"],
        "proof_generation",
    ) is False


def test_golden_path_review_rejects_sparse_contract_evidence(tmp_path: Path) -> None:
    proof = generate_golden_path_proof(Path.cwd(), output_dir=tmp_path / "golden-path")
    professional = next(
        item for item in proof.proofs if item.fixture_class == "professional_survey_dry_run"
    )
    comparison_path = tmp_path / "golden-path" / professional.comparison_path
    comparison = json.loads(comparison_path.read_text(encoding="utf-8"))
    comparison["fields"][0]["evidence_snippets"] = []
    comparison["fields"][0]["substantive_evidence"] = False
    comparison["fields"][0]["passed"] = True
    comparison_path.write_text(json.dumps(comparison, indent=2), encoding="utf-8")

    review = review_golden_path_workspace(
        Path.cwd(),
        proof_path=tmp_path / "golden-path" / "intake-proof" / "proof-summary.json",
        output_path=tmp_path / "golden-path" / "review-latest.json",
    )

    assert review.passed is False
    assert any(finding.code == "contract_sparse_evidence" for finding in review.findings)


def test_golden_path_review_passes_with_expanded_fixture_set(tmp_path: Path) -> None:
    generate_golden_path_proof(Path.cwd(), output_dir=tmp_path / "golden-path")

    review = review_golden_path_workspace(
        Path.cwd(),
        proof_path=tmp_path / "golden-path" / "intake-proof" / "proof-summary.json",
        output_path=tmp_path / "golden-path" / "review-latest.json",
    )

    assert review.passed is True
    assert review.summary["fixture_design"].errors == 0
    assert review.summary["contract_extraction"].errors == 0
    assert set(review.reviewed_fixture_ids) == {
        "val_golden_path_bad_input_scanned_v1",
        "val_golden_path_novice_concept_v1",
        "val_golden_path_novice_segmentation_warning_v1",
        "val_golden_path_professional_dry_run_v1",
        "val_golden_path_professional_manual_intake_v1",
    }


def test_golden_path_review_requires_fixture_level_report_proofs(tmp_path: Path) -> None:
    generate_golden_path_proof(Path.cwd(), output_dir=tmp_path / "golden-path")
    proof_path = tmp_path / "golden-path" / "intake-proof" / "proof-summary.json"
    payload = json.loads(proof_path.read_text(encoding="utf-8"))
    payload["fixture_report_proofs"] = []
    proof_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    review = review_golden_path_workspace(
        Path.cwd(),
        proof_path=proof_path,
        output_path=tmp_path / "golden-path" / "review-latest.json",
    )

    assert review.passed is False
    assert any(finding.code == "missing_fixture_report_proof" for finding in review.findings)


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


def test_orchestrator_next_task_fails_when_all_specs_are_complete(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"
    state_path.write_text(
        json.dumps(
            {
                "completed_specs": list(REQUIRED_SPEC_IDS),
                "active_task_id": None,
                "rejected_attempts": [],
                "accepted_artifacts": [],
                "last_verification": None,
            }
        ),
        encoding="utf-8",
    )
    loop = OrchestratorLoop.for_workspace(Path.cwd(), state_path=state_path)

    with pytest.raises(ValueError, match="All specs are already complete"):
        loop.next_task()
