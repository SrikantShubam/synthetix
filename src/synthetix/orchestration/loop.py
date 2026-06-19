from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field


class AgentModel(StrEnum):
    GPT_5_4 = "gpt-5.4"
    GPT_5_4_MINI = "gpt-5.4-mini"


class TaskStatus(StrEnum):
    PENDING = "pending"
    DISPATCHED = "dispatched"
    BLOCKED = "blocked"
    COMPLETED = "completed"


class OrchestratorTask(BaseModel):
    spec_id: str
    task_id: str
    title: str
    assigned_model: AgentModel
    allowed_paths: list[str]
    forbidden_paths: list[str]
    acceptance_checks: list[str]
    status: TaskStatus = TaskStatus.PENDING
    review_notes: list[str] = Field(default_factory=list)
    artifact_paths: list[str] = Field(default_factory=list)


class VerificationResult(BaseModel):
    passed: bool
    checks: dict[str, bool]
    review_notes: list[str] = Field(default_factory=list)
    artifact_paths: list[str] = Field(default_factory=list)


class RejectedAttempt(BaseModel):
    task_id: str
    review_notes: list[str]
    checks: dict[str, bool]


class OrchestratorState(BaseModel):
    completed_specs: list[str] = Field(default_factory=list)
    active_task_id: str | None = None
    rejected_attempts: list[RejectedAttempt] = Field(default_factory=list)
    accepted_artifacts: list[str] = Field(default_factory=list)
    last_verification: VerificationResult | None = None


class OrchestratorRunResult(BaseModel):
    completed_count: int
    blocked_task: OrchestratorTask | None
    blocked_reason: str
    state: OrchestratorState


