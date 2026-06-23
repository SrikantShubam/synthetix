from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from synthetix.blueprints.models import ChoiceQuestion, LikertQuestion, OpenTextQuestion, Question, SimulationBlueprint
from synthetix.execution.manifest import RunManifest
from synthetix.execution.models import AttemptStatus, RunResult
from synthetix.reporting.models import (
    AnalyticsChart,
    ChartDecision,
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
MIN_CHART_BASE = 2
PROFESSIONAL_MIN_CHART_BASE = 30
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


def _echarts_donut_option(
    *,
    title: str,
    labels: list[str],
    values: list[int],
) -> dict[str, Any]:
    return {
        "animation": False,
        "title": {"text": title, "left": "left"},
        "tooltip": {"trigger": "item"},
        "legend": {"bottom": 0, "left": "center"},
        "series": [
            {
                "type": "pie",
                "radius": ["42%", "68%"],
                "avoidLabelOverlap": True,
                "label": {"show": True, "formatter": "{b}: {c}"},
                "data": [
                    {"name": label, "value": value}
                    for label, value in zip(labels, values, strict=False)
                ],
            }
        ],
    }


def _echarts_likert_option(
    *,
    title: str,
    labels: list[str],
    values: list[int],
) -> dict[str, Any]:
    palette = ["#9ecae1", "#6baed6", "#4292c6", "#2171b5", "#084594", "#08306b"]
    return {
        "animation": False,
        "title": {"text": title, "left": "left"},
        "tooltip": {"trigger": "item"},
        "grid": {"left": 56, "right": 24, "top": 56, "bottom": 72, "containLabel": True},
        "xAxis": {"type": "value", "minInterval": 1},
        "yAxis": {"type": "category", "data": ["Synthetic responses"]},
        "legend": {"bottom": 0, "left": "center"},
        "series": [
            {
                "name": label,
                "type": "bar",
                "stack": "total",
                "label": {"show": value > 0, "formatter": str(value)},
                "itemStyle": {"color": palette[index % len(palette)]},
                "data": [value],
            }
            for index, (label, value) in enumerate(zip(labels, values, strict=False))
        ],
    }


def _echarts_heatmap_option(
    *,
    title: str,
    row_labels: list[str],
    column_labels: list[str],
    matrix: list[list[int]],
) -> dict[str, Any]:
    values = [
        [column_index, row_index, value]
        for row_index, row in enumerate(matrix)
        for column_index, value in enumerate(row)
    ]
    max_value = max((value for row in matrix for value in row), default=0)
    return {
        "animation": False,
        "title": {"text": title, "left": "left"},
        "tooltip": {"position": "top"},
        "grid": {"left": 120, "right": 24, "top": 64, "bottom": 72, "containLabel": True},
        "xAxis": {"type": "category", "data": column_labels, "splitArea": {"show": True}},
        "yAxis": {"type": "category", "data": row_labels, "splitArea": {"show": True}},
        "visualMap": {
            "min": 0,
            "max": max_value,
            "calculable": False,
            "orient": "horizontal",
            "left": "center",
            "bottom": 0,
        },
        "series": [
            {
                "name": "Segment response count",
                "type": "heatmap",
                "data": values,
                "label": {"show": True},
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
                        suppression_reason="Suppressed because the segment base is below the minimum threshold.",
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
        use_donut = 3 <= len(values) <= 5 and sum(values) > 0
        charts.append(
            AnalyticsChart(
                chart_id=f"population:{composition.attribute}",
                title=title,
                chart_family="population_segment",
                visual_type="donut" if use_donut else "horizontal_bar",
                labels=labels,
                values=values,
                full_labels=full_labels,
                denominator=sum(values),
                option=(
                    _echarts_donut_option(title=title, labels=full_labels, values=values)
                    if use_donut
                    else _echarts_bar_option(
                        title=title,
                        labels=labels,
                        values=values,
                        y_axis_label="Synthetic respondents",
                        horizontal=True,
                    )
                ),
            )
        )
    return charts


def _build_segment_comparison_charts(question_reports: list[QuestionReport]) -> list[AnalyticsChart]:
    charts: list[AnalyticsChart] = []
    for report in question_reports:
        if report.chart_decision is not None and report.chart_decision.status != "rendered":
            continue
        if report.question_type not in {"choice", "likert"} or not report.distribution.labels:
            continue
        by_attribute: dict[str, list[SegmentCut]] = defaultdict(list)
        for cut in report.segment_cuts:
            if cut.suppressed or not cut.distribution.labels:
                continue
            by_attribute[cut.attribute].append(cut)
        for attribute, cuts in sorted(by_attribute.items()):
            row_labels: list[str] = []
            matrix: list[list[int]] = []
            for cut in cuts:
                values_by_label = dict(zip(cut.distribution.labels, cut.distribution.values, strict=False))
                matrix.append([int(values_by_label.get(label, 0)) for label in report.distribution.labels])
                row_labels.append(f"{attribute}: {cut.value}")
            if not row_labels:
                continue
            column_labels = list(report.distribution.labels)
            values = [value for row in matrix for value in row]
            title = f"{report.question_id} by {attribute.replace('_', ' ')}"
            charts.append(
                AnalyticsChart(
                    chart_id=f"segment:{report.question_id}:{attribute}",
                    title=title,
                    chart_family="segment_comparison",
                    visual_type="heatmap",
                    labels=[_wrap_chart_label(label) for label in column_labels],
                    values=values,
                    full_labels=column_labels,
                    row_labels=row_labels,
                    column_labels=column_labels,
                    matrix=matrix,
                    denominator=sum(sum(row) for row in matrix),
                    option=_echarts_heatmap_option(
                        title=title,
                        row_labels=row_labels,
                        column_labels=column_labels,
                        matrix=matrix,
                    ),
                )
            )
    return charts


def _build_question_chart(report: QuestionReport) -> AnalyticsChart | None:
    if report.question_type == "likert" and report.distribution.labels:
        labels = [_wrap_chart_label(label) for label in report.distribution.labels]
        values = list(report.distribution.values)
        return AnalyticsChart(
            chart_id=f"question:{report.question_id}",
            title=report.prompt,
            chart_family="question_distribution",
            visual_type="likert_stacked",
            labels=labels,
            values=values,
            full_labels=list(report.distribution.labels),
            denominator=report.denominators.valid_responses,
            option=_echarts_likert_option(
                title=report.prompt,
                labels=list(report.distribution.labels),
                values=values,
            ),
        )
    if report.question_type == "choice" and report.distribution.labels:
        labels = [_wrap_chart_label(label) for label in report.distribution.labels]
        values = list(report.distribution.values)
        full_labels = list(report.distribution.labels)
        use_donut = 2 <= len(values) <= 3 and sum(values) > 0
        use_horizontal = not use_donut and any(len(label) > 18 for label in full_labels)
        visual_type = "donut" if use_donut else "horizontal_bar" if use_horizontal else "bar"
        option: dict[str, Any]
        if use_donut:
            option = _echarts_donut_option(
                title=report.prompt,
                labels=full_labels,
                values=values,
            )
        else:
            option = _echarts_bar_option(
                title=report.prompt,
                labels=labels,
                values=values,
                y_axis_label="Synthetic responses",
                horizontal=use_horizontal,
            )
        return AnalyticsChart(
            chart_id=f"question:{report.question_id}",
            title=report.prompt,
            chart_family="question_distribution",
            visual_type=visual_type,
            labels=labels,
            values=values,
            full_labels=full_labels,
            denominator=report.denominators.valid_responses,
            option=option,
        )
    if report.question_type == "open_text" and report.themes:
        return None
    return None


def _chart_decision(
    report: QuestionReport,
    chart: AnalyticsChart | None,
    *,
    min_chart_base: int = MIN_CHART_BASE,
) -> ChartDecision:
    if report.denominators.valid_responses < min_chart_base:
        return ChartDecision(
            question_id=report.question_id,
            status="suppressed",
            reason=(
                "Question base is too small for a stable chart: "
                f"valid responses={report.denominators.valid_responses} is below the minimum base of {min_chart_base}."
            ),
        )
    if report.question_role == "diagnostic" and any(cut.suppressed for cut in report.segment_cuts):
        return ChartDecision(
            question_id=report.question_id,
            status="replaced_with_table",
            reason=(
                "This diagnostic reporting decision has at least one suppressed segment cut; "
                "a table preserves the base-size context better than a standalone chart."
            ),
            replacement_type="table",
        )
    prompt = report.prompt.casefold()
    if report.question_role == "diagnostic" and any(
        marker in prompt
        for marker in (
            "regional pattern",
            "country-group",
            "minimum-base",
            "unstable",
            "reported",
        )
    ):
        return ChartDecision(
            question_id=report.question_id,
            status="replaced_with_table",
            reason=(
                "This diagnostic item is a reporting decision about unstable segment cuts; "
                "a table preserves the base-size context better than a standalone chart."
            ),
            replacement_type="table",
        )
    if chart is not None and report.question_type in {"choice", "likert"} and report.distribution.labels:
        return ChartDecision(
            question_id=report.question_id,
            status="rendered",
            reason="Closed-ended distribution has a stable base and chart-safe categorical labels.",
            visual_type=chart.visual_type,
        )
    if report.question_type == "open_text" and report.themes:
        return ChartDecision(
            question_id=report.question_id,
            status="replaced_with_evidence_panel",
            reason="Open-text evidence is better shown through coded themes and quotes than a raw chart.",
            replacement_type="evidence_panel",
        )
    return ChartDecision(
        question_id=report.question_id,
        status="replaced_with_table",
        reason="No chart-safe series was available for this question.",
        replacement_type="table",
    )


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
    synthesis = _build_cross_question_synthesis(question_reports)
    if synthesis is not None:
        findings.append(synthesis)
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


def _build_cross_question_synthesis(question_reports: list[QuestionReport]) -> ExecutiveFinding | None:
    closed_summary: tuple[str, str, int, int, list[str]] | None = None
    qualitative_summary: tuple[str, str, int, int, list[str]] | None = None

    for question in question_reports:
        if (
            closed_summary is None
            and question.question_type in {"choice", "likert"}
            and question.distribution.labels
            and question.denominators.valid_responses > 0
        ):
            pairs = list(zip(question.distribution.labels, question.distribution.values, strict=False))
            top_label, top_count = max(pairs, key=lambda pair: (pair[1], pair[0]))
            if top_count > 0:
                evidence_quote_ids = [
                    quote.quote_id
                    for quote in question.quote_evidence
                    if _normalized_text(quote.text) == _normalized_text(top_label)
                ][:MAX_QUOTES]
                closed_summary = (
                    question.question_id,
                    top_label,
                    top_count,
                    question.denominators.valid_responses,
                    evidence_quote_ids,
                )
        if qualitative_summary is None and question.question_type == "open_text" and question.themes:
            theme = question.themes[0]
            qualitative_summary = (
                question.question_id,
                theme.label,
                theme.count,
                question.denominators.valid_responses,
                list(theme.supporting_quote_ids)[:MAX_QUOTES],
            )
        if closed_summary is not None and qualitative_summary is not None:
            break

    if closed_summary is None or qualitative_summary is None:
        return None

    closed_question_id, top_label, top_count, closed_base, closed_quotes = closed_summary
    qualitative_question_id, theme_label, theme_count, theme_base, theme_quotes = qualitative_summary
    evidence_quote_ids = [*closed_quotes, *theme_quotes][:MAX_QUOTES]
    return ExecutiveFinding(
        finding_id="cross-question-synthesis",
        title="Cross-question synthesis",
        summary=(
            "Across the dry-run questions, the leading closed-ended signal was "
            f"'{top_label}' on {closed_question_id} ({top_count}/{closed_base}), while the leading "
            f"coded rationale was '{theme_label}' on {qualitative_question_id} "
            f"({theme_count}/{theme_base}). Treat this as a hypothesis for human fieldwork, not a "
            "representative estimate."
        ),
        question_id=closed_question_id,
        evidence_quote_ids=evidence_quote_ids,
    )


def _build_objective_coverage(
    blueprint: SimulationBlueprint,
    question_reports: list[QuestionReport],
) -> list[ObjectiveCoverage]:
    research_design = blueprint.research_design
    if research_design is None:
        return []
    coverage: list[ObjectiveCoverage] = []
    for index, objective in enumerate(research_design.research_objectives):
        decision_question = (
            research_design.decision_questions[index]
            if index < len(research_design.decision_questions)
            else research_design.decision_questions[-1]
            if research_design.decision_questions
            else None
        )
        covered_question_ids = _questions_for_objective(
            objective=objective,
            decision_question=decision_question,
            question_reports=question_reports,
        )
        coverage.append(
            ObjectiveCoverage(
                objective=objective,
                decision_question=decision_question,
                covered_question_ids=covered_question_ids,
                status="covered" if covered_question_ids else "gap",
                notes=(
                    "Coverage is derived from objective-specific question role, prompt, and decision-question relevance."
                ),
            )
        )
    return coverage


def _questions_for_objective(
    *,
    objective: str,
    decision_question: str | None,
    question_reports: list[QuestionReport],
) -> list[str]:
    objective_text = f"{objective} {decision_question or ''}"
    objective_tokens = _semantic_tokens(objective_text)
    role_hints = _objective_role_hints(objective_text)
    needs_suppression_evidence = any(
        marker in objective_text.casefold()
        for marker in ("segment", "suppression", "suppress", "base", "regional", "subgroup")
    )
    scored: list[tuple[int, str]] = []

    for report in question_reports:
        score = 0
        if report.question_role in role_hints:
            score += 8
        if needs_suppression_evidence and report.question_role == "diagnostic":
            prompt = report.prompt.casefold()
            if any(
                marker in prompt
                for marker in ("unstable", "base", "bases", "regional", "reported", "report", "country-group", "subgroup")
            ):
                score += 6
        if report.question_type == "open_text" and "qualitative_probe" in role_hints:
            score += 2
        if report.question_type in {"choice", "likert"} and role_hints & {"primary_outcome", "driver"}:
            score += 1
        score += len(objective_tokens & _semantic_tokens(report.prompt))
        if score > 0:
            scored.append((score, report.question_id))

    if not scored:
        return []
    best_score = max(score for score, _question_id in scored)
    return [question_id for score, question_id in scored if score == best_score]


def _semantic_tokens(text: str) -> set[str]:
    tokens = {
        token.strip(".,;:!?()[]{}\"'").casefold()
        for token in text.replace("/", " ").replace("-", " ").split()
    }
    return {
        token
        for token in tokens
        if len(token) >= 4 and token not in _THEME_STOPWORDS
    }


def _objective_role_hints(text: str) -> set[str]:
    lowered = text.casefold()
    hints: set[str] = set()
    if any(marker in lowered for marker in ("theme", "barrier", "objection", "why", "rationale", "reason")):
        hints.add("qualitative_probe")
    if any(marker in lowered for marker in ("fit", "adopt", "proceed", "accept", "preference", "intent")):
        hints.add("primary_outcome")
    if any(marker in lowered for marker in ("driver", "factor", "influence", "importance")):
        hints.add("driver")
    if any(marker in lowered for marker in ("segment", "cut", "suppression", "base", "diagnostic")):
        hints.add("diagnostic")
    return hints or {"primary_outcome", "driver", "diagnostic", "qualitative_probe"}


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
    min_chart_base = (
        PROFESSIONAL_MIN_CHART_BASE
        if blueprint.research_design is not None
        and blueprint.research_design.requires_professional_quality_gate()
        else MIN_CHART_BASE
    )
    updated_question_reports: list[QuestionReport] = []
    for question_report in question_reports:
        chart = _build_question_chart(question_report)
        chart_decision = _chart_decision(
            question_report,
            chart,
            min_chart_base=min_chart_base,
        )
        updated_question_reports.append(
            question_report.model_copy(
                update={
                    "chart": chart if chart_decision.status == "rendered" else None,
                    "chart_decision": chart_decision,
                }
            )
        )
    question_reports = updated_question_reports
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
            segment_comparison_charts=_build_segment_comparison_charts(question_reports),
        ),
        research_design=blueprint.research_design,
        research_intake=blueprint.research_intake,
        objective_coverage=_build_objective_coverage(blueprint, question_reports),
        sensitivity_notes=[
            "Small synthetic populations can overstate apparent consensus.",
            "Changing the model, provider, or seed can materially alter outputs.",
        ],
        fieldwork_handoff=_build_fieldwork_handoff(blueprint),
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
        chart_decisions=[
            report.chart_decision
            for report in question_reports
            if report.chart_decision is not None
        ],
        warnings=_build_report_warnings(blueprint),
        limitations=[
            "Synthetic personas are not sampled human respondents.",
            "Do not infer population prevalence, causality, or statistical significance.",
            "Provider and model changes can materially alter outputs.",
            *blueprint.limitations,
        ],
        manifest=manifest.model_dump(mode="json"),
    )


def _build_report_warnings(blueprint: SimulationBlueprint) -> list[str]:
    warnings: list[str] = []
    research_design = blueprint.research_design
    if research_design is None:
        warnings.append("Synthetic scenario evidence only.")
        return warnings

    if research_design.disclosure_plan.synthetic_only_warning:
        warnings.append("Synthetic scenario evidence only.")
    if research_design.disclosure_plan.non_inferential_limits:
        warnings.append(
            "Do not infer prevalence, causality, or statistical significance from this report."
        )
    warnings.extend(research_design.disclosure_plan.data_quality_notes)
    return list(dict.fromkeys(warnings))


def _build_fieldwork_handoff(blueprint: SimulationBlueprint) -> list[str]:
    handoff = [
        "Use this dry run to refine wording, segment rules, and the human fieldwork plan before external decisions."
    ]
    research_intake = blueprint.research_intake
    if research_intake is not None and research_intake.target_population_size is not None:
        handoff.append(
            "Do not treat "
            f"{research_intake.intended_synthetic_panel_size} synthetic respondents as representative of the "
            f"{research_intake.target_population_size}-person target population."
        )
    elif research_intake is not None and research_intake.source_sample_size is not None:
        handoff.append(
            "Do not treat "
            f"{research_intake.intended_synthetic_panel_size} synthetic respondents as equivalent to the "
            f"{research_intake.source_sample_size}-response source study."
        )
    else:
        handoff.append("Target/source scale is incomplete; human fieldwork planning still needs explicit population sizing.")
    if research_intake is not None and research_intake.unresolved_gaps:
        handoff.extend(research_intake.unresolved_gaps[:2])
    return handoff
