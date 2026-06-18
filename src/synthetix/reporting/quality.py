from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from synthetix.reporting.models import ReportModel
from synthetix.reporting.renderer import ReportArtifacts


CATEGORY_WEIGHTS: dict[str, float] = {
    "analytical_correctness": 30.0,
    "segmentation_and_bases": 20.0,
    "evidence_traceability": 15.0,
    "methodology_and_limitations": 15.0,
    "visual_readability_checks": 10.0,
    "reproducibility_and_artifact_integrity": 10.0,
}
PASSING_THRESHOLD = 85.0
REQUIRED_REPORT_SECTIONS: tuple[str, ...] = (
    "title",
    "executive_summary",
    "methodology",
    "question_results",
    "attrition",
    "limitations",
    "provenance",
    "appendix",
)
_INFERENTIAL_CLAIM_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bconfidence interval(s)?\b", re.IGNORECASE),
    re.compile(r"\bstatistical(ly)? significant\b", re.IGNORECASE),
    re.compile(r"\bstatistical significance\b", re.IGNORECASE),
    re.compile(r"\bpopulation prevalence\b", re.IGNORECASE),
)


class CategoryScores(BaseModel):
    analytical_correctness: float = Field(ge=0, le=100)
    segmentation_and_bases: float = Field(ge=0, le=100)
    evidence_traceability: float = Field(ge=0, le=100)
    methodology_and_limitations: float = Field(ge=0, le=100)
    visual_readability_checks: float = Field(ge=0, le=100)
    reproducibility_and_artifact_integrity: float = Field(ge=0, le=100)

    def weighted_breakdown(self) -> dict[str, float]:
        return {
            name: round(getattr(self, name) * weight / 100.0, 2)
            for name, weight in CATEGORY_WEIGHTS.items()
        }


class PercentageEvidence(BaseModel):
    label: str
    value: float
    numerator: float | int | None = None
    denominator: int | None = Field(default=None, gt=0)


class KeyFindingEvidence(BaseModel):
    finding_id: str
    text: str
    question_id: str | None = None
    response_evidence: list[str] = Field(default_factory=list)


class ArtifactChecksum(BaseModel):
    path: str
    expected_sha256: str
    actual_sha256: str

    @property
    def is_valid(self) -> bool:
        return self.expected_sha256 == self.actual_sha256


class AttritionEvidence(BaseModel):
    labels: list[str] = Field(default_factory=list)
    counts: dict[str, int] = Field(default_factory=dict)


class ReportQualityInput(BaseModel):
    category_scores: CategoryScores
    chart_labels: list[str] = Field(default_factory=list)
    percentages: list[PercentageEvidence] = Field(default_factory=list)
    key_findings: list[KeyFindingEvidence] = Field(default_factory=list)
    configured_population_dimensions: list[str] = Field(default_factory=list)
    composition_dimensions: list[str] = Field(default_factory=list)
    suppression_notes: dict[str, str] = Field(default_factory=dict)
    sections_present: list[str] = Field(default_factory=list)
    artifact_checksums: list[ArtifactChecksum] = Field(default_factory=list)
    non_inferential_warning_present: bool = False
    claim_texts: list[str] = Field(default_factory=list)
    attrition: AttritionEvidence = Field(default_factory=AttritionEvidence)


class HardGateResult(BaseModel):
    name: str
    passed: bool
    detail: str


class ReportQualityScore(BaseModel):
    total_score: float
    threshold: float = PASSING_THRESHOLD
    passes_threshold: bool
    accepted: bool
    weighted_breakdown: dict[str, float]
    hard_gates: list[HardGateResult] = Field(default_factory=list)

    @property
    def failed_hard_gates(self) -> list[str]:
        return [gate.name for gate in self.hard_gates if not gate.passed]


class BenchmarkRegistryEntry(BaseModel):
    benchmark_id: str
    display_name: str
    steward: str
    access_tier: Literal["public", "registration_required", "restricted"]
    download_permitted: bool
    restricted_data: bool
    source_url: str
    citation: str
    notes: str


class BenchmarkRegistry(BaseModel):
    version: str
    entries: list[BenchmarkRegistryEntry]


def load_benchmark_registry(path: Path) -> BenchmarkRegistry:
    return BenchmarkRegistry.model_validate_json(path.read_text(encoding="utf-8"))


