from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from synthetix.blueprints.models import ChoiceQuestion, LikertQuestion, OpenTextQuestion, Question, SimulationBlueprint
from synthetix.execution.manifest import RunManifest
from synthetix.execution.models import AttemptStatus, RunResult
from synthetix.reporting.models import (
    AnalyticsChart,
    DenominatorSummary,
    Distribution,
    ExecutiveFinding,
    FailureSummary,
    MethodologySummary,
    ObjectiveCoverage,
    ProvenanceSummary,
    QuestionReport,
    QuoteEvidence,
    ReportAnalytics,
    ReportModel,
    SegmentComposition,
    SegmentCompositionEntry,
    SegmentCut,
    ThemeEvidence,
)

MAX_QUOTES = 5
MIN_SEGMENT_BASE = 2
_THEME_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "because",
    "but",
    "by",
    "for",
    "from",
    "how",
    "i",
    "if",
    "in",
    "is",
    "it",
    "its",
    "my",
    "of",
    "on",
    "or",
    "so",
    "that",
    "the",
    "their",
    "there",
    "they",
    "this",
    "to",
    "very",
    "was",
    "we",
    "would",
}
_THEME_RULES: list[tuple[str, str, set[str]]] = [
    (
        "price_value",
        "Price sensitivity and value concern",
        {"price", "premium", "cost", "expensive", "value", "worth", "afford", "budget", "payback"},
    ),
    (
        "trust_credibility",
        "Trust and credibility concern",
        {"trust", "credible", "credibility", "real", "prove", "proof", "skeptic", "suspicious"},
    ),
    (
        "training_onboarding",
        "Training and onboarding friction",
        {"training", "onboarding", "learn", "learning", "setup", "effort", "workflow"},
    ),
    (
        "quality_taste",
        "Taste and product quality uncertainty",
        {"taste", "flavor", "quality", "portion", "quality-focused"},
    ),
    (
        "convenience_fit",
        "Convenience and workflow fit",
        {"convenience", "fit", "faster", "quick", "workflow", "slot", "easier"},
    ),
    (
        "competitive_alternatives",
        "Competitive price comparison",
        {"local", "alternative", "alternatives", "cheaper", "compare", "comparison"},
    ),
    (
        "impact_responsibility",
        "Impact and responsibility skepticism",
        {"offset", "carbon", "greenwashing", "responsibility", "consumer", "impact", "badge"},
    ),
    (
        "questionnaire_clarity",
        "Question wording clarity issue",
        {
            "word",
            "wording",
            "question",
            "questions",
            "clear",
            "clarity",
            "unclear",
            "leading",
            "option",
            "options",
            "feedback",
            "separate",
            "ask",
            "whether",
            "answer",
            "neutral",
        },
    ),
]


def _collapse_whitespace(value: str) -> str:
    return " ".join(value.split())


def _normalized_text(value: str) -> str:
    return _collapse_whitespace(value).casefold()


def _wrap_chart_label(value: str, width: int = 18) -> str:
    words = value.split()
    if not words:
        return value
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if len(candidate) <= width:
            current = candidate
            continue
        lines.append(current)
        current = word
    lines.append(current)
    return "\n".join(lines[:3])


def _theme_axis_label(value: str, index: int) -> str:
    words = _collapse_whitespace(value).split()
    compact = " ".join(words[:4]).strip(".,;:!?")
    compact = compact[:28].rstrip()
    if not compact:
        compact = f"Theme {index}"
    return f"Theme {index}: {compact}"


def _echarts_bar_option(
    *,
    title: str,
    labels: list[str],
    values: list[int],
    y_axis_label: str,
    horizontal: bool = False,
) -> dict[str, Any]:
    category_axis = {
        "type": "category",
        "data": labels,
        "axisLabel": {"interval": 0},
    }
    value_axis = {
        "type": "value",
        "name": y_axis_label,
        "minInterval": 1,
    }
    return {
        "animation": False,
        "title": {"text": title, "left": "left"},
        "tooltip": {"trigger": "axis"},
        "grid": {"left": 56, "right": 24, "top": 56, "bottom": 56, "containLabel": True},
        "xAxis": value_axis if horizontal else category_axis,
        "yAxis": category_axis if horizontal else value_axis,
        "series": [
            {
                "type": "bar",
                "data": values,
                "itemStyle": {"color": "#1f5f78"},
                "barWidth": "56%",
                "label": {"show": True, "position": "top" if not horizontal else "right"},
            }
        ],
    }


def _clean_open_text(value: Any) -> str | None:
    if value is None:
        return None
    cleaned = _collapse_whitespace(str(value))
    return cleaned or None


def _theme_tokens(value: str) -> list[str]:
    tokens = []
    for raw_token in value.casefold().replace("-", " ").split():
        token = raw_token.strip(".,;:!?()[]{}'\"")
        if not token or token in _THEME_STOPWORDS:
            continue
        if token.endswith("ing") and len(token) > 5:
            token = token[:-3]
        elif token.endswith("ed") and len(token) > 4:
            token = token[:-2]
        elif token.endswith("s") and len(token) > 4 and not token.endswith(("ss", "ness")):
            token = token[:-1]
        tokens.append(token)
    return tokens


