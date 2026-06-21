from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Literal

from pypdf import PdfReader
from pydantic import BaseModel, Field

from synthetix.reporting.models import ReportModel
from synthetix.reporting.renderer import ReportArtifacts
from synthetix.reporting.renderer import _chart_labels as renderer_chart_labels


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


class ReportDepthEvidence(BaseModel):
    pdf_pages: int = Field(default=0, ge=0)
    word_count: int = Field(default=0, ge=0)
    chart_count: int = Field(default=0, ge=0)
    table_count: int = Field(default=0, ge=0)
    question_count: int = Field(default=0, ge=0)
    segment_cut_count: int = Field(default=0, ge=0)
    qualitative_theme_count: int = Field(default=0, ge=0)
    traceable_quote_count: int = Field(default=0, ge=0)
    min_pdf_pages: int = Field(default=12, ge=1)
    min_word_count: int = Field(default=3000, ge=1)
    min_chart_count: int = Field(default=6, ge=1)
    min_table_count: int = Field(default=8, ge=1)
    min_question_count: int = Field(default=3, ge=1)
    min_segment_cut_count: int = Field(default=4, ge=1)
    min_qualitative_theme_count: int = Field(default=6, ge=1)
    min_traceable_quote_count: int = Field(default=12, ge=1)


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
    report_depth: ReportDepthEvidence = Field(default_factory=ReportDepthEvidence)
    research_design_tier: str = "lightweight_exploration"
    objective_coverage: list[dict[str, object]] = Field(default_factory=list)
    research_objectives: list[str] = Field(default_factory=list)
    decision_questions: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    target_population_summary: str = ""
    sampling_frame_summary: str = ""
    segmentation_plan_summary: str = ""
    analysis_plan_summary: str = ""
    qualitative_coding_summary: str = ""
    standards_alignment_texts: list[str] = Field(default_factory=list)
    benchmark_wording_texts: list[str] = Field(default_factory=list)
    typed_answer_issues: list[str] = Field(default_factory=list)


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
            self._check_typed_answer_integrity(report_input.typed_answer_issues),
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
            self._check_report_depth(report_input.report_depth),
            self._check_research_design_requirement(report_input.research_design_tier),
            self._check_objective_coverage(
                report_input.research_design_tier,
                report_input.objective_coverage,
                report_input.decision_questions,
            ),
            self._check_standards_alignment(
                report_input.research_design_tier,
                report_input.assumptions,
                report_input.target_population_summary,
                report_input.sampling_frame_summary,
                report_input.segmentation_plan_summary,
                report_input.analysis_plan_summary,
                report_input.qualitative_coding_summary,
                report_input.standards_alignment_texts,
            ),
            self._check_benchmark_wording(report_input.benchmark_wording_texts),
        ]
        all_gates_passed = all(gate.passed for gate in hard_gates)
        passes_threshold = total_score >= self.passing_threshold and all_gates_passed
        accepted = passes_threshold and all_gates_passed
        return ReportQualityScore(
            total_score=total_score,
            threshold=self.passing_threshold,
            passes_threshold=passes_threshold,
            accepted=accepted,
            weighted_breakdown=weighted_breakdown,
            hard_gates=hard_gates,
        )

    def _check_typed_answer_integrity(self, issues: list[str]) -> HardGateResult:
        return HardGateResult(
            name="typed_answer_integrity",
            passed=not issues,
            detail="Typed question outputs use valid categorical or numeric answer labels."
            if not issues
            else "Invalid typed-answer labels: " + "; ".join(issues),
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
            if not _is_non_inferential_limit_warning(text)
            and any(pattern.search(text) for pattern in _INFERENTIAL_CLAIM_PATTERNS)
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

    def _check_report_depth(self, depth: ReportDepthEvidence) -> HardGateResult:
        missing = []
        if depth.pdf_pages < depth.min_pdf_pages:
            missing.append(f"pdf_pages {depth.pdf_pages} < {depth.min_pdf_pages}")
        if depth.word_count < depth.min_word_count:
            missing.append(f"word_count {depth.word_count} < {depth.min_word_count}")
        if depth.chart_count < depth.min_chart_count:
            missing.append(f"chart_count {depth.chart_count} < {depth.min_chart_count}")
        if depth.table_count < depth.min_table_count:
            missing.append(f"table_count {depth.table_count} < {depth.min_table_count}")
        if depth.question_count < depth.min_question_count:
            missing.append(f"question_count {depth.question_count} < {depth.min_question_count}")
        if depth.segment_cut_count < depth.min_segment_cut_count:
            missing.append(
                f"segment_cut_count {depth.segment_cut_count} < {depth.min_segment_cut_count}"
            )
        if depth.qualitative_theme_count < depth.min_qualitative_theme_count:
            missing.append(
                "qualitative_theme_count "
                f"{depth.qualitative_theme_count} < {depth.min_qualitative_theme_count}"
            )
        if depth.traceable_quote_count < depth.min_traceable_quote_count:
            missing.append(
                "traceable_quote_count "
                f"{depth.traceable_quote_count} < {depth.min_traceable_quote_count}"
            )
        return HardGateResult(
            name="professional_report_depth",
            passed=not missing,
            detail="Report meets professional depth thresholds."
            if not missing
            else "Insufficient depth: " + "; ".join(missing),
        )

    def _check_research_design_requirement(self, tier: str) -> HardGateResult:
        professional = tier == "professional"
        return HardGateResult(
            name="professional_research_design_required",
            passed=professional,
            detail="Professional report tier uses an explicit or confirmed ResearchDesign."
            if professional
            else "Lightweight exploration plans may execute but cannot pass professional report quality gates.",
        )

    def _check_objective_coverage(
        self,
        tier: str,
        objective_coverage: list[dict[str, object]],
        decision_questions: list[str],
    ) -> HardGateResult:
        if tier != "professional":
            return HardGateResult(
                name="research_objectives_covered",
                passed=False,
                detail="Objective coverage is only accepted for professional ResearchDesign plans.",
            )
        if not objective_coverage or not decision_questions:
            return HardGateResult(
                name="research_objectives_covered",
                passed=False,
                detail="Missing objective coverage or decision questions.",
            )
        missing = []
        for item in objective_coverage:
            covered = item.get("covered_question_ids")
            status = str(item.get("status", ""))
            if not isinstance(covered, list) or not covered or status == "gap":
                missing.append(str(item.get("objective", "unknown_objective")))
        return HardGateResult(
            name="research_objectives_covered",
            passed=not missing,
            detail="Every research objective maps to covered questions and decision support."
            if not missing
            else f"Missing objective coverage for: {missing}",
        )

    def _check_standards_alignment(
        self,
        tier: str,
        assumptions: list[str],
        target_population_summary: str,
        sampling_frame_summary: str,
        segmentation_plan_summary: str,
        analysis_plan_summary: str,
        qualitative_coding_summary: str,
        standards_alignment_texts: list[str],
    ) -> HardGateResult:
        if tier != "professional":
            return HardGateResult(
                name="standards_alignment_disclosure_complete",
                passed=False,
                detail="Lightweight exploration plans do not satisfy the professional standards-aligned disclosure gate.",
            )
        missing = []
        if not assumptions:
            missing.append("assumptions")
        if not target_population_summary.strip():
            missing.append("target_population")
        if not sampling_frame_summary.strip():
            missing.append("simulation_frame")
        if not segmentation_plan_summary.strip():
            missing.append("segmentation_plan")
        if not analysis_plan_summary.strip():
            missing.append("analysis_plan")
        if not qualitative_coding_summary.strip():
            missing.append("qualitative_coding_plan")
        if not standards_alignment_texts:
            missing.append("standards_alignment")
        return HardGateResult(
            name="standards_alignment_disclosure_complete",
            passed=not missing,
            detail="Professional report includes study-plan and standards-aligned disclosure coverage."
            if not missing
            else f"Missing disclosure coverage for: {missing}",
        )

    def _check_benchmark_wording(self, wording_texts: list[str]) -> HardGateResult:
        joined = " ".join(wording_texts).casefold()
        banned_accuracy = re.search(r"\baccuracy\b", joined) is not None
        required_label = "selected metric pass rate" in joined
        banned_replication = any(
            phrase in joined
            for phrase in (
                "full paper replication",
                "full table replication",
                "full chart replication",
                "full wording replication",
                "full report replication",
            )
        )
        passed = required_label and not banned_accuracy and not banned_replication
        detail = (
            "Benchmark wording uses selected metric pass rate language and avoids replication claims."
            if passed
            else "Benchmark wording must use selected metric pass rate language and avoid broad accuracy or replication claims."
        )
        return HardGateResult(
            name="benchmark_wording_uses_selected_metric_pass_rate",
            passed=passed,
            detail=detail,
        )


def _looks_like_narrative_label(label: str) -> bool:
    stripped = label.strip()
    tokens = re.findall(r"[A-Za-z0-9']+", stripped)
    if len(tokens) > 5:
        return True
    if len(stripped) > 48:
        return True
    return any(marker in stripped for marker in (".", "!", "?", ";", ":", "\n"))


def _is_non_inferential_limit_warning(text: str) -> bool:
    lowered = text.casefold()
    return "do not infer" in lowered or "non-inferential" in lowered


def build_quality_input(report: ReportModel, artifacts: ReportArtifacts) -> ReportQualityInput:
    checksums = {}
    if artifacts.checksums_path.exists():
        checksums = _read_checksum_file(artifacts.checksums_path)

    chart_labels = [
        label
        for question in report.questions
        for label in renderer_chart_labels(
            {
                "question_type": question.question_type,
                "labels": question.distribution.labels,
            }
        )
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
    research_design = report.research_design
    target_population_summary = ""
    sampling_frame_summary = ""
    segmentation_plan_summary = ""
    analysis_plan_summary = ""
    qualitative_coding_summary = ""
    standards_alignment_texts: list[str] = []
    benchmark_wording_texts: list[str] = []
    if research_design is not None:
        target_population_summary = "; ".join(
            [
                ", ".join(research_design.target_population_definition.inclusion_rules),
                research_design.target_population_definition.unit_of_analysis,
                research_design.target_population_definition.geography,
                research_design.target_population_definition.timeframe,
            ]
        ).strip("; ").strip()
        sampling_frame_summary = research_design.sampling_or_simulation_frame.persona_generation_frame
        segmentation_plan_summary = "; ".join(
            [
                ", ".join(research_design.segmentation_plan.segment_variables),
                ", ".join(research_design.segmentation_plan.planned_cuts),
                research_design.segmentation_plan.minimum_base_rule,
                research_design.segmentation_plan.suppression_rule,
            ]
        ).strip("; ").strip()
        analysis_plan_summary = "; ".join(
            research_design.analysis_plan.toplines
            + research_design.analysis_plan.cross_tabs
            + research_design.analysis_plan.theme_coding
            + research_design.analysis_plan.sensitivity_checks
            + research_design.analysis_plan.benchmark_checks
        )
        qualitative_coding_summary = "; ".join(
            [
                research_design.qualitative_coding_plan.coding_mode,
                research_design.qualitative_coding_plan.theme_granularity,
                f"minimum themes={research_design.qualitative_coding_plan.minimum_theme_count}",
            ]
        )
        standards_alignment_texts = (
            list(research_design.standards_alignment.iso_20252)
            + list(research_design.standards_alignment.aapor_disclosure)
            + list(research_design.standards_alignment.icc_esomar)
        )
        benchmark_wording_texts = list(research_design.analysis_plan.benchmark_checks) + list(
            research_design.disclosure_plan.data_quality_notes
        )
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
        report_depth=_derive_report_depth(report, artifacts),
        research_design_tier=(
            research_design.report_requirements.report_tier
            if research_design is not None
            else "lightweight_exploration"
        ),
        objective_coverage=[item.model_dump(mode="json") for item in report.objective_coverage],
        research_objectives=list(research_design.research_objectives) if research_design else [],
        decision_questions=list(research_design.decision_questions) if research_design else [],
        assumptions=list(research_design.assumptions) if research_design else [],
        target_population_summary=target_population_summary,
        sampling_frame_summary=sampling_frame_summary,
        segmentation_plan_summary=segmentation_plan_summary,
        analysis_plan_summary=analysis_plan_summary,
        qualitative_coding_summary=qualitative_coding_summary,
        standards_alignment_texts=standards_alignment_texts,
        benchmark_wording_texts=benchmark_wording_texts,
        typed_answer_issues=_derive_typed_answer_issues(report),
    )


def _derive_report_depth(report: ReportModel, artifacts: ReportArtifacts) -> ReportDepthEvidence:
    html_text = artifacts.html_path.read_text(encoding="utf-8") if artifacts.html_path.exists() else ""
    plain_text = re.sub(r"<[^>]+>", " ", html_text)
    word_count = len(re.findall(r"[A-Za-z0-9']+", plain_text))
    table_count = len(re.findall(r"<table\b", html_text, flags=re.IGNORECASE))
    chart_count = len(artifacts.chart_paths) + len(report.analytics.population_charts)
    segment_cut_count = sum(len(question.segment_cuts) for question in report.questions)
    qualitative_theme_count = sum(
        len(question.themes)
        + sum(len(segment.themes) for segment in question.segment_cuts)
        for question in report.questions
    )
    traceable_quote_count = sum(
        len(theme.supporting_quote_ids)
        for question in report.questions
        for theme in question.themes
    ) + sum(
        len(theme.supporting_quote_ids)
        for question in report.questions
        for segment in question.segment_cuts
        for theme in segment.themes
    ) + sum(len(question.quote_evidence) for question in report.questions)
    return ReportDepthEvidence(
        pdf_pages=_pdf_page_count(artifacts.pdf_path),
        word_count=word_count,
        chart_count=chart_count,
        table_count=table_count,
        question_count=len(report.questions),
        segment_cut_count=segment_cut_count,
        qualitative_theme_count=qualitative_theme_count,
        traceable_quote_count=traceable_quote_count,
    )


def _pdf_page_count(path: Path) -> int:
    if not path.exists():
        return 0
    try:
        return len(PdfReader(path).pages)
    except Exception:
        return 0


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


def _derive_typed_answer_issues(report: ReportModel) -> list[str]:
    issues: list[str] = []
    for question in report.questions:
        if question.question_type == "choice":
            bad_labels = [
                label for label in question.distribution.labels if _looks_like_narrative_label(label)
            ]
            if bad_labels:
                issues.append(
                    f"{question.question_id} choice labels contain narrative text: {bad_labels[:3]}"
                )
        elif question.question_type == "likert":
            if any(not re.fullmatch(r"-?\d+", label.strip()) for label in question.distribution.labels):
                issues.append(
                    f"{question.question_id} likert labels must be integers: {question.distribution.labels[:5]}"
                )
        elif (
            report.research_design is not None
            and report.research_design.requires_professional_quality_gate()
            and any(_looks_like_narrative_label(theme.label) for theme in question.themes)
        ):
            issues.append(
                f"{question.question_id} professional qualitative themes are still verbatim response variants"
            )
    return issues


def _derive_sections_present(report: ReportModel) -> list[str]:
    sections = ["title", "executive_summary", "question_results", "attrition", "limitations", "provenance", "appendix"]
    if report.methodology is not None:
        sections.append("methodology")
    if report.research_design is not None:
        sections.extend(["research_design", "objective_coverage", "standards_alignment_appendix"])
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
        if path.exists()
    ]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
