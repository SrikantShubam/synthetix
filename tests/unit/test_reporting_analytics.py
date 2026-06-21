from __future__ import annotations

from datetime import datetime, timezone

from synthetix.analysis.reporting import build_report
from synthetix.blueprints.models import (
    ChoiceQuestion,
    LikertQuestion,
    OpenTextQuestion,
    PopulationSpec,
    SimulationBlueprint,
)
from synthetix.execution.manifest import RunManifest
from synthetix.execution.models import (
    AttemptRecord,
    AttemptStatus,
    RespondentResult,
    RunResult,
    RunStatus,
)


def _blueprint(*questions: object, attributes: dict[str, list[str]] | None = None) -> SimulationBlueprint:
    return SimulationBlueprint(
        title="Analytics contract",
        purpose="Exercise the reporting contract.",
        population=PopulationSpec(
            size=4,
            seed=7,
            attributes=attributes or {"region": ["urban", "rural"]},
        ),
        questions=list(questions),
    )


def _manifest(blueprint: SimulationBlueprint) -> RunManifest:
    return RunManifest.create(
        run_id="run-analytics",
        blueprint=blueprint,
        source_hashes={"survey.yaml": "abc123"},
        model_id="openai/gpt-4.1-mini",
        provider="openai",
        parameters={"temperature": 0.2},
    )


def _respondent(
    persona_id: str,
    *,
    status: AttemptStatus = AttemptStatus.SUCCEEDED,
    answers: dict[str, object] | None = None,
    attributes: dict[str, str] | None = None,
    attempts: int = 1,
) -> RespondentResult:
    return RespondentResult(
        persona_id=persona_id,
        attributes=attributes or {"region": "urban"},
        status=status,
        answers=answers or {},
        attempts=[
            AttemptRecord(
                number=index + 1,
                status=status if index == attempts - 1 else AttemptStatus.FAILED,
                input_tokens=10,
                output_tokens=5,
                cost_usd=0.01,
            )
            for index in range(attempts)
        ],
    )