class ReportQualityScorer:
    def __init__(self, *, passing_threshold: float = PASSING_THRESHOLD) -> None:
        self.passing_threshold = passing_threshold

    def evaluate(self, report_input: ReportQualityInput) -> ReportQualityScore:
        weighted_breakdown = report_input.category_scores.weighted_breakdown()
        total_score = round(sum(weighted_breakdown.values()), 2)
        hard_gates = [
            self._check_chart_labels(report_input.chart_labels),
            self._check_denominators(report_input.percentages),
            self._check_key_findings(report_input.key_findings),
            self._check_population_dimensions(
                report_input.configured_population_dimensions,
                report_input.composition_dimensions,
                report_input.suppression_notes,
            ),
            self._check_sections(report_input.sections_present),
            self._check_checksums(report_input.artifact_checksums),
            self._check_warning(report_input.non_inferential_warning_present),
            self._check_inferential_claims(report_input.claim_texts),
            self._check_attrition(report_input.attrition),
        ]
        passes_threshold = total_score >= self.passing_threshold
        accepted = passes_threshold and all(gate.passed for gate in hard_gates)
        return ReportQualityScore(
            total_score=total_score,
            threshold=self.passing_threshold,
            passes_threshold=passes_threshold,
            accepted=accepted,
            weighted_breakdown=weighted_breakdown,
            hard_gates=hard_gates,
        )

    def _check_chart_labels(self, labels: list[str]) -> HardGateResult:
        offenders = [label for label in labels if _looks_like_narrative_label(label)]
        return HardGateResult(
            name="no_raw_narrative_chart_labels",
            passed=not offenders,
            detail="All chart labels are short categorical values."
            if not offenders
            else f"Narrative labels found: {offenders}",
        )

    def _check_denominators(
        self, percentages: list[PercentageEvidence]
    ) -> HardGateResult:
        missing = [metric.label for metric in percentages if metric.denominator is None]
        return HardGateResult(
            name="every_percentage_has_denominator",
            passed=not missing,
            detail="All percentages include denominators."
            if not missing
            else f"Missing denominators for: {missing}",
        )

    def _check_key_findings(
        self, key_findings: list[KeyFindingEvidence]
    ) -> HardGateResult:
        invalid = [
            finding.finding_id
            for finding in key_findings
            if not finding.question_id or not finding.response_evidence
        ]
        return HardGateResult(
            name="key_findings_link_to_question_and_response_evidence",
            passed=not invalid,
            detail="Every key finding links to a question and response evidence."
            if not invalid
            else f"Missing evidence links for findings: {invalid}",
        )

    def _check_population_dimensions(
        self,
        configured_dimensions: list[str],
        composition_dimensions: list[str],
        suppression_notes: dict[str, str],
    ) -> HardGateResult:
        composition = set(composition_dimensions)
        covered = [
            dimension
            for dimension in configured_dimensions
            if dimension in composition or suppression_notes.get(dimension, "").strip()
        ]
        missing = sorted(set(configured_dimensions) - set(covered))
        return HardGateResult(
            name="population_dimensions_covered_or_suppressed",
            passed=not missing,
            detail="All configured population dimensions are shown or explicitly suppressed."
            if not missing
            else f"Missing composition or suppression notes for: {missing}",
        )

    def _check_sections(self, sections_present: list[str]) -> HardGateResult:
        missing = sorted(set(REQUIRED_REPORT_SECTIONS) - set(sections_present))
        return HardGateResult(
            name="required_sections_exist",
            passed=not missing,
            detail="All required report sections exist."
            if not missing
            else f"Missing sections: {missing}",
        )

    def _check_checksums(
        self, artifact_checksums: list[ArtifactChecksum]
    ) -> HardGateResult:
        if not artifact_checksums:
            return HardGateResult(
                name="artifact_checksums_validate",
                passed=False,
                detail="No artifact checksums were provided.",
            )
        invalid = [artifact.path for artifact in artifact_checksums if not artifact.is_valid]
        return HardGateResult(
            name="artifact_checksums_validate",
            passed=not invalid,
            detail="All artifact checksums validate."
            if not invalid
            else f"Checksum mismatches: {invalid}",
        )

    def _check_warning(self, warning_present: bool) -> HardGateResult:
        return HardGateResult(
            name="non_inferential_warning_exists",
            passed=warning_present,
            detail="The non-inferential warning exists."
            if warning_present
            else "The non-inferential warning is missing.",
        )

    def _check_inferential_claims(self, claim_texts: list[str]) -> HardGateResult:
        claims = [
            text
            for text in claim_texts
            if any(pattern.search(text) for pattern in _INFERENTIAL_CLAIM_PATTERNS)
        ]
        return HardGateResult(
            name="no_inferential_claims",
            passed=not claims,
            detail="No inferential claims were detected."
            if not claims
            else f"Inferential claims detected: {claims}",
        )

    def _check_attrition(self, attrition: AttritionEvidence) -> HardGateResult:
        labels = {label.casefold() for label in attrition.labels}
        failed_count = attrition.counts.get("failed", 0)
        refused_count = attrition.counts.get("refused", 0)
        failed_ok = failed_count == 0 or "failed" in labels
        refused_ok = refused_count == 0 or "refused" in labels
        passed = failed_ok and refused_ok
        return HardGateResult(
            name="attrition_represents_failed_and_refused",
            passed=passed,
            detail="Failed and refused respondents remain represented in attrition."
            if passed
            else "Attrition omits failed or refused respondents despite non-zero counts.",
        )


