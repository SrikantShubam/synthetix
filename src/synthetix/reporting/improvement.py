from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Protocol

from pydantic import BaseModel, Field

from synthetix.reporting.quality import ReportQualityScore


class ImprovementCandidate(BaseModel):
    candidate_id: str
    payload: Any


class CandidateProposal(BaseModel):
    candidate: ImprovementCandidate
    touched_paths: list[str] = Field(default_factory=list)
    cost_usd: float = Field(default=0.0, ge=0)


class CandidateTestResult(BaseModel):
    passed: bool
    failed_tests: list[str] = Field(default_factory=list)


class ImprovementDecisionLogEntry(BaseModel):
    iteration: int
    candidate_id: str
    decision: str
    reason: str
    cost_usd: float
    touched_paths: list[str] = Field(default_factory=list)
    score_before: float
    score_after: float | None = None
    failed_tests: list[str] = Field(default_factory=list)
    failed_hard_gates: list[str] = Field(default_factory=list)


class ImprovementLoopResult(BaseModel):
    best_candidate: ImprovementCandidate
    best_score: ReportQualityScore
    decision_log: list[ImprovementDecisionLogEntry] = Field(default_factory=list)
    spent_cost_usd: float = 0.0
    termination_reason: str


class CandidateEditor(Protocol):
    def propose(
        self,
        current_best: ImprovementCandidate,
        decision_log: Sequence[ImprovementDecisionLogEntry],
    ) -> CandidateProposal | None: ...


class CandidateEvaluator(Protocol):
    def evaluate(self, candidate: ImprovementCandidate) -> ReportQualityScore: ...


class CandidateTestRunner(Protocol):
    def run(self, candidate: ImprovementCandidate) -> CandidateTestResult: ...


class ImprovementLoop:
    def __init__(
        self,
        *,
        editor: CandidateEditor,
        evaluator: CandidateEvaluator,
        test_runner: CandidateTestRunner,
        max_iterations: int,
        max_total_cost_usd: float,
        forbidden_path_prefixes: Sequence[str],
    ) -> None:
        self.editor = editor
        self.evaluator = evaluator
        self.test_runner = test_runner
        self.max_iterations = max_iterations
        self.max_total_cost_usd = max_total_cost_usd
        self.forbidden_path_prefixes = tuple(
            _normalize_path(prefix) for prefix in forbidden_path_prefixes
        )

    def run(self, baseline: ImprovementCandidate) -> ImprovementLoopResult:
        best_candidate = baseline
        best_score = self.evaluator.evaluate(baseline)
        decision_log: list[ImprovementDecisionLogEntry] = []
        spent_cost_usd = 0.0
        termination_reason = "max_iterations_reached"

        for iteration in range(1, self.max_iterations + 1):
            proposal = self.editor.propose(best_candidate, tuple(decision_log))
            if proposal is None:
                termination_reason = "editor_exhausted"
                break
            if spent_cost_usd + proposal.cost_usd > self.max_total_cost_usd:
                decision_log.append(
                    ImprovementDecisionLogEntry(
                        iteration=iteration,
                        candidate_id=proposal.candidate.candidate_id,
                        decision="rejected",
                        reason="cost_budget_exceeded",
                        cost_usd=proposal.cost_usd,
                        touched_paths=proposal.touched_paths,
                        score_before=best_score.total_score,
                    )
                )
                termination_reason = "budget_exhausted"
                break

            spent_cost_usd = round(spent_cost_usd + proposal.cost_usd, 6)
            if self._touches_forbidden_path(proposal.touched_paths):
                decision_log.append(
                    ImprovementDecisionLogEntry(
                        iteration=iteration,
                        candidate_id=proposal.candidate.candidate_id,
                        decision="rejected",
                        reason="forbidden_change",
                        cost_usd=proposal.cost_usd,
                        touched_paths=proposal.touched_paths,
                        score_before=best_score.total_score,
                    )
                )
                continue

            test_result = self.test_runner.run(proposal.candidate)
            if not test_result.passed:
                decision_log.append(
                    ImprovementDecisionLogEntry(
                        iteration=iteration,
                        candidate_id=proposal.candidate.candidate_id,
                        decision="rejected",
                        reason="tests_failed",
                        cost_usd=proposal.cost_usd,
                        touched_paths=proposal.touched_paths,
                        score_before=best_score.total_score,
                        failed_tests=test_result.failed_tests,
                    )
                )
                continue

            candidate_score = self.evaluator.evaluate(proposal.candidate)
            if candidate_score.failed_hard_gates:
                decision_log.append(
                    ImprovementDecisionLogEntry(
                        iteration=iteration,
                        candidate_id=proposal.candidate.candidate_id,
                        decision="rejected",
                        reason="hard_gate_failure",
                        cost_usd=proposal.cost_usd,
                        touched_paths=proposal.touched_paths,
                        score_before=best_score.total_score,
                        score_after=candidate_score.total_score,
                        failed_hard_gates=candidate_score.failed_hard_gates,
                    )
                )
                continue
            if candidate_score.total_score <= best_score.total_score:
                decision_log.append(
                    ImprovementDecisionLogEntry(
                        iteration=iteration,
                        candidate_id=proposal.candidate.candidate_id,
                        decision="rejected",
                        reason="no_strict_improvement",
                        cost_usd=proposal.cost_usd,
                        touched_paths=proposal.touched_paths,
                        score_before=best_score.total_score,
                        score_after=candidate_score.total_score,
                    )
                )
                continue

            prior_score = best_score.total_score
            best_candidate = proposal.candidate
            best_score = candidate_score
            decision_log.append(
                ImprovementDecisionLogEntry(
                    iteration=iteration,
                    candidate_id=proposal.candidate.candidate_id,
                    decision="accepted",
                    reason="strict_score_improvement",
                    cost_usd=proposal.cost_usd,
                    touched_paths=proposal.touched_paths,
                    score_before=prior_score,
                    score_after=candidate_score.total_score,
                )
            )

        return ImprovementLoopResult(
            best_candidate=best_candidate,
            best_score=best_score,
            decision_log=decision_log,
            spent_cost_usd=spent_cost_usd,
            termination_reason=termination_reason,
        )

    def _touches_forbidden_path(self, touched_paths: Sequence[str]) -> bool:
        normalized_paths = [_normalize_path(path) for path in touched_paths]
        return any(
            any(path.startswith(prefix) for prefix in self.forbidden_path_prefixes)
            for path in normalized_paths
        )


def _normalize_path(path: str) -> str:
    return path.replace("\\", "/").strip().lower().strip("/")