class OrchestratorLoop:
    def __init__(
        self,
        *,
        workspace: Path,
        state_path: Path | None = None,
        progress_path: Path | None = None,
    ) -> None:
        self.workspace = workspace
        self.state_path = state_path
        self.progress_path = progress_path
        self.state = self._load_state()

    @classmethod
    def for_workspace(
        cls,
        workspace: Path,
        *,
        state_path: Path | None = None,
        progress_path: Path | None = None,
    ) -> "OrchestratorLoop":
        return cls(workspace=workspace, state_path=state_path, progress_path=progress_path)

    def next_task(self) -> OrchestratorTask:
        active_task_id = self.state.active_task_id
        if active_task_id is not None:
            return self._task_catalog()[active_task_id]

        if self._all_specs_complete():
            raise ValueError("All specs are already complete; no next task is available.")

        for task in self._task_catalog().values():
            if task.spec_id not in self.state.completed_specs:
                self.validate_task_policy(task)
                self.state.active_task_id = task.task_id
                self._save_state()
                return task
        raise ValueError("No incomplete orchestrator task is available.")

    def record_verification(
        self,
        task_id: str,
        verification: VerificationResult,
    ) -> OrchestratorState:
        task = self._task_catalog()[task_id]
        if self.state.active_task_id is None:
            self.state.active_task_id = task_id
        if self.state.active_task_id != task_id:
            raise ValueError(f"Expected active task '{self.state.active_task_id}', got '{task_id}'")

        self.validate_task_policy(task)
        self.state.last_verification = verification
        if not verification.passed:
            self.state.rejected_attempts.append(
                RejectedAttempt(
                    task_id=task_id,
                    review_notes=verification.review_notes,
                    checks=verification.checks,
                )
            )
            self._save_state()
            return self.state

        missing_checks = [
            check for check in task.acceptance_checks if verification.checks.get(check) is not True
        ]
        if missing_checks:
            raise ValueError(f"Missing passing checks for task '{task_id}': {missing_checks}")
        if task.spec_id not in self.state.completed_specs:
            self.state.completed_specs.append(task.spec_id)
        self.state.active_task_id = None
        for artifact_path in verification.artifact_paths:
            if artifact_path not in self.state.accepted_artifacts:
                self.state.accepted_artifacts.append(artifact_path)
        self._save_state()
        return self.state

    def run_until_blocked(self, *, max_steps: int = 20) -> OrchestratorRunResult:
        completed_count = 0
        blocked_task: OrchestratorTask | None = None
        blocked_reason = ""

        for _ in range(max_steps):
            if self._all_specs_complete():
                blocked_reason = "All specs complete"
                break
            task = self.next_task()
            packet = self.dispatch_packet(task)
            self._append_progress(
                f"## Dispatch: {task.task_id}\n\n"
                f"- model: `{task.assigned_model.value}`\n"
                f"- allowed paths: `{', '.join(task.allowed_paths)}`\n"
                f"- forbidden paths: `{', '.join(task.forbidden_paths)}`\n"
                f"- checks: `{', '.join(task.acceptance_checks)}`\n"
                f"- implementation prompt ready: `{bool(packet['implementation_prompt'])}`\n"
            )
            verification = self.evaluate_task(task)
            if not verification.passed:
                blocked_task = task.model_copy(
                    update={
                        "status": TaskStatus.BLOCKED,
                        "review_notes": verification.review_notes,
                    }
                )
                blocked_reason = "; ".join(verification.review_notes)
                self.record_verification(task.task_id, verification)
                self._append_progress(
                    f"\n### Blocked: {task.task_id}\n\n"
                    f"- reason: {blocked_reason}\n"
                    f"- checks: `{verification.checks}`\n"
                )
                break

            self.record_verification(task.task_id, verification)
            completed_count += 1
            self._append_progress(
                f"\n### Accepted: {task.task_id}\n\n"
                f"- artifacts: `{', '.join(verification.artifact_paths)}`\n"
                f"- checks: `{verification.checks}`\n"
            )
        else:
            blocked_reason = f"Reached max_steps={max_steps}"

        return OrchestratorRunResult(
            completed_count=completed_count,
            blocked_task=blocked_task,
            blocked_reason=blocked_reason,
            state=self.state,
        )

    def _all_specs_complete(self) -> bool:
        spec_ids = {task.spec_id for task in self._task_catalog().values()}
        return spec_ids.issubset(set(self.state.completed_specs))

    def dispatch_packet(self, task: OrchestratorTask) -> dict[str, object]:
        spec_path = self.workspace / "docs/specs" / f"{task.spec_id}.md"
        spec_text = spec_path.read_text(encoding="utf-8") if spec_path.exists() else ""
        goals_path = self.workspace / "goals.md"
        goals_text = goals_path.read_text(encoding="utf-8") if goals_path.exists() else ""
        return {
            "spec_id": task.spec_id,
            "task_id": task.task_id,
            "assigned_model": task.assigned_model.value,
            "allowed_paths": task.allowed_paths,
            "forbidden_paths": task.forbidden_paths,
            "acceptance_checks": task.acceptance_checks,
            "implementation_prompt": (
                "Implement this Synthetix spec using TDD. Stay within allowed paths, "
                "do not touch forbidden paths, and return artifact paths plus test evidence.\n\n"
                f"# Goals\n{goals_text}\n\n# Spec\n{spec_text}"
            ),
            "spec_review_prompt": (
                "Review the implementation strictly against the spec. Reject missing behavior, "
                "extra scope, holdout contamination, weak guardrails, or missing artifacts."
            ),
            "code_quality_prompt": (
                "Review code quality after spec compliance. Prioritize correctness, tests, "
                "maintainability, and architecture fit."
            ),
        }

    def evaluate_task(self, task: OrchestratorTask) -> VerificationResult:
        checks = {check: self._check_acceptance(task, check) for check in task.acceptance_checks}
        passed = all(checks.values())
        missing = [check for check, ok in checks.items() if not ok]
        review_notes = [] if passed else [f"Missing passing checks: {', '.join(missing)}"]
        artifact_paths = [
            path for path in task.allowed_paths if (self.workspace / path).exists()
        ]
        return VerificationResult(
            passed=passed,
            checks=checks,
            review_notes=review_notes,
            artifact_paths=artifact_paths,
        )

    @staticmethod
    def validate_task_policy(task: OrchestratorTask) -> None:
        high_judgment_specs = {
            "00-product-goals",
            "01-benchmark-thresholds",
            "03-professional-report-pdf",
            "05-validation-and-holdout-readiness",
            "06-agent-orchestrator-loop",
            "07-honest-predictor-improvement",
            "08-rich-reporting-upgrade",
            "09-research-design-study-plan",
        }
        if task.spec_id in high_judgment_specs and task.assigned_model != AgentModel.GPT_5_4:
            raise ValueError(f"Spec '{task.spec_id}' must be assigned to GPT-5.4")
        holdout_paths = [
            path
            for path in task.allowed_paths
            if "research/source_of_truth" in path or "holdout_papers" in path
        ]
        if holdout_paths and task.spec_id != "05-validation-and-holdout-readiness":
            raise ValueError(f"Task '{task.task_id}' is not allowed to target holdout paths")

    def _load_state(self) -> OrchestratorState:
        if self.state_path and self.state_path.exists():
            return OrchestratorState.model_validate_json(
                self.state_path.read_text(encoding="utf-8")
            )
        return OrchestratorState()

    def _save_state(self) -> None:
        if self.state_path is None:
            return
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(self.state.model_dump_json(indent=2), encoding="utf-8")

    def _append_progress(self, text: str) -> None:
        if self.progress_path is None:
            return
        self.progress_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.progress_path.exists():
            self.progress_path.write_text("# Orchestrator Progress\n\n", encoding="utf-8")
        with self.progress_path.open("a", encoding="utf-8") as progress_file:
            progress_file.write(text)
            progress_file.write("\n")

    def _check_acceptance(self, task: OrchestratorTask, check: str) -> bool:
        if check == "spec_presence":
            return all((self.workspace / path).exists() for path in task.allowed_paths)
        if check == "unit_tests":
            return (self.workspace / "tests/unit").exists()
        if check == "integration_tests":
            return (self.workspace / "tests/integration").exists()
        if check == "policy_gates":
            return (self.workspace / "tests").exists()
        if check == "holdout_contamination":
            return self._no_holdout_contamination(task)
        if check == "benchmark_classifier":
            return (self.workspace / "src/synthetix/benchmarking/classifier.py").exists()
        if check == "benchmark_comparison":
            return (self.workspace / "data/benchmark-results/development/summary.json").exists()
        if check == "report_quality":
            return (self.workspace / "src/synthetix/reporting/quality.py").exists()
        if check == "professional_report_quality":
            return (self.workspace / "src/synthetix/reporting/quality.py").exists()
        if check == "report_artifacts":
            required = ["report.json", "report.html", "report.pdf", "checksums.json"]
            return any(
                all((run_dir / filename).exists() for filename in required)
                for run_dir in (self.workspace / "data").glob("**")
                if run_dir.is_dir()
            )
        if check == "validation_evidence":
            return any((self.workspace / "research/benchmark_program/validation").glob("*.json"))
        if check == "research_design_schema":
            return (self.workspace / "tests/unit/test_research_design.py").exists()
        if check == "study_plan_validation":
            return (self.workspace / "tests/unit/test_research_design.py").exists()
        if check == "standards_alignment_checklist":
            return (
                self.workspace / "docs/protocols/research-design-standards-alignment.md"
            ).exists()
        if check == "prompt_contract_tests":
            return (self.workspace / "tests/unit/test_research_design.py").exists()
        if check == "report_objective_coverage":
            return (self.workspace / "tests/unit/test_research_design_reporting.py").exists()
        return False

    def _no_holdout_contamination(self, task: OrchestratorTask) -> bool:
        return not any(
            "research/source_of_truth" in path or "holdout_papers" in path
            for path in task.allowed_paths
            if task.spec_id != "05-validation-and-holdout-readiness"
        )

    @staticmethod
    def _task_catalog() -> dict[str, OrchestratorTask]:
        return {
            "00-product-goals": OrchestratorTask(
                spec_id="00-product-goals",
                task_id="00-product-goals",
                title="Product goals",
                assigned_model=AgentModel.GPT_5_4,
                allowed_paths=["goals.md", "docs/specs/00-product-goals.md"],
                forbidden_paths=["research/source_of_truth", "data/benchmark-results/holdout"],
                acceptance_checks=["spec_presence", "unit_tests"],
            ),
            "01-benchmark-thresholds": OrchestratorTask(
                spec_id="01-benchmark-thresholds",
                task_id="01-benchmark-thresholds",
                title="Benchmark thresholds",
                assigned_model=AgentModel.GPT_5_4,
                allowed_paths=["docs/specs/01-benchmark-thresholds.md", "src/synthetix"],
                forbidden_paths=["research/source_of_truth", "data/benchmark-results/holdout"],
                acceptance_checks=["unit_tests", "holdout_contamination", "benchmark_classifier"],
            ),
            "02-pipeline-predicted-metrics": OrchestratorTask(
                spec_id="02-pipeline-predicted-metrics",
                task_id="02-pipeline-predicted-metrics",
                title="Pipeline predicted metrics",
                assigned_model=AgentModel.GPT_5_4_MINI,
                allowed_paths=["src/synthetix", "tests", "data/benchmark-predictions"],
                forbidden_paths=["research/source_of_truth", "data/benchmark-results/holdout"],
                acceptance_checks=["unit_tests", "integration_tests", "benchmark_comparison"],
            ),
            "03-professional-report-pdf": OrchestratorTask(
                spec_id="03-professional-report-pdf",
                task_id="03-professional-report-pdf",
                title="Professional report PDF",
                assigned_model=AgentModel.GPT_5_4,
                allowed_paths=["src/synthetix/reporting", "src/synthetix/analysis", "tests"],
                forbidden_paths=["research/source_of_truth", "data/benchmark-results/holdout"],
                acceptance_checks=["unit_tests", "report_quality", "report_artifacts"],
            ),
            "04-transparent-simulation-dashboard": OrchestratorTask(
                spec_id="04-transparent-simulation-dashboard",
                task_id="04-transparent-simulation-dashboard",
                title="Transparent simulation dashboard",
                assigned_model=AgentModel.GPT_5_4_MINI,
                allowed_paths=["src/synthetix/web", "tests"],
                forbidden_paths=["research/source_of_truth", "data/benchmark-results/holdout"],
                acceptance_checks=["unit_tests", "integration_tests"],
            ),
            "05-validation-and-holdout-readiness": OrchestratorTask(
                spec_id="05-validation-and-holdout-readiness",
                task_id="05-validation-and-holdout-readiness",
                title="Validation and holdout readiness",
                assigned_model=AgentModel.GPT_5_4,
                allowed_paths=[
                    "research/benchmark_program/validation",
                    "docs/specs/05-validation-and-holdout-readiness.md",
                ],
                forbidden_paths=["research/source_of_truth/holdout_papers"],
                acceptance_checks=["validation_evidence", "holdout_contamination"],
            ),
            "06-agent-orchestrator-loop": OrchestratorTask(
                spec_id="06-agent-orchestrator-loop",
                task_id="06-agent-orchestrator-loop",
                title="Agent orchestrator loop",
                assigned_model=AgentModel.GPT_5_4,
                allowed_paths=["src/synthetix/orchestration", "tests", "docs/specs"],
                forbidden_paths=["research/source_of_truth", "data/benchmark-results/holdout"],
                acceptance_checks=["unit_tests", "integration_tests", "policy_gates"],
            ),
            "07-honest-predictor-improvement": OrchestratorTask(
                spec_id="07-honest-predictor-improvement",
                task_id="07-honest-predictor-improvement",
                title="Honest predictor improvement",
                assigned_model=AgentModel.GPT_5_4,
                allowed_paths=["src/synthetix", "tests", "docs/specs", "data/benchmark-predictions"],
                forbidden_paths=["research/source_of_truth", "data/benchmark-results/holdout"],
                acceptance_checks=["unit_tests", "integration_tests", "benchmark_comparison", "policy_gates"],
            ),
            "08-rich-reporting-upgrade": OrchestratorTask(
                spec_id="08-rich-reporting-upgrade",
                task_id="08-rich-reporting-upgrade",
                title="Rich reporting upgrade",
                assigned_model=AgentModel.GPT_5_4,
                allowed_paths=["src/synthetix/reporting", "src/synthetix/analysis", "src/synthetix/web", "tests", "docs/specs"],
                forbidden_paths=["research/source_of_truth", "data/benchmark-results/holdout"],
                acceptance_checks=["unit_tests", "integration_tests", "report_quality", "report_artifacts", "policy_gates"],
            ),
            "09-research-design-study-plan": OrchestratorTask(
                spec_id="09-research-design-study-plan",
                task_id="09-research-design-study-plan",
                title="Research design study plan",
                assigned_model=AgentModel.GPT_5_4,
                allowed_paths=[
                    "src/synthetix/blueprints",
                    "src/synthetix/execution",
                    "src/synthetix/analysis",
                    "src/synthetix/reporting",
                    "src/synthetix/orchestration",
                    "tests",
                    "docs/specs/09-research-design-study-plan.md",
                    "docs/protocols/research-design-standards-alignment.md",
                ],
                forbidden_paths=["research/source_of_truth", "data/benchmark-results/holdout"],
                acceptance_checks=[
                    "research_design_schema",
                    "study_plan_validation",
                    "standards_alignment_checklist",
                    "prompt_contract_tests",
                    "report_objective_coverage",
                    "professional_report_quality",
                    "unit_tests",
                    "integration_tests",
                    "policy_gates",
                ],
            ),
        }
