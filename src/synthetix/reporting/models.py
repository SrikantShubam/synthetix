from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field

from synthetix.blueprints.models import ResearchDesign, ResearchIntake


class Distribution(BaseModel):
    labels: list[str] = Field(default_factory=list)
    values: list[int] = Field(default_factory=list)


class AnalyticsChart(BaseModel):
    chart_id: str
    title: str
    chart_family: str
    visual_type: Literal["bar", "horizontal_bar", "likert_stacked", "donut"] = "bar"
    labels: list[str] = Field(default_factory=list)
    values: list[int] = Field(default_factory=list)
    full_labels: list[str] = Field(default_factory=list)
    denominator: int = 0
    option: dict[str, Any] = Field(default_factory=dict)


class ChartDecision(BaseModel):
    question_id: str | None = None
    status: Literal["rendered", "suppressed", "replaced_with_table", "replaced_with_evidence_panel"]
    reason: str


class ReportAnalytics(BaseModel):
    contract_version: str = "1.0"
    population_charts: list[AnalyticsChart] = Field(default_factory=list)


class DenominatorSummary(BaseModel):
    total_personas: int = 0
    succeeded_personas: int = 0
    answered_responses: int = 0
    valid_responses: int = 0
    missing_responses: int = 0
    invalid_responses: int = 0


class QuoteEvidence(BaseModel):
    quote_id: str
    persona_id: str
    text: str
    attributes: dict[str, str] = Field(default_factory=dict)


class ThemeEvidence(BaseModel):
    theme_id: str
    label: str
    count: int
    supporting_quote_ids: list[str] = Field(default_factory=list)


class SegmentCut(BaseModel):
    attribute: str
    value: str
    base_count: int
    suppressed: bool = False
    suppression_reason: str = ""
    distribution: Distribution = Field(default_factory=Distribution)
    themes: list[ThemeEvidence] = Field(default_factory=list)


class SegmentCompositionEntry(BaseModel):
    value: str
    count: int
    share: float
    suppressed: bool = False


class SegmentComposition(BaseModel):
    attribute: str
    segments: list[SegmentCompositionEntry] = Field(default_factory=list)


class ExecutiveFinding(BaseModel):
    finding_id: str
    title: str
    summary: str
    question_id: str | None = None
    evidence_quote_ids: list[str] = Field(default_factory=list)


class MethodologySummary(BaseModel):
    approach: str
    response_generation: str = ""
    quality_controls: list[str] = Field(default_factory=list)


class QuestionReport(BaseModel):
    question_id: str
    prompt: str
    question_type: str = "open_text"
    question_role: str | None = None
    response_count: int
    distribution: Distribution
    quotes: list[str] = Field(default_factory=list)
    denominators: DenominatorSummary = Field(default_factory=DenominatorSummary)
    quote_evidence: list[QuoteEvidence] = Field(default_factory=list)
    themes: list[ThemeEvidence] = Field(default_factory=list)
    segment_cuts: list[SegmentCut] = Field(default_factory=list)
    chart: AnalyticsChart | None = None
    chart_decision: ChartDecision | None = None


class FailureSummary(BaseModel):
    total_personas: int
    succeeded: int
    failed: int
    retries: int
    classifications: dict[str, int] = Field(default_factory=dict)


class ProvenanceSummary(BaseModel):
    model_id: str
    provider: str
    blueprint_hash: str
    manifest_hash: str
    protocol_version: str


class ObjectiveCoverage(BaseModel):
    objective: str
    decision_question: str | None = None
    covered_question_ids: list[str] = Field(default_factory=list)
    status: Literal["covered", "partial", "gap"] = "covered"
    notes: str = ""