def _looks_like_narrative_label(label: str) -> bool:
    stripped = label.strip()
    tokens = re.findall(r"[A-Za-z0-9']+", stripped)
    if len(tokens) > 5:
        return True
    if len(stripped) > 48:
        return True
    return any(marker in stripped for marker in (".", "!", "?", ";", ":", "\n"))


def build_quality_input(report: ReportModel, artifacts: ReportArtifacts) -> ReportQualityInput:
    checksums = {}
    if artifacts.checksums_path.exists():
        checksums = _read_checksum_file(artifacts.checksums_path)

    chart_labels = [
        label
        for question in report.questions
        for label in question.distribution.labels
    ]
    percentages = [
        PercentageEvidence(
            label=f"{question.question_id}:{label}",
            value=(count / question.denominators.valid_responses) * 100
            if question.denominators.valid_responses
            else 0.0,
            numerator=count,
            denominator=question.denominators.valid_responses or None,
        )
        for question in report.questions
        for label, count in zip(question.distribution.labels, question.distribution.values)
    ]
    key_findings = [
        KeyFindingEvidence(
            finding_id=finding.finding_id,
            text=finding.summary,
            question_id=finding.question_id,
            response_evidence=list(finding.evidence_quote_ids),
        )
        for finding in report.executive_findings
    ]
    suppression_notes = {
        composition.attribute: "Suppressed due to minimum-base policy."
        for composition in report.segment_composition
        if any(segment.suppressed for segment in composition.segments)
    }
    claim_texts = [
        report.executive_summary,
        *[finding.summary for finding in report.executive_findings],
        *report.limitations,
    ]
    return ReportQualityInput(
        category_scores=_derive_category_scores(report, checksums),
        chart_labels=chart_labels,
        percentages=percentages,
        key_findings=key_findings,
        configured_population_dimensions=sorted(
            str(key) for key in report.population.get("attributes", {}).keys()
        ),
        composition_dimensions=[item.attribute for item in report.segment_composition],
        suppression_notes=suppression_notes,
        sections_present=_derive_sections_present(report),
        artifact_checksums=[
            ArtifactChecksum(
                path=path.name,
                expected_sha256=expected,
                actual_sha256=_sha256(path),
            )
            for path, expected in _expected_artifact_pairs(artifacts, checksums)
        ],
        non_inferential_warning_present=_contains_non_inferential_warning(
            artifacts.html_path.read_text(encoding="utf-8")
            if artifacts.html_path.exists()
            else report.executive_summary
        ),
        claim_texts=claim_texts,
        attrition=AttritionEvidence(
            labels=["succeeded", *sorted(report.failures.classifications.keys())],
            counts={
                "succeeded": report.failures.succeeded,
                "failed": report.failures.failed,
                **report.failures.classifications,
            },
        ),
    )


def _derive_category_scores(
    report: ReportModel,
    checksums: dict[str, str],
) -> CategoryScores:
    analytical = 100.0 if all(
        question.response_count == question.denominators.valid_responses
        for question in report.questions
    ) else 70.0
    segmentation = 100.0 if report.segment_composition else 60.0
    evidence = 100.0 if all(
        finding.question_id is not None
        for finding in report.executive_findings
    ) else 70.0
    methodology = 100.0 if report.methodology and report.limitations else 60.0
    readability = 100.0 if all(not _looks_like_narrative_label(label) for question in report.questions for label in question.distribution.labels) else 50.0
    reproducibility = 100.0 if checksums else 40.0
    return CategoryScores(
        analytical_correctness=analytical,
        segmentation_and_bases=segmentation,
        evidence_traceability=evidence,
        methodology_and_limitations=methodology,
        visual_readability_checks=readability,
        reproducibility_and_artifact_integrity=reproducibility,
    )


def _derive_sections_present(report: ReportModel) -> list[str]:
    sections = ["title", "executive_summary", "question_results", "attrition", "limitations", "provenance", "appendix"]
    if report.methodology is not None:
        sections.append("methodology")
    return sections


def _contains_non_inferential_warning(text: str) -> bool:
    lowered = text.casefold()
    return "non-inferential" in lowered or "do not infer prevalence" in lowered


def _read_checksum_file(path: Path) -> dict[str, str]:
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(loaded, dict):
        return {str(key): str(value) for key, value in loaded.items()}
    return {}


def _expected_artifact_pairs(
    artifacts: ReportArtifacts,
    checksums: dict[str, str],
) -> list[tuple[Path, str]]:
    files = [artifacts.json_path, artifacts.html_path, artifacts.pdf_path, *artifacts.chart_paths]
    return [
        (path, checksums.get(path.name, ""))
        for path in files
    ]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