def _theme_bucket(value: str) -> tuple[str, str]:
    tokens = _theme_tokens(value)
    token_set = set(tokens)
    for bucket_id, label, markers in _THEME_RULES:
        if token_set & markers:
            return bucket_id, label
    if not tokens:
        return "general_feedback", "General feedback"
    if len(tokens) == 1:
        return f"emergent:{tokens[0]}", f"{tokens[0].title()} concern"
    return (
        f"emergent:{tokens[0]}:{tokens[1]}",
        f"{tokens[0].title()} and {tokens[1].title()} concern",
    )


def _typed_quote_evidence(question_id: str, respondent: Any, answer_text: str) -> QuoteEvidence:
    return QuoteEvidence(
        quote_id=f"{question_id}:{respondent.persona_id}",
        persona_id=respondent.persona_id,
        text=answer_text,
        attributes=respondent.attributes,
    )


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
        key, label = _theme_bucket(cleaned)
        group = theme_groups.setdefault(
            key,
            {"label": label, "supporting_quote_ids": []},
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
) -> tuple[Distribution, list[QuoteEvidence], int]:
    counts: Counter[str] = Counter()
    quote_evidence: list[QuoteEvidence] = []
    for respondent in respondents:
        canonical = _canonicalize_choice(question, respondent.answers.get(question.id))
        if canonical is None:
            continue
        counts[canonical] += 1
        quote_evidence.append(_typed_quote_evidence(question.id, respondent, canonical))
    return (
        Distribution(
            labels=list(question.options),
            values=[counts.get(option, 0) for option in question.options],
        ),
        quote_evidence,
        len(quote_evidence),
    )


