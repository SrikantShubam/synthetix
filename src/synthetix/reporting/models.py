from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class Distribution(BaseModel):
    labels: list[str] = Field(default_factory=list)
    values: list[int] = Field(default_factory=list)


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
    response_count: int
    distribution: Distribution
    quotes: list[str] = Field(default_factory=list)
    denominators: DenominatorSummary = Field(default_factory=DenominatorSummary)
    quote_evidence: list[QuoteEvidence] = Field(default_factory=list)
    themes: list[ThemeEvidence] = Field(default_factory=list)
    segment_cuts: list[SegmentCut] = Field(default_factory=list)


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
    sensitivity_notes: list[str] = Field(default_factory=list)
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
                )
            ],
            executive_findings=[
                ExecutiveFinding(
                    finding_id="finding-1",
                    title="Mixed synthetic concept fit",
                    summary="One synthetic respondent aligned positively while one surfaced price friction.",
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
