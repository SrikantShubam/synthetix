from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from synthetix.blueprints.models import ChoiceQuestion, LikertQuestion, OpenTextQuestion, Question, SimulationBlueprint
from synthetix.execution.manifest import RunManifest
from synthetix.execution.models import AttemptStatus, RunResult
from synthetix.reporting.models import (
    DenominatorSummary,
    Distribution,
    ExecutiveFinding,
    FailureSummary,
    MethodologySummary,
    ProvenanceSummary,
    QuestionReport,
    QuoteEvidence,
    ReportModel,
    SegmentComposition,
    SegmentCompositionEntry,
    SegmentCut,
    ThemeEvidence,
)

MAX_QUOTES = 5
MIN_SEGMENT_BASE = 2


def _collapse_whitespace(value: str) -> str:
    return " ".join(value.split())


def _normalized_text(value: str) -> str:
    return _collapse_whitespace(value).casefold()


def _clean_open_text(value: Any) -> str | None:
    if value is None:
        return None
    cleaned = _collapse_whitespace(str(value))
    return cleaned or None


def _canonicalize_choice(question: ChoiceQuestion, value: Any) -> str | None:
    canonical = {
        _normalized_text(option): option
        for option in question.options
    }
    cleaned = _clean_open_text(value)
    if cleaned is None:
        return None
    return canonical.get(cleaned.casefold())