def _build_likert_distribution(
    question: LikertQuestion,
    respondents: list[Any],
) -> tuple[Distribution, list[QuoteEvidence], int]:
    counts: Counter[int] = Counter()
    quote_evidence: list[QuoteEvidence] = []
    for respondent in respondents:
        canonical = _canonicalize_likert(question, respondent.answers.get(question.id))
        if canonical is None:
            continue
        counts[canonical] += 1
        quote_evidence.append(_typed_quote_evidence(question.id, respondent, str(canonical)))
    scale = list(range(question.minimum, question.maximum + 1))
    return (
        Distribution(
            labels=[str(value) for value in scale],
            values=[counts.get(value, 0) for value in scale],
        ),
        quote_evidence,
        len(quote_evidence),
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


def _build_population_charts(segment_composition: list[SegmentComposition]) -> list[AnalyticsChart]:
    charts: list[AnalyticsChart] = []
    for composition in segment_composition:
        labels = [_wrap_chart_label(segment.value) for segment in composition.segments]
        values = [segment.count for segment in composition.segments]
        full_labels = [segment.value for segment in composition.segments]
        title = f"{composition.attribute.replace('_', ' ').title()} composition"
        charts.append(
            AnalyticsChart(
                chart_id=f"population:{composition.attribute}",
                title=title,
                chart_family="population_segment",
                labels=labels,
                values=values,
                full_labels=full_labels,
                denominator=sum(values),
                option=_echarts_bar_option(
                    title=title,
                    labels=labels,
                    values=values,
                    y_axis_label="Synthetic respondents",
                ),
            )
        )
    return charts


def _build_question_chart(report: QuestionReport) -> AnalyticsChart | None:
    if report.question_type in {"choice", "likert"} and report.distribution.labels:
        labels = [_wrap_chart_label(label) for label in report.distribution.labels]
        values = list(report.distribution.values)
        return AnalyticsChart(
            chart_id=f"question:{report.question_id}",
            title=report.prompt,
            chart_family="question_distribution",
            labels=labels,
            values=values,
            full_labels=list(report.distribution.labels),
            denominator=report.denominators.valid_responses,
            option=_echarts_bar_option(
                title=report.prompt,
                labels=labels,
                values=values,
                y_axis_label="Synthetic responses",
            ),
        )
    if report.question_type == "open_text" and report.themes:
        labels = [_theme_axis_label(theme.label, index) for index, theme in enumerate(report.themes, start=1)]
        values = [theme.count for theme in report.themes]
        full_labels = [theme.label for theme in report.themes]
        return AnalyticsChart(
            chart_id=f"question:{report.question_id}",
            title=f"{report.question_id} themes",
            chart_family="question_themes",
            labels=labels,
            values=values,
            full_labels=full_labels,
            denominator=report.denominators.valid_responses,
            option=_echarts_bar_option(
                title=f"{report.question_id} themes",
                labels=labels,
                values=values,
                y_axis_label="Theme mentions",
                horizontal=True,
            ),
        )
    return None


def _build_question_report(
    question: Question,
    *,
    total_personas: int,
    succeeded_respondents: list[Any],
    population_attributes: dict[str, list[str]],
    question_role: str | None,
) -> QuestionReport:
    answered_respondents = _answered_respondents(question.id, succeeded_respondents)
    if question.type == "choice":
        distribution, quote_evidence, valid_count = _build_choice_distribution(question, answered_respondents)
        return QuestionReport(
            question_id=question.id,
            prompt=question.prompt,
            question_type=question.type,
            question_role=question_role,
            response_count=valid_count,
            distribution=distribution,
            quotes=[quote.text for quote in quote_evidence[:MAX_QUOTES]],
            denominators=_build_denominators(
                total_personas=total_personas,
                succeeded_personas=len(succeeded_respondents),
                answered_responses=len(answered_respondents),
                valid_responses=valid_count,
            ),
            quote_evidence=quote_evidence,
            segment_cuts=_build_segment_cuts(question, succeeded_respondents, population_attributes),
        )

    if question.type == "likert":
        distribution, quote_evidence, valid_count = _build_likert_distribution(question, answered_respondents)
        return QuestionReport(
            question_id=question.id,
            prompt=question.prompt,
            question_type=question.type,
            question_role=question_role,
            response_count=valid_count,
            distribution=distribution,
            quotes=[quote.text for quote in quote_evidence[:MAX_QUOTES]],
            denominators=_build_denominators(
                total_personas=total_personas,
                succeeded_personas=len(succeeded_respondents),
                answered_responses=len(answered_respondents),
                valid_responses=valid_count,
            ),
            quote_evidence=quote_evidence,
            segment_cuts=_build_segment_cuts(question, succeeded_respondents, population_attributes),
        )

    quote_evidence, themes = _build_open_text_evidence(question, answered_respondents)
    return QuestionReport(
        question_id=question.id,
        prompt=question.prompt,
        question_type=question.type,
        question_role=question_role,
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
            evidence_quote_ids = [
                quote.quote_id
                for quote in question.quote_evidence
                if _normalized_text(quote.text) == _normalized_text(top_label)
            ][:MAX_QUOTES]
            findings.append(
                ExecutiveFinding(
                    finding_id=f"{question.question_id}-top-response",
                    title=f"Top response for {question.question_id}",
                    summary=(
                        f"'{top_label}' was the most common synthetic response "
                        f"({top_count}/{question.denominators.valid_responses})."
                    ),
                    question_id=question.question_id,
                    evidence_quote_ids=evidence_quote_ids,
                )
            )
        elif question.question_type == "open_text" and question.themes:
            theme = question.themes[0]
            findings.append(
                ExecutiveFinding(
                    finding_id=f"{question.question_id}-theme-1",
                    title=f"Leading theme for {question.question_id}",
                    summary=(
                        f"The leading qualitative theme was '{theme.label}' "
                        f"({theme.count}/{question.denominators.valid_responses})."
                    ),
                    question_id=question.question_id,
                    evidence_quote_ids=list(theme.supporting_quote_ids),
                )
            )
    return findings[:5]


def _build_objective_coverage(
    blueprint: SimulationBlueprint,
    question_reports: list[QuestionReport],
) -> list[ObjectiveCoverage]:
    research_design = blueprint.research_design
    if research_design is None:
        return []
    primary_questions = [
        report.question_id
        for report in question_reports
        if report.question_role in {"primary_outcome", "driver", "diagnostic", "qualitative_probe"}
    ]
    if not primary_questions:
        primary_questions = [report.question_id for report in question_reports]
    coverage: list[ObjectiveCoverage] = []
    for index, objective in enumerate(research_design.research_objectives):
        decision_question = (
            research_design.decision_questions[index]
            if index < len(research_design.decision_questions)
            else None
        )
        coverage.append(
            ObjectiveCoverage(
                objective=objective,
                decision_question=decision_question,
                covered_question_ids=primary_questions,
                status="covered" if primary_questions else "gap",
                notes=(
                    "Coverage is derived from planned primary, driver, diagnostic, and qualitative questions."
                ),
            )
        )
    return coverage


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
            question_role=(
                blueprint.research_design.question_role_map.get(question.id)
                if blueprint.research_design is not None
                else None
            ),
        )
        for question in blueprint.questions
    ]
    question_reports = [
        report.model_copy(update={"chart": _build_question_chart(report)})
        for report in question_reports
    ]
    failures: defaultdict[str, int] = defaultdict(int)
    retries = 0
    for respondent in result.respondents:
        retries += max(0, len(respondent.attempts) - 1)
        if respondent.status != AttemptStatus.SUCCEEDED:
            failures[respondent.status.value] += 1
    succeeded = len(succeeded_respondents)
    question_findings = _build_executive_findings(question_reports)
    segment_composition = _build_segment_composition(
        succeeded_respondents,
        blueprint.population.attributes,
    )
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
        segment_composition=segment_composition,
        analytics=ReportAnalytics(
            population_charts=_build_population_charts(segment_composition),
        ),
        research_design=blueprint.research_design,
        objective_coverage=_build_objective_coverage(blueprint, question_reports),
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
                "Benchmark comparisons, when present, are described as selected metric pass rates only and do not imply full paper, table, chart, wording, or report replication.",
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
