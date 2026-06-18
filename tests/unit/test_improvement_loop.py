from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from synthetix.reporting.improvement import (
    CandidateProposal,
    CandidateTestResult,
    ImprovementCandidate,
    ImprovementLoop,
    ImprovementLoopResult,
)
from synthetix.reporting.quality import (
    HardGateResult,
    ReportQualityScore,
)


class QueueEditor:
    def __init__(self, proposals: Sequence[CandidateProposal]) -> None:
        self._proposals = list(proposals)

    def propose(
        self,
        current_best: ImprovementCandidate,
        decision_log: Sequence[Any],
    ) -> CandidateProposal | None:
        del current_best, decision_log
        if not self._proposals:
            return None
        return self._proposals.pop(0)


class MappingEvaluator:
    def __init__(self, scores: dict[str, ReportQualityScore]) -> None:
        self._scores = scores

    def evaluate(self, candidate: ImprovementCandidate) -> ReportQualityScore:
        return self._scores[candidate.candidate_id]


class MappingTestRunner:
    def __init__(self, results: dict[str, CandidateTestResult]) -> None:
        self._results = results

    def run(self, candidate: ImprovementCandidate) -> CandidateTestResult:
        return self._results[candidate.candidate_id]


def make_score(
    total_score: float,
    *,
    hard_gate_failures: Sequence[str] = (),
) -> ReportQualityScore:
    gates = [
        HardGateResult(name=name, passed=False, detail=f"{name} failed")
        for name in hard_gate_failures
    ]
    return ReportQualityScore(
        total_score=total_score,
        threshold=85.0,
        passes_threshold=total_score >= 85.0,
        accepted=not hard_gate_failures and total_score >= 85.0,
        weighted_breakdown={"analytical_correctness": total_score},
        hard_gates=gates,
    )


def test_improvement_loop_accepts_only_strict_score_improvements() -> None:
    baseline = ImprovementCandidate(candidate_id="baseline", payload={"rev": 0})
    same_score = ImprovementCandidate(candidate_id="same-score", payload={"rev": 1})
    improved = ImprovementCandidate(candidate_id="improved", payload={"rev": 2})

    loop = ImprovementLoop(
        editor=QueueEditor(
            [
                CandidateProposal(candidate=same_score, touched_paths=[], cost_usd=1.0),
                CandidateProposal(candidate=improved, touched_paths=[], cost_usd=1.0),
            ]
        ),
        evaluator=MappingEvaluator(
            {
                "baseline": make_score(80.0),
                "same-score": make_score(80.0),
                "improved": make_score(82.0),
            }
        ),
        test_runner=MappingTestRunner(
            {
                "same-score": CandidateTestResult(passed=True, failed_tests=[]),
                "improved": CandidateTestResult(passed=True, failed_tests=[]),
            }
        ),
        max_iterations=3,
        max_total_cost_usd=5.0,
        forbidden_path_prefixes=["src/synthetix/cli"],
    )

    result = loop.run(baseline)

    assert isinstance(result, ImprovementLoopResult)
    assert result.best_candidate.candidate_id == "improved"
    assert result.best_score.total_score == 82.0
    assert [entry.decision for entry in result.decision_log] == [
        "rejected",
        "accepted",
    ]
    assert [entry.reason for entry in result.decision_log] == [
        "no_strict_improvement",
        "strict_score_improvement",
    ]


def test_improvement_loop_logs_baseline_score_before_first_acceptance() -> None:
    baseline = ImprovementCandidate(candidate_id="baseline", payload={"rev": 0})
    improved = ImprovementCandidate(candidate_id="improved", payload={"rev": 1})

    loop = ImprovementLoop(
        editor=QueueEditor(
            [CandidateProposal(candidate=improved, touched_paths=[], cost_usd=1.0)]
        ),
        evaluator=MappingEvaluator(
            {
                "baseline": make_score(81.0),
                "improved": make_score(86.0),
            }
        ),
        test_runner=MappingTestRunner(
            {"improved": CandidateTestResult(passed=True, failed_tests=[])}
        ),
        max_iterations=1,
        max_total_cost_usd=5.0,
        forbidden_path_prefixes=[],
    )

    result = loop.run(baseline)

    assert result.decision_log[0].decision == "accepted"
    assert result.decision_log[0].score_before == 81.0
    assert result.decision_log[0].score_after == 86.0


def test_improvement_loop_rejects_forbidden_changes_test_failures_and_hard_gate_failures() -> None:
    baseline = ImprovementCandidate(candidate_id="baseline", payload={"rev": 0})
    forbidden = ImprovementCandidate(candidate_id="forbidden", payload={"rev": 1})
    failing_tests = ImprovementCandidate(candidate_id="failing-tests", payload={"rev": 2})
    hard_gate = ImprovementCandidate(candidate_id="hard-gate", payload={"rev": 3})

    loop = ImprovementLoop(
        editor=QueueEditor(
            [
                CandidateProposal(
                    candidate=forbidden,
                    touched_paths=["src/synthetix/cli/app.py"],
                    cost_usd=0.5,
                ),
                CandidateProposal(
                    candidate=failing_tests,
                    touched_paths=["src/synthetix/reporting/quality.py"],
                    cost_usd=0.5,
                ),
                CandidateProposal(
                    candidate=hard_gate,
                    touched_paths=["src/synthetix/reporting/improvement.py"],
                    cost_usd=0.5,
                ),
            ]
        ),
        evaluator=MappingEvaluator(
            {
                "baseline": make_score(84.0),
                "hard-gate": make_score(
                    95.0,
                    hard_gate_failures=["artifact_checksums_validate"],
                ),
            }
        ),
        test_runner=MappingTestRunner(
            {
                "failing-tests": CandidateTestResult(
                    passed=False,
                    failed_tests=["tests/unit/test_improvement_loop.py::test_example"],
                ),
                "hard-gate": CandidateTestResult(passed=True, failed_tests=[]),
            }
        ),
        max_iterations=4,
        max_total_cost_usd=5.0,
        forbidden_path_prefixes=["src/synthetix/cli"],
    )

    result = loop.run(baseline)

    assert result.best_candidate.candidate_id == "baseline"
    assert [entry.reason for entry in result.decision_log] == [
        "forbidden_change",
        "tests_failed",
        "hard_gate_failure",
    ]


def test_improvement_loop_stops_when_budget_would_be_exceeded() -> None:
    baseline = ImprovementCandidate(candidate_id="baseline", payload={"rev": 0})
    over_budget = ImprovementCandidate(candidate_id="over-budget", payload={"rev": 1})

    loop = ImprovementLoop(
        editor=QueueEditor(
            [
                CandidateProposal(
                    candidate=over_budget,
                    touched_paths=["src/synthetix/reporting/quality.py"],
                    cost_usd=2.5,
                )
            ]
        ),
        evaluator=MappingEvaluator({"baseline": make_score(84.0)}),
        test_runner=MappingTestRunner({}),
        max_iterations=2,
        max_total_cost_usd=2.0,
        forbidden_path_prefixes=[],
    )

    result = loop.run(baseline)

    assert result.best_candidate.candidate_id == "baseline"
    assert result.termination_reason == "budget_exhausted"
    assert result.decision_log[0].reason == "cost_budget_exceeded"