def _canonicalize_likert(question: LikertQuestion, value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    score: int | None = None
    if isinstance(value, int):
        score = value
    elif isinstance(value, float) and value.is_integer():
        score = int(value)
    elif isinstance(value, str):
        cleaned = _collapse_whitespace(value)
        if not cleaned:
            return None
        try:
            numeric = float(cleaned)
        except ValueError:
            return None
        if numeric.is_integer():
            score = int(numeric)
    if score is None or not question.minimum <= score <= question.maximum:
        return None
    return score


def _build_denominators(
    *,
    total_personas: int,
    succeeded_personas: int,
    answered_responses: int,
    valid_responses: int,
) -> DenominatorSummary:
    return DenominatorSummary(
        total_personas=total_personas,
        succeeded_personas=succeeded_personas,
        answered_responses=answered_responses,
        valid_responses=valid_responses,
        missing_responses=max(0, succeeded_personas - answered_responses),
        invalid_responses=max(0, answered_responses - valid_responses),
    )


def _build_open_text_evidence(
    question: OpenTextQuestion,
    respondents: list[Any],
) -> tuple[list[QuoteEvidence], list[ThemeEvidence]]:
    quote_evidence: list[QuoteEvidence] = []
    theme_groups: dict[str, dict[str, Any]] = {}
    for respondent in respondents:
        cleaned = _clean_open_text(respondent.answers.get(question.id))
        if cleaned is None:
            continue
        quote_id = f"{question.id}:{respondent.persona_id}"
        quote_evidence.append(
            QuoteEvidence(
                quote_id=quote_id,
                persona_id=respondent.persona_id,
                text=cleaned,
                attributes=respondent.attributes,
            )
        )
        key = cleaned.casefold()
        group = theme_groups.setdefault(
            key,
            {"label": cleaned, "supporting_quote_ids": []},
        )
        group["supporting_quote_ids"].append(quote_id)

    ordered_groups = sorted(
        theme_groups.values(),
        key=lambda group: (-len(group["supporting_quote_ids"]), group["label"].casefold()),
    )
    themes = [
        ThemeEvidence(
            theme_id=f"{question.id}:theme:{index}",
            label=group["label"],
            count=len(group["supporting_quote_ids"]),
            supporting_quote_ids=list(group["supporting_quote_ids"]),
        )
        for index, group in enumerate(ordered_groups, start=1)
    ]
    return quote_evidence, themes


def _build_choice_distribution(
    question: ChoiceQuestion,
    respondents: list[Any],
) -> tuple[Distribution, list[str], int]:
    counts: Counter[str] = Counter()
    valid_values: list[str] = []
    for respondent in respondents:
        canonical = _canonicalize_choice(question, respondent.answers.get(question.id))
        if canonical is None:
            continue
        counts[canonical] += 1
        valid_values.append(canonical)
    return (
        Distribution(
            labels=list(question.options),
            values=[counts.get(option, 0) for option in question.options],
        ),
        valid_values[:MAX_QUOTES],
        len(valid_values),
    )


def _build_likert_distribution(
    question: LikertQuestion,
    respondents: list[Any],
) -> tuple[Distribution, list[str], int]:
    counts: Counter[int] = Counter()
    valid_values: list[str] = []
    for respondent in respondents:
        canonical = _canonicalize_likert(question, respondent.answers.get(question.id))
        if canonical is None:
            continue
        counts[canonical] += 1
        valid_values.append(str(canonical))
    scale = list(range(question.minimum, question.maximum + 1))
    return (
        Distribution(
            labels=[str(value) for value in scale],
            values=[counts.get(value, 0) for value in scale],
        ),
        valid_values[:MAX_QUOTES],
        len(valid_values),
    )


def _answered_respondents(question_id: str, respondents: list[Any]) -> list[Any]:
    return [respondent for respondent in respondents if question_id in respondent.answers]


def _build_segment_cuts(
    question: Question,
    succeeded_respondents: list[Any],
    population_attributes: dict[str, list[str]],
) -> list[SegmentCut]:
    observed_values_by_attribute: dict[str, list[str]] = {}
    for attribute, declared_values in population_attributes.items():
        extras = sorted(
            {
                respondent.attributes.get(attribute)
                for respondent in succeeded_respondents
                if respondent.attributes.get(attribute) not in set(declared_values)
                and respondent.attributes.get(attribute)
            }
        )
        observed_values_by_attribute[attribute] = [*declared_values, *extras]

    segment_cuts: list[SegmentCut] = []
    for attribute, values in observed_values_by_attribute.items():
        for value in values:
            segment_respondents = [
                respondent
                for respondent in succeeded_respondents
                if respondent.attributes.get(attribute) == value
            ]
            base_count = len(segment_respondents)
            if base_count < MIN_SEGMENT_BASE:
                segment_cuts.append(
                    SegmentCut(
                        attribute=attribute,
                        value=value,
                        base_count=base_count,
                        suppressed=True,
                    )
                )
                continue

            if question.type == "choice":
                distribution, _, _ = _build_choice_distribution(question, segment_respondents)
                segment_cuts.append(
                    SegmentCut(
                        attribute=attribute,
                        value=value,
                        base_count=base_count,
                        distribution=distribution,
                    )
                )
            elif question.type == "likert":
                distribution, _, _ = _build_likert_distribution(question, segment_respondents)
                segment_cuts.append(
                    SegmentCut(
                        attribute=attribute,
                        value=value,
                        base_count=base_count,
                        distribution=distribution,
                    )
                )
            else:
                _, themes = _build_open_text_evidence(question, segment_respondents)
                segment_cuts.append(
                    SegmentCut(
                        attribute=attribute,
                        value=value,
                        base_count=base_count,
                        themes=themes,
                    )
                )
    return segment_cuts


def _build_segment_composition(
    succeeded_respondents: list[Any],
    population_attributes: dict[str, list[str]],
) -> list[SegmentComposition]:
    compositions: list[SegmentComposition] = []
    succeeded_total = len(succeeded_respondents)
    for attribute, declared_values in population_attributes.items():
        counts = Counter(
            respondent.attributes.get(attribute)
            for respondent in succeeded_respondents
            if respondent.attributes.get(attribute)
        )
        extras = sorted(value for value in counts if value not in set(declared_values))
        values = [*declared_values, *extras]
        compositions.append(
            SegmentComposition(
                attribute=attribute,
                segments=[
                    SegmentCompositionEntry(
                        value=value,
                        count=counts.get(value, 0),
                        share=(
                            counts.get(value, 0) / succeeded_total
                            if succeeded_total
                            else 0.0
                        ),
                        suppressed=counts.get(value, 0) < MIN_SEGMENT_BASE,
                    )
                    for value in values
                ],
            )
        )
    return compositions


def _build_question_report(
    question: Question,
    *,
    total_personas: int,
    succeeded_respondents: list[Any],
    population_attributes: dict[str, list[str]],
) -> QuestionReport:
    answered_respondents = _answered_respondents(question.id, succeeded_respondents)
    if question.type == "choice":
        distribution, quotes, valid_count = _build_choice_distribution(question, answered_respondents)
        return QuestionReport(
            question_id=question.id,
            prompt=question.prompt,
            question_type=question.type,
            response_count=valid_count,
            distribution=distribution,
            quotes=quotes,
            denominators=_build_denominators(
                total_personas=total_personas,
                succeeded_personas=len(succeeded_respondents),
                answered_responses=len(answered_respondents),
                valid_responses=valid_count,
            ),
            segment_cuts=_build_segment_cuts(question, succeeded_respondents, population_attributes),
        )

    if question.type == "likert":
        distribution, quotes, valid_count = _build_likert_distribution(question, answered_respondents)
        return QuestionReport(
            question_id=question.id,
            prompt=question.prompt,
            question_type=question.type,
            response_count=valid_count,
            distribution=distribution,
            quotes=quotes,
            denominators=_build_denominators(
                total_personas=total_personas,
                succeeded_personas=len(succeeded_respondents),
                answered_responses=len(answered_respondents),
                valid_responses=valid_count,
            ),
            segment_cuts=_build_segment_cuts(question, succeeded_respondents, population_attributes),
        )

    quote_evidence, themes = _build_open_text_evidence(question, answered_respondents)
    return QuestionReport(
        question_id=question.id,
        prompt=question.prompt,
        question_type=question.type,
        response_count=len(quote_evidence),
        distribution=Distribution(),
        quotes=[quote.text for quote in quote_evidence[:MAX_QUOTES]],
        denominators=_build_denominators(
            total_personas=total_personas,
            succeeded_personas=len(succeeded_respondents),
            answered_responses=len(answered_respondents),
            valid_responses=len(quote_evidence),
        ),
        quote_evidence=quote_evidence,
        themes=themes,
        segment_cuts=_build_segment_cuts(question, succeeded_respondents, population_attributes),
    )


def _build_executive_findings(question_reports: list[QuestionReport]) -> list[ExecutiveFinding]:
    findings: list[ExecutiveFinding] = []
    for question in question_reports:
        if question.question_type in {"choice", "likert"} and question.distribution.labels:
            pairs = list(zip(question.distribution.labels, question.distribution.values))
            top_label, top_count = max(pairs, key=lambda pair: (pair[1], pair[0]))
            if top_count <= 0 or question.denominators.valid_responses <= 0:
                continue
            findings.append(
                ExecutiveFinding(
                    finding_id=f"{question.question_id}-top-response",
                    title=f"Top response for {question.question_id}",
                    summary=(
                        f"'{top_label}' was the most common synthetic response "
                        f"({top_count}/{question.denominators.valid_responses})."
                    ),
                    question_id=question.question_id,
                )
            )
        elif question.question_type == "open_text" and question.themes:
            theme = question.themes[0]
            findings.append(
                ExecutiveFinding(
                    finding_id=f"{question.question_id}-theme-1",
                    title=f"Most repeated wording for {question.question_id}",
                    summary=(
                        f"The most repeated exact-response wording was '{theme.label}' "
                        f"({theme.count} mentions)."
                    ),
                    question_id=question.question_id,
                    evidence_quote_ids=list(theme.supporting_quote_ids),
                )
            )
    return findings[:5]


def build_report(
    blueprint: SimulationBlueprint,
    result: RunResult,
    manifest: RunManifest,
) -> ReportModel:
    succeeded_respondents = [
        respondent
        for respondent in result.respondents
        if respondent.status == AttemptStatus.SUCCEEDED
    ]
    question_reports = [
        _build_question_report(
            question,
            total_personas=len(result.respondents),
            succeeded_respondents=succeeded_respondents,
            population_attributes=blueprint.population.attributes,
        )
        for question in blueprint.questions
    ]
    failures: defaultdict[str, int] = defaultdict(int)
    retries = 0
    for respondent in result.respondents:
        retries += max(0, len(respondent.attempts) - 1)
        if respondent.status != AttemptStatus.SUCCEEDED:
            failures[respondent.status.value] += 1
    succeeded = len(succeeded_respondents)
    question_findings = _build_executive_findings(question_reports)
    return ReportModel(
        run_id=result.run_id,
        title=blueprint.title,
        purpose=blueprint.purpose,
        executive_summary=(
            f"{succeeded} of {len(result.respondents)} synthetic personas produced valid responses. "
            "These outputs support scenario exploration only."
        ),
        population=blueprint.population.model_dump(mode="json"),
        questions=question_reports,
        executive_findings=question_findings,
        segment_composition=_build_segment_composition(
            succeeded_respondents,
            blueprint.population.attributes,
        ),
        sensitivity_notes=[
            "Small synthetic populations can overstate apparent consensus.",
            "Changing the model, provider, or seed can materially alter outputs.",
        ],
        methodology=MethodologySummary(
            approach="Synthetic persona scenario exploration with deterministic aggregation.",
            response_generation=(
                "Each synthetic persona returns one validated answer set; retries and invalid attempts "
                "remain retained for audit and attrition accounting."
            ),
            quality_controls=[
                "Invalid, duplicate, unknown, and missing required answers cannot become succeeded respondents.",
                "Question distributions are normalized by question type and shown with explicit denominators.",
                "Open-text responses are kept as traceable evidence rather than charted as categorical distributions.",
            ],
        ),
        failures=FailureSummary(
            total_personas=len(result.respondents),
            succeeded=succeeded,
            failed=len(result.respondents) - succeeded,
            retries=retries,
            classifications=dict(failures),
        ),
        provenance=ProvenanceSummary(
            model_id=manifest.model_id,
            provider=manifest.provider,
            blueprint_hash=manifest.blueprint_hash,
            manifest_hash=manifest.manifest_hash(),
            protocol_version=manifest.protocol_version,
        ),
        token_usage=sum(
            attempt.input_tokens + attempt.output_tokens
            for respondent in result.respondents
            for attempt in respondent.attempts
        ),
        cost_usd=result.total_cost_usd,
        limitations=[
            "Synthetic personas are not sampled human respondents.",
            "Do not infer population prevalence, causality, or statistical significance.",
            "Provider and model changes can materially alter outputs.",
            *blueprint.limitations,
        ],
        manifest=manifest.model_dump(mode="json"),
    )