class ReportModel(BaseModel):
    report_version: str = "2.0"
    run_id: str
    title: str
    purpose: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    executive_summary: str
    population: dict[str, Any]
    questions: list[QuestionReport]
    executive_findings: list[ExecutiveFinding] = Field(default_factory=list)
    segment_composition: list[SegmentComposition] = Field(default_factory=list)
    analytics: ReportAnalytics = Field(default_factory=ReportAnalytics)
    research_design: ResearchDesign | None = None
    research_intake: ResearchIntake | None = None
    chart_decisions: list[ChartDecision] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    objective_coverage: list[ObjectiveCoverage] = Field(default_factory=list)
    sensitivity_notes: list[str] = Field(default_factory=list)
    fieldwork_handoff: list[str] = Field(default_factory=list)
    methodology: MethodologySummary | None = None
    failures: FailureSummary
    provenance: ProvenanceSummary
    token_usage: int
    cost_usd: float
    limitations: list[str]
    manifest: dict[str, Any]

    @classmethod
    def example(cls) -> "ReportModel":
        return cls(
            run_id="example",
            title="Synthetic scenario exploration",
            purpose="Demonstrate a deterministic report.",
            generated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            executive_summary="Two synthetic personas described their scenario preferences.",
            population={"size": 2, "seed": 1, "attributes": {"region": ["urban", "rural"]}},
            questions=[
                QuestionReport(
                    question_id="q1",
                    prompt="Would this concept fit your scenario?",
                    response_count=2,
                    distribution=Distribution(labels=["yes", "no"], values=[1, 1]),
                    quotes=["It fits my needs.", "The price would be difficult."],
                    chart=AnalyticsChart(
                        chart_id="question:q1",
                        title="Would this concept fit your scenario?",
                        chart_family="question_distribution",
                        visual_type="bar",
                        labels=["yes", "no"],
                        values=[1, 1],
                        full_labels=["yes", "no"],
                        denominator=2,
                        option={
                            "animation": False,
                            "title": {"text": "Would this concept fit your scenario?", "left": "left"},
                            "tooltip": {"trigger": "axis"},
                            "grid": {"left": 56, "right": 24, "top": 56, "bottom": 56, "containLabel": True},
                            "xAxis": {"type": "category", "data": ["yes", "no"], "axisLabel": {"interval": 0}},
                            "yAxis": {"type": "value", "name": "Synthetic responses", "minInterval": 1},
                            "series": [
                                {
                                    "type": "bar",
                                    "data": [1, 1],
                                    "itemStyle": {"color": "#1f5f78"},
                                    "barWidth": "56%",
                                    "label": {"show": True, "position": "top"},
                                }
                            ],
                        },
                    ),
                )
            ],
            chart_decisions=[
                ChartDecision(
                    question_id="q1",
                    status="rendered",
                    reason="Closed-ended distribution has a stable base and chart-safe categorical labels.",
                )
            ],
            warnings=[
                "Synthetic scenario evidence only.",
                "Do not infer prevalence, causality, or statistical significance from this report.",
            ],
            executive_findings=[
                ExecutiveFinding(
                    finding_id="finding-1",
                    title="Mixed synthetic concept fit",
                    summary="One synthetic respondent aligned positively while one surfaced price friction.",
                )
            ],
            research_design=ResearchDesign(
                study_type="concept_test",
                research_objectives=["Measure synthetic concept fit."],
                decision_questions=["Should the concept proceed to human fieldwork?"],
                assumptions=[
                    "Synthetic outputs are exploratory only.",
                    "No inferential claims are supported.",
                ],
                target_population_definition={
                    "inclusion_rules": ["Declared synthetic personas only."],
                    "exclusion_rules": ["Undeclared populations are out of scope."],
                    "unit_of_analysis": "Synthetic respondent",
                },
                sampling_or_simulation_frame={
                    "persona_generation_frame": "Declared attribute grid over region.",
                    "quotas_or_weights": ["No weighting applied."],
                    "uncovered_groups": ["Undeclared regions."],
                },
                segmentation_plan={
                    "segment_variables": ["region"],
                    "planned_cuts": ["region"],
                    "minimum_base_rule": "Suppress slices below n=2.",
                    "suppression_rule": "Explicitly mark suppressed slices.",
                },
                question_role_map={"q1": "primary_outcome"},
                analysis_plan={
                    "toplines": ["Concept fit topline."],
                    "cross_tabs": ["Concept fit by region."],
                    "likert_summaries": [],
                    "rankings": [],
                    "theme_coding": [],
                    "sensitivity_checks": ["Review failed attempts."],
                    "benchmark_checks": [
                        "Benchmark comparisons, when present, use selected metric pass rate wording only."
                    ],
                },
                qualitative_coding_plan={
                    "coding_mode": "deterministic",
                    "theme_granularity": "Semantic barrier themes",
                    "quote_evidence_required": True,
                    "minimum_theme_count": 1,
                },
                report_requirements={
                    "report_tier": "professional",
                    "required_sections": [
                        "research_design",
                        "objective_coverage",
                        "standards_alignment_appendix",
                    ],
                    "minimum_figures": 1,
                    "minimum_tables": 1,
                    "appendix_requirements": ["Planned-vs-delivered appendix"],
                    "audience_level": "professional",
                },
                disclosure_plan={
                    "synthetic_only_warning": True,
                    "non_inferential_limits": True,
                    "model_provider_provenance": True,
                    "data_quality_notes": ["Synthetic scenario evidence only."],
                },
                standards_alignment={
                    "iso_20252": ["Purpose and process disclosure."],
                    "aapor_disclosure": ["Questionnaire and denominator disclosure."],
                    "icc_esomar": ["Transparency disclosure."],
                },
            ),
            objective_coverage=[
                ObjectiveCoverage(
                    objective="Measure synthetic concept fit.",
                    decision_question="Should the concept proceed to human fieldwork?",
                    covered_question_ids=["q1"],
                    status="covered",
                    notes="Topline and segment comparisons cover the primary outcome.",
                )
            ],
            methodology=MethodologySummary(
                approach="Synthetic persona scenario exploration with deterministic aggregation.",
                response_generation="One response per synthetic persona with retries retained.",
                quality_controls=[
                    "Question distributions include explicit denominators.",
                    "Failures remain represented in attrition accounting.",
                ],
            ),
            analytics=ReportAnalytics(
                population_charts=[
                    AnalyticsChart(
                        chart_id="population:region",
                        title="Region composition",
                        chart_family="population_segment",
                        visual_type="donut",
                        labels=["urban", "rural"],
                        values=[1, 1],
                        full_labels=["urban", "rural"],
                        denominator=2,
                        option={
                            "animation": False,
                            "title": {"text": "Region composition", "left": "left"},
                            "tooltip": {"trigger": "axis"},
                            "grid": {"left": 56, "right": 24, "top": 56, "bottom": 56, "containLabel": True},
                            "xAxis": {"type": "category", "data": ["urban", "rural"], "axisLabel": {"interval": 0}},
                            "yAxis": {"type": "value", "name": "Synthetic respondents", "minInterval": 1},
                            "series": [
                                {
                                    "type": "bar",
                                    "data": [1, 1],
                                    "itemStyle": {"color": "#1f5f78"},
                                    "barWidth": "56%",
                                    "label": {"show": True, "position": "top"},
                                }
                            ],
                        },
                    )
                ]
            ),
            failures=FailureSummary(
                total_personas=2,
                succeeded=2,
                failed=0,
                retries=0,
            ),
            provenance=ProvenanceSummary(
                model_id="example/model",
                provider="example",
                blueprint_hash="0" * 64,
                manifest_hash="1" * 64,
                protocol_version="1.0",
            ),
            token_usage=100,
            cost_usd=0.01,
            limitations=["Example data only."],
            manifest={"example": True},
        )