def _result(*respondents: RespondentResult) -> RunResult:
    return RunResult(
        run_id="run-analytics",
        status=RunStatus.COMPLETED,
        respondents=list(respondents),
        started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        completed_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


def test_build_report_canonicalizes_choice_and_likert_answers() -> None:
    blueprint = _blueprint(
        ChoiceQuestion(id="q_choice", prompt="Would you buy it?", options=["Yes", "No"]),
        LikertQuestion(id="q_likert", prompt="Rate fit", minimum=1, maximum=5),
    )
    result = _result(
        _respondent("p1", answers={"q_choice": " yes ", "q_likert": 5}),
        _respondent("p2", answers={"q_choice": "YES", "q_likert": "5"}),
        _respondent("p3", answers={"q_choice": "No", "q_likert": 2.0}),
        _respondent("p4", answers={"q_choice": "maybe", "q_likert": " 1 "}),
        _respondent("p5", answers={"q_likert": 7}),
    )

    report = build_report(blueprint, result, _manifest(blueprint))

    choice = report.questions[0]
    assert choice.question_type == "choice"
    assert choice.distribution.labels == ["Yes", "No"]
    assert choice.distribution.values == [2, 1]
    assert choice.response_count == 3
    assert choice.denominators.answered_responses == 4
    assert choice.denominators.valid_responses == 3
    assert choice.denominators.invalid_responses == 1
    assert choice.denominators.missing_responses == 1
    assert [quote.quote_id for quote in choice.quote_evidence] == ["q_choice:p1", "q_choice:p2", "q_choice:p3"]
    assert choice.chart is not None
    assert choice.chart.chart_family == "question_distribution"
    assert choice.chart.values == [2, 1]
    assert choice.chart.option["series"][0]["data"] == [2, 1]

    likert = report.questions[1]
    assert likert.question_type == "likert"
    assert likert.distribution.labels == ["1", "2", "3", "4", "5"]
    assert likert.distribution.values == [1, 1, 0, 0, 2]
    assert likert.response_count == 4
    assert likert.denominators.answered_responses == 5
    assert likert.denominators.valid_responses == 4
    assert likert.denominators.invalid_responses == 1
    assert likert.chart is not None
    assert likert.chart.chart_family == "question_distribution"


def test_build_report_uses_open_text_as_traceable_evidence() -> None:
    blueprint = _blueprint(
        OpenTextQuestion(id="q_open", prompt="What stood out?"),
    )
    result = _result(
        _respondent("p1", answers={"q_open": "Need lower price"}),
        _respondent("p2", answers={"q_open": " need lower price "}),
        _respondent("p3", answers={"q_open": "I like the convenience"}),
    )

    report = build_report(blueprint, result, _manifest(blueprint))

    question = report.questions[0]
    assert question.question_type == "open_text"
    assert question.distribution.labels == []
    assert question.distribution.values == []
    assert question.quotes == [
        "Need lower price",
        "need lower price",
        "I like the convenience",
    ]
    assert [quote.quote_id for quote in question.quote_evidence] == [
        "q_open:p1",
        "q_open:p2",
        "q_open:p3",
    ]
    assert question.quote_evidence[0].persona_id == "p1"
    assert question.quote_evidence[1].text == "need lower price"
    assert question.themes[0].label == "Price sensitivity and value concern"
    assert question.themes[0].count == 2
    assert question.themes[0].supporting_quote_ids == ["q_open:p1", "q_open:p2"]
    assert question.chart is None
    assert question.chart_decision is not None
    assert question.chart_decision.status == "replaced_with_evidence_panel"
    assert "coded themes and quotes" in question.chart_decision.reason


def test_build_report_links_executive_findings_to_response_evidence() -> None:
    blueprint = _blueprint(
        ChoiceQuestion(id="q_choice", prompt="Would you buy it?", options=["Yes", "No"]),
        OpenTextQuestion(id="q_open", prompt="What stood out?"),
    )
    result = _result(
        _respondent("p1", answers={"q_choice": "Yes", "q_open": "Need lower price"}),
        _respondent("p2", answers={"q_choice": "Yes", "q_open": "The price feels expensive"}),
        _respondent("p3", answers={"q_choice": "No", "q_open": "I like the convenience"}),
    )

    report = build_report(blueprint, result, _manifest(blueprint))

    top_response = next(finding for finding in report.executive_findings if finding.finding_id == "q_choice-top-response")
    top_theme = next(finding for finding in report.executive_findings if finding.finding_id == "q_open-theme-1")

    assert top_response.evidence_quote_ids == ["q_choice:p1", "q_choice:p2"]
    assert top_theme.evidence_quote_ids == ["q_open:p1", "q_open:p2"]


def test_build_report_includes_segment_composition_and_suppressed_cuts() -> None:
    blueprint = _blueprint(
        ChoiceQuestion(id="q_choice", prompt="Would you buy it?", options=["Yes", "No"]),
        attributes={"region": ["urban", "rural"]},
    )
    result = _result(
        _respondent("p1", answers={"q_choice": "Yes"}, attributes={"region": "urban"}),
        _respondent("p2", answers={"q_choice": "No"}, attributes={"region": "urban"}),
        _respondent("p3", answers={"q_choice": "Yes"}, attributes={"region": "rural"}),
    )

    report = build_report(blueprint, result, _manifest(blueprint))

    composition = report.segment_composition[0]
    assert composition.attribute == "region"
    assert {segment.value: segment.count for segment in composition.segments} == {
        "urban": 2,
        "rural": 1,
    }
    assert {segment.value: segment.suppressed for segment in composition.segments} == {
        "urban": False,
        "rural": True,
    }

    question = report.questions[0]
    cuts = {(cut.attribute, cut.value): cut for cut in question.segment_cuts}
    assert cuts[("region", "urban")].suppressed is False
    assert cuts[("region", "urban")].distribution.values == [1, 1]
    assert cuts[("region", "rural")].suppressed is True
    assert cuts[("region", "rural")].distribution.labels == []
    assert cuts[("region", "rural")].base_count == 1
    assert report.analytics.population_charts[0].chart_family == "population_segment"
    assert report.analytics.population_charts[0].values == [2, 1]


def test_build_report_tracks_question_denominators_and_failures() -> None:
    blueprint = _blueprint(
        ChoiceQuestion(id="q_choice", prompt="Would you buy it?", options=["Yes", "No"]),
    )
    result = _result(
        _respondent("p1", answers={"q_choice": "Yes"}, attempts=2),
        _respondent("p2", answers={}, attempts=1),
        _respondent("p3", answers={"q_choice": "maybe"}, attempts=1),
        _respondent("p4", status=AttemptStatus.TIMEOUT, attempts=2),
    )

    report = build_report(blueprint, result, _manifest(blueprint))

    question = report.questions[0]
    assert question.denominators.total_personas == 4
    assert question.denominators.succeeded_personas == 3
    assert question.denominators.answered_responses == 2
    assert question.denominators.valid_responses == 1
    assert question.denominators.invalid_responses == 1
    assert question.denominators.missing_responses == 1

    assert report.failures.total_personas == 4
    assert report.failures.succeeded == 3
    assert report.failures.failed == 1
    assert report.failures.retries == 2
    assert report.failures.classifications == {"timeout": 1}
