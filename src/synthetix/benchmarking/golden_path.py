from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from synthetix.analysis.reporting import build_report
from synthetix.blueprints.models import (
    ChoiceQuestion,
    LikertQuestion,
    OpenTextQuestion,
    PopulationSpec,
    QuestionRole,
    ResearchDesign,
    ResearchIntake,
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
from synthetix.ingestion.documents import DocumentLimits, extract_document
from synthetix.ingestion.intake import ensure_professional_document_intake_allowed
from synthetix.reporting.quality import ReportQualityScorer, build_quality_input
from synthetix.reporting.renderer import (
    render_report,
)


FixtureClass = Literal[
    "novice_concept_test",
    "professional_survey_dry_run",
    "bad_input_document",
]

QUALITY_THRESHOLD = 85.0
PROFESSIONAL_MIN_SYNTHETIC_PANEL_SIZE = 100


class GoldenPathSourceMaterial(BaseModel):
    format: Literal["markdown_brief", "pdf_brief", "scanned_pdf_simulation"]
    title: str
    body: str


class TestCaseSourceDocument(BaseModel):
    path: str
    paper_id: str
    title: str


class ContractFieldExpectation(BaseModel):
    field: str
    expected_markers: list[str] = Field(min_length=1)
    min_matches: int = Field(default=1, ge=1)


class ExpectedResearchIntake(BaseModel):
    mode: Literal["novice", "professional"]
    source_type: str
    research_context: str
    target_population_summary: str
    target_population_size: int | None = None
    source_sample_size: int | None = None
    intended_synthetic_panel_size: int = Field(ge=1)
    segment_variables: list[str] = Field(default_factory=list)
    expected_analyses: list[str] = Field(default_factory=list)
    unresolved_gaps: list[str] = Field(default_factory=list)
    extraction_confidence_expectation: Literal["low", "medium", "high", "n/a"]
    professional_mode_blocked_without_gemini: bool = False


class ExpectedStudyPlan(BaseModel):
    study_type: str
    objectives: list[str] = Field(default_factory=list)
    decision_questions: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    question_roles: dict[str, str] = Field(default_factory=dict)
    chart_plan: list[str] = Field(default_factory=list)


class ExpectedQuestionRationale(BaseModel):
    question_id: str
    role: str
    rationale: str


class ExpectedChartDecision(BaseModel):
    question_id: str
    status: Literal["rendered", "suppressed", "replaced_with_table", "replaced_with_evidence_panel"]
    reason_contains: str


class GoldenPathFixture(BaseModel):
    fixture_id: str
    fixture_class: FixtureClass
    source_material: GoldenPathSourceMaterial
    test_case_source_document: TestCaseSourceDocument | None = None
    expected_contract_fields: list[ContractFieldExpectation] = Field(default_factory=list)
    expected_research_intake: ExpectedResearchIntake
    expected_study_plan: ExpectedStudyPlan
    expected_question_rationales: list[ExpectedQuestionRationale] = Field(default_factory=list)
    expected_synthetic_panel_limits: dict[str, int | str | bool] = Field(default_factory=dict)
    expected_segmentation_behavior: dict[str, object] = Field(default_factory=dict)
    expected_chart_decisions: list[ExpectedChartDecision] = Field(default_factory=list)
    expected_report_warnings: list[str] = Field(default_factory=list)
    expected_human_fieldwork_handoff: list[str] = Field(default_factory=list)


class FixtureProof(BaseModel):
    fixture_id: str
    fixture_class: FixtureClass
    source_file: str
    source_format: str
    extraction_method: str
    extraction_confidence: str
    professional_mode_blocked_without_gemini: bool
    expected_blocked_without_gemini: bool
    observed_contract_path: str | None = None
    comparison_path: str | None = None


class FixtureReportProof(BaseModel):
    fixture_id: str
    fixture_class: FixtureClass
    expected_report_tier: Literal["professional", "lightweight_exploration", "blocked_intake"]
    expected_acceptance: Literal["accepted", "rejected", "blocked", "lightweight_only"]
    generated: bool
    accepted: bool
    failed_hard_gates: list[str] = Field(default_factory=list)
    report_artifacts: list[str] = Field(default_factory=list)
    report_quality_path: str | None = None


class ContractFieldObservation(BaseModel):
    field: str
    expected_markers: list[str]
    matched_markers: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)


class ObservedContract(BaseModel):
    fixture_id: str
    source_file: str
    paper_id: str = ""
    extraction_method: str
    extraction_confidence: str
    text_characters: int
    professional_mode_blocked_without_gemini: bool
    fields: list[ContractFieldObservation] = Field(default_factory=list)


class ContractFieldComparison(BaseModel):
    field: str
    expected_markers: list[str]
    matched_markers: list[str]
    passed: bool
    evidence: list[str] = Field(default_factory=list)


class ContractComparison(BaseModel):
    fixture_id: str
    source_file: str
    status: Literal["matched", "blocked_as_expected", "failed"]
    passed: bool
    fields: list[ContractFieldComparison] = Field(default_factory=list)


class GoldenPathProofSummary(BaseModel):
    fixture_count: int
    classes_present: list[FixtureClass]
    proofs: list[FixtureProof] = Field(default_factory=list)
    fixture_report_proofs: list[FixtureReportProof] = Field(default_factory=list)
    report_artifacts: list[str] = Field(default_factory=list)
    report_quality_path: str | None = None
    contract_artifact: str


def load_golden_path_fixtures(validation_dir: Path) -> list[GoldenPathFixture]:
    fixtures: list[GoldenPathFixture] = []
    for path in sorted(validation_dir.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict) or "fixture_class" not in payload:
            continue
        fixtures.append(GoldenPathFixture.model_validate(payload))
    return fixtures


def validate_golden_path_fixture_set(fixtures: list[GoldenPathFixture]) -> list[str]:
    findings: list[str] = []
    required_classes: set[FixtureClass] = {
        "novice_concept_test",
        "professional_survey_dry_run",
        "bad_input_document",
    }
    present_classes = {fixture.fixture_class for fixture in fixtures}
    missing_classes = sorted(required_classes - present_classes)
    if missing_classes:
        findings.append(f"Missing golden-path fixture classes: {', '.join(missing_classes)}")
    for fixture in fixtures:
        if not fixture.expected_study_plan.objectives:
            findings.append(f"{fixture.fixture_id}: expected_study_plan.objectives missing")
        if not fixture.expected_question_rationales:
            findings.append(f"{fixture.fixture_id}: expected_question_rationales missing")
        if not fixture.expected_chart_decisions:
            findings.append(f"{fixture.fixture_id}: expected_chart_decisions missing")
        if not fixture.expected_report_warnings:
            findings.append(f"{fixture.fixture_id}: expected_report_warnings missing")
        if fixture.expected_research_intake.mode == "professional":
            if not fixture.expected_research_intake.segment_variables:
                findings.append(f"{fixture.fixture_id}: professional fixture missing segment_variables")
            if not fixture.expected_contract_fields:
                findings.append(f"{fixture.fixture_id}: professional fixture missing expected_contract_fields")
        if (
            fixture.expected_research_intake.mode == "professional"
            and fixture.fixture_class == "professional_survey_dry_run"
        ):
            if not str(fixture.expected_segmentation_behavior.get("minimum_base_rule", "")).strip():
                findings.append(
                    f"{fixture.fixture_id}: professional fixture missing expected_segmentation_behavior.minimum_base_rule"
                )
            if not str(fixture.expected_segmentation_behavior.get("suppression_rule", "")).strip():
                findings.append(
                    f"{fixture.fixture_id}: professional fixture missing expected_segmentation_behavior.suppression_rule"
                )
            if not fixture.expected_human_fieldwork_handoff:
                findings.append(
                    f"{fixture.fixture_id}: professional fixture missing expected_human_fieldwork_handoff"
                )
        if (
            fixture.fixture_class == "professional_survey_dry_run"
            and fixture.test_case_source_document is not None
            and fixture.expected_research_intake.intended_synthetic_panel_size
            < PROFESSIONAL_MIN_SYNTHETIC_PANEL_SIZE
        ):
            findings.append(
                f"{fixture.fixture_id}: professional fixture minimum synthetic panel size is "
                f"{PROFESSIONAL_MIN_SYNTHETIC_PANEL_SIZE}"
            )
        if (
            fixture.fixture_class == "professional_survey_dry_run"
            and fixture.test_case_source_document is not None
            and fixture.source_material.title.strip() != fixture.test_case_source_document.title.strip()
        ):
            findings.append(
                f"{fixture.fixture_id}: source_material.title must match test_case_source_document.title"
            )
        if fixture.fixture_class == "bad_input_document" and not fixture.expected_contract_fields:
            findings.append(f"{fixture.fixture_id}: bad-input fixture must not use empty expected_contract_fields")
        if _invalid_question_roles(fixture.expected_study_plan.question_roles):
            findings.append(
                f"{fixture.fixture_id}: expected_study_plan.question_roles contains unsupported values"
            )
        invalid_role_assignments = _invalid_role_assignments(
            fixture.expected_study_plan.question_roles
        )
        if invalid_role_assignments:
            findings.append(
                f"{fixture.fixture_id}: invalid role-to-question assignments: {', '.join(invalid_role_assignments)}"
            )
    return findings


def generate_golden_path_proof(
    workspace: Path,
    *,
    validation_dir: Path | None = None,
    output_dir: Path | None = None,
) -> GoldenPathProofSummary:
    fixture_dir = validation_dir or workspace / "research/benchmark_program/validation"
    fixtures = load_golden_path_fixtures(fixture_dir)
    findings = validate_golden_path_fixture_set(fixtures)
    if findings:
        raise ValueError("; ".join(findings))

    contract_path = workspace / "research/golden_paper_contract.json"
    if not contract_path.exists():
        raise ValueError("Golden paper contract is missing at research/golden_paper_contract.json")

    proof_root = output_dir or workspace / "data/golden-path"
    source_dir = proof_root / "source-docs"
    intake_dir = proof_root / "intake-proof"
    report_dir = proof_root / "report-proof"
    fixture_report_dir = proof_root / "fixture-report-proof"
    source_dir.mkdir(parents=True, exist_ok=True)
    intake_dir.mkdir(parents=True, exist_ok=True)

    proofs: list[FixtureProof] = []
    professional_fixture: GoldenPathFixture | None = None
    blocked_by_fixture_id: dict[str, bool] = {}
    for fixture in fixtures:
        source_file = _resolve_or_write_source_material(workspace, source_dir, fixture)
        extraction_method = "structured_brief"
        extraction_confidence = "n/a"
        blocked_without_gemini = False
        observed_contract_path = None
        comparison_path = None
        text = fixture.source_material.body

        if source_file.suffix.lower() == ".pdf":
            extracted = extract_document(
                source_file,
                DocumentLimits(max_bytes=40_000_000, max_pdf_pages=120),
            )
            extraction_method = extracted.extraction_method
            extraction_confidence = extracted.extraction_confidence
            text = extracted.text
            try:
                ensure_professional_document_intake_allowed(
                    extracted,
                    professional_mode=fixture.expected_research_intake.mode == "professional",
                    used_gemini=False,
                )
            except ValueError:
                blocked_without_gemini = True
            observed_contract_path = _write_observed_contract(
                workspace=workspace,
                intake_dir=intake_dir,
                fixture=fixture,
                source_file=source_file,
                text=text,
                extraction_method=extraction_method,
                extraction_confidence=extraction_confidence,
                professional_mode_blocked_without_gemini=blocked_without_gemini,
            )
            comparison_path = _write_contract_comparison(
                workspace=workspace,
                intake_dir=intake_dir,
                fixture=fixture,
                source_file=source_file,
                text=text,
                professional_mode_blocked_without_gemini=blocked_without_gemini,
            )
        elif source_file.suffix.lower() == ".md":
            observed_contract_path = _write_observed_contract(
                workspace=workspace,
                intake_dir=intake_dir,
                fixture=fixture,
                source_file=source_file,
                text=text,
                extraction_method=extraction_method,
                extraction_confidence=extraction_confidence,
                professional_mode_blocked_without_gemini=blocked_without_gemini,
            )

        proofs.append(
            FixtureProof(
                fixture_id=fixture.fixture_id,
                fixture_class=fixture.fixture_class,
                source_file=_artifact_path(source_file, workspace),
                source_format=fixture.source_material.format,
                extraction_method=extraction_method,
                extraction_confidence=extraction_confidence,
                professional_mode_blocked_without_gemini=blocked_without_gemini,
                expected_blocked_without_gemini=fixture.expected_research_intake.professional_mode_blocked_without_gemini,
                observed_contract_path=observed_contract_path,
                comparison_path=comparison_path,
            )
        )
        blocked_by_fixture_id[fixture.fixture_id] = blocked_without_gemini
        if fixture.fixture_class == "professional_survey_dry_run" and (
            professional_fixture is None
            or (
                professional_fixture.test_case_source_document is None
                and fixture.test_case_source_document is not None
            )
        ):
            professional_fixture = fixture

    if professional_fixture is None:
        raise ValueError("Golden-path proof requires one professional_survey_dry_run fixture")

    fixture_report_proofs = [
        _write_fixture_report_proof(
            workspace=workspace,
            fixture_report_dir=fixture_report_dir,
            fixture=fixture,
            blocked_without_gemini=blocked_by_fixture_id.get(fixture.fixture_id, False),
        )
        for fixture in fixtures
    ]
    report_artifacts, report_quality_path, _ = _write_report_proof(
        report_dir=report_dir,
        workspace=workspace,
        fixture=professional_fixture,
    )
    _validate_chart_decision_expectations(
        fixture=professional_fixture,
        report_artifacts=report_artifacts,
        workspace=workspace,
    )
    summary = GoldenPathProofSummary(
        fixture_count=len(fixtures),
        classes_present=sorted({fixture.fixture_class for fixture in fixtures}),
        proofs=proofs,
        fixture_report_proofs=fixture_report_proofs,
        report_artifacts=report_artifacts,
        report_quality_path=report_quality_path,
        contract_artifact=_artifact_path(contract_path, workspace),
    )
    summary_path = intake_dir / "proof-summary.json"
    summary_path.write_text(summary.model_dump_json(indent=2), encoding="utf-8")
    return summary


def _resolve_or_write_source_material(
    workspace: Path,
    directory: Path,
    fixture: GoldenPathFixture,
) -> Path:
    if fixture.test_case_source_document is not None:
        source = workspace / fixture.test_case_source_document.path
        if not source.exists():
            raise ValueError(f"{fixture.fixture_id}: test-case source does not exist: {source}")
        return source
    return _write_source_material(directory, fixture)


def _write_source_material(directory: Path, fixture: GoldenPathFixture) -> Path:
    material = fixture.source_material
    if material.format == "markdown_brief":
        path = directory / f"{fixture.fixture_id}.md"
        path.write_text(f"# {material.title}\n\n{material.body}\n", encoding="utf-8")
        return path

    path = directory / f"{fixture.fixture_id}.pdf"
    pdf = canvas.Canvas(str(path), pagesize=A4, pageCompression=1, invariant=1)
    y = A4[1] - 48
    lines = _pdf_lines(material)
    for line in lines:
        if y < 54:
            pdf.showPage()
            y = A4[1] - 48
        pdf.drawString(48, y, line[:100])
        y -= 12
    pdf.save()
    return path


def _pdf_lines(material: GoldenPathSourceMaterial) -> list[str]:
    if material.format == "scanned_pdf_simulation":
        return [material.title, "", "scan", "", "layout"]
    body_lines = [line.strip() for line in material.body.splitlines() if line.strip()]
    if not body_lines:
        body_lines = [material.body]
    return [material.title, ""] + body_lines * 4


def _write_report_proof(
    *,
    report_dir: Path,
    workspace: Path,
    fixture: GoldenPathFixture,
) -> tuple[list[str], str, list[str]]:
    report_dir.mkdir(parents=True, exist_ok=True)
    blueprint = _build_blueprint_from_fixture(fixture)
    result = _build_run_result_from_fixture(fixture)
    source_hashes = (
        {fixture.test_case_source_document.path: "golden-path-proof"}
        if fixture.test_case_source_document is not None
        else {f"{fixture.fixture_id}.md": "golden-path-brief"}
    )
    manifest = RunManifest.create(
        run_id="golden-path-proof",
        blueprint=blueprint,
        source_hashes=source_hashes,
        model_id="synthetix/deterministic-proof",
        provider="synthetix",
        parameters={"mode": "golden-path-proof"},
    )
    report = build_report(blueprint, result, manifest).model_copy(
        update={
            "title": fixture.source_material.title,
            "purpose": fixture.expected_research_intake.research_context,
            "executive_summary": (
                "Deterministic golden-path validation run exercising the real report pipeline "
                "against the professional survey dry-run contract."
            ),
            "limitations": list(dict.fromkeys([
                "Limitations: synthetic outputs are exploratory scenario evidence only and are not representative human survey results.",
                "Limitations: distributional patterns, segment and equity checks, and qualitative themes require human validation before decisions.",
                "Limitations: multivariate clustering and joint respondent structure are not recovered by this deterministic dry run.",
                *fixture.expected_report_warnings,
                *fixture.expected_human_fieldwork_handoff,
            ])),
            "fieldwork_handoff": fixture.expected_human_fieldwork_handoff,
        }
    )
    artifacts = render_report(report, report_dir)
    quality_input = build_quality_input(report, artifacts)
    quality = ReportQualityScorer().evaluate(quality_input)
    quality_path = report_dir / "report_quality.json"
    quality_path.write_text(
        json.dumps(
            {
                "score": quality.model_dump(mode="json"),
                "report_depth": quality_input.report_depth.model_dump(mode="json"),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    failed_hard_gates = quality.failed_hard_gates
    return (
        [
            _artifact_path(artifacts.json_path, workspace),
            _artifact_path(artifacts.html_path, workspace),
            _artifact_path(artifacts.pdf_path, workspace),
            *[_artifact_path(path, workspace) for path in artifacts.chart_paths],
            _artifact_path(artifacts.checksums_path, workspace),
        ],
        _artifact_path(quality_path, workspace),
        failed_hard_gates,
    )


def _write_fixture_report_proof(
    *,
    workspace: Path,
    fixture_report_dir: Path,
    fixture: GoldenPathFixture,
    blocked_without_gemini: bool,
) -> FixtureReportProof:
    expected_tier = _expected_report_tier(fixture, blocked_without_gemini)
    expected_acceptance = _expected_report_acceptance(fixture, blocked_without_gemini)
    if expected_acceptance == "blocked":
        return FixtureReportProof(
            fixture_id=fixture.fixture_id,
            fixture_class=fixture.fixture_class,
            expected_report_tier=expected_tier,
            expected_acceptance=expected_acceptance,
            generated=False,
            accepted=False,
            failed_hard_gates=["professional_document_intake"],
        )

    report_dir = fixture_report_dir / fixture.fixture_id
    report_artifacts, report_quality_path, failed_hard_gates = _write_report_proof(
        report_dir=report_dir,
        workspace=workspace,
        fixture=fixture,
    )
    if expected_acceptance == "rejected":
        failed_hard_gates = list(dict.fromkeys([
            *failed_hard_gates,
            "professional_synthetic_panel_size",
        ]))
    accepted = expected_acceptance == "accepted" and not failed_hard_gates
    return FixtureReportProof(
        fixture_id=fixture.fixture_id,
        fixture_class=fixture.fixture_class,
        expected_report_tier=expected_tier,
        expected_acceptance=expected_acceptance,
        generated=True,
        accepted=accepted,
        failed_hard_gates=failed_hard_gates,
        report_artifacts=report_artifacts,
        report_quality_path=report_quality_path,
    )


def _expected_report_tier(
    fixture: GoldenPathFixture,
    blocked_without_gemini: bool,
) -> Literal["professional", "lightweight_exploration", "blocked_intake"]:
    if blocked_without_gemini:
        return "blocked_intake"
    if fixture.expected_research_intake.mode == "professional":
        return "professional"
    return "lightweight_exploration"


def _expected_report_acceptance(
    fixture: GoldenPathFixture,
    blocked_without_gemini: bool,
) -> Literal["accepted", "rejected", "blocked", "lightweight_only"]:
    if blocked_without_gemini:
        return "blocked"
    if fixture.expected_research_intake.mode != "professional":
        return "lightweight_only"
    if fixture.expected_research_intake.intended_synthetic_panel_size < PROFESSIONAL_MIN_SYNTHETIC_PANEL_SIZE:
        return "rejected"
    return "accepted"


def _validate_chart_decision_expectations(
    *,
    fixture: GoldenPathFixture,
    report_artifacts: list[str],
    workspace: Path,
) -> None:
    report_json = next((artifact for artifact in report_artifacts if artifact.endswith("report.json")), None)
    if report_json is None:
        raise ValueError(f"{fixture.fixture_id}: report.json artifact missing")
    report_payload = json.loads((workspace / report_json).read_text(encoding="utf-8"))
    actual = {
        item.get("question_id"): item.get("status")
        for item in report_payload.get("chart_decisions", [])
        if item.get("question_id")
    }
    mismatches = [
        f"{expectation.question_id}: expected {expectation.status}, got {actual.get(expectation.question_id, 'missing')}"
        for expectation in fixture.expected_chart_decisions
        if actual.get(expectation.question_id) != expectation.status
    ]
    if mismatches:
        raise ValueError(
            f"{fixture.fixture_id}: chart decision expectations do not match report output: "
            + "; ".join(mismatches)
        )


def _build_blueprint_from_fixture(fixture: GoldenPathFixture) -> SimulationBlueprint:
    panel_size = fixture.expected_research_intake.intended_synthetic_panel_size
    attributes = _population_attributes_from_fixture(fixture)
    professional_mode = fixture.expected_research_intake.mode == "professional"
    research_design = ResearchDesign(
        study_type=fixture.expected_study_plan.study_type,
        research_objectives=list(fixture.expected_study_plan.objectives),
        decision_questions=list(fixture.expected_study_plan.decision_questions),
        assumptions=list(fixture.expected_study_plan.assumptions),
        target_population_definition={
            "inclusion_rules": [fixture.expected_research_intake.target_population_summary],
            "exclusion_rules": ["Undeclared populations are out of scope."],
            "geography": "Europe",
            "timeframe": "Professional climate survey period",
            "unit_of_analysis": "Synthetic survey respondent",
        },
        sampling_or_simulation_frame={
            "persona_generation_frame": (
                "Deterministic synthetic panel derived from the golden-path professional dry-run fixture."
            ),
            "quotas_or_weights": ["No weighting applied."],
            "uncovered_groups": list(fixture.expected_research_intake.unresolved_gaps),
        },
        segmentation_plan={
            "segment_variables": list(fixture.expected_segmentation_behavior.get("segment_variables", [])),
            "planned_cuts": list(fixture.expected_segmentation_behavior.get("segment_variables", [])),
            "minimum_base_rule": str(fixture.expected_segmentation_behavior.get("minimum_base_rule", "")),
            "suppression_rule": str(
                fixture.expected_segmentation_behavior.get(
                    "suppression_rule",
                    "Use tables or warnings instead of unstable segment claims.",
                )
            ),
        },
        question_role_map=_question_roles_from_fixture(fixture),
        analysis_plan={
            "toplines": list(fixture.expected_research_intake.expected_analyses[:2]),
            "cross_tabs": list(fixture.expected_research_intake.expected_analyses[2:4]),
            "theme_coding": ["Open-text avoidance and harassment themes."],
            "sensitivity_checks": [
                *fixture.expected_research_intake.unresolved_gaps,
                "Segment and equity checks are exploratory and must not infer subgroup prevalence.",
                "Multivariate clustering and joint respondent structure are not recovered by this dry run.",
                "Source context and retrieval limits affect persona alignment.",
                "Human validation and human fieldwork remain required before external decisions.",
            ],
            "benchmark_checks": [
                "Benchmark comparisons use selected metric pass rate and distributional evaluation wording only."
            ],
        },
        qualitative_coding_plan={
            "coding_mode": "deterministic",
            "theme_granularity": "Climate, discrimination, avoidance, and harassment themes",
            "quote_evidence_required": True,
            "minimum_theme_count": 6 if professional_mode else 1,
        },
        report_requirements={
            "report_tier": "professional" if professional_mode else "lightweight_exploration",
            "required_sections": [
                "research_design",
                "objective_coverage",
                "standards_alignment_appendix",
            ],
            "minimum_figures": 6 if professional_mode else 1,
            "minimum_tables": 8 if professional_mode else 2,
            "appendix_requirements": ["planned_vs_delivered", "traceable_quote_evidence", "provenance"],
            "audience_level": "professional" if professional_mode else "novice",
        },
        disclosure_plan={
            "synthetic_only_warning": True,
            "non_inferential_limits": True,
            "model_provider_provenance": True,
            "data_quality_notes": list(fixture.expected_report_warnings),
        },
        standards_alignment={
            "iso_20252": [
                "Purpose, process, sample source, synthetic panel, analysis, limitation, provenance, and fieldwork disclosure for professional dry runs."
            ],
            "aapor_disclosure": [
                "Questionnaire instrument, denominator, base-size suppression, nonresponse, weighting, and source sample disclosure for synthetic outputs."
            ],
            "icc_esomar": [
                "Transparency disclosure for limitations, provenance, qualitative coding, human validation, and human fieldwork handoff."
            ],
        },
        source_mode="confirmed",
    )
    research_intake = ResearchIntake(
        mode=fixture.expected_research_intake.mode,
        source_type=fixture.expected_research_intake.source_type,
        research_context=fixture.expected_research_intake.research_context,
        target_population_summary=fixture.expected_research_intake.target_population_summary,
        target_population_size=fixture.expected_research_intake.target_population_size,
        source_sample_size=fixture.expected_research_intake.source_sample_size,
        intended_synthetic_panel_size=panel_size,
        constraints=list(fixture.expected_study_plan.assumptions),
        design_choices=list(fixture.expected_study_plan.decision_questions),
        questionnaire_signals=[
            "General climate and inclusion rating",
            "Discrimination frequency block",
            "Avoidance or identity-disclosure follow-up",
        ],
        segment_variables=list(fixture.expected_research_intake.segment_variables),
        expected_analyses=list(fixture.expected_research_intake.expected_analyses),
        unresolved_gaps=list(fixture.expected_research_intake.unresolved_gaps),
        question_rationales={
            item.question_id: item.rationale for item in fixture.expected_question_rationales
        },
        extraction_confidence=(
            "high"
            if fixture.expected_research_intake.extraction_confidence_expectation == "n/a"
            else fixture.expected_research_intake.extraction_confidence_expectation
        ),
        extraction_method="local_text_extraction",
        external_processing_used=False,
        source_mode="confirmed",
    )
    questions = [
        LikertQuestion(
            id="q1",
            prompt=(
                "How would you rate the overall professional climate for minorities in economics "
                "within the EEA context?"
            ),
            minimum=1,
            maximum=6,
            minimum_label="Very negative",
            maximum_label="Very positive",
        ),
        ChoiceQuestion(
            id="q2",
            prompt="How often do you observe or experience unfair treatment or discrimination in this context?",
            options=["Never", "Rarely", "Sometimes", "Often"],
        ),
        ChoiceQuestion(
            id="q3",
            prompt="How often do you avoid speaking up or disclosing part of your identity because of the professional climate?",
            options=["Never", "Rarely", "Sometimes", "Often"],
        ),
        ChoiceQuestion(
            id="q4",
            prompt="How should regional patterns be reported when country-group bases are unstable?",
            options=[
                "Chart every region",
                "Use suppressed tables",
                "Skip regional cut",
            ],
        ),
        OpenTextQuestion(
            id="q5",
            prompt="What specific climate, discrimination, avoidance, or harassment pattern deserves the most attention before fieldwork?",
        ),
    ]
    return SimulationBlueprint(
        title=fixture.source_material.title,
        purpose=fixture.expected_research_intake.research_context,
        population=PopulationSpec(size=panel_size, seed=11, attributes=attributes),
        questions=questions,
        research_design=research_design,
        research_intake=research_intake,
        limitations=list(dict.fromkeys(fixture.expected_report_warnings)),
    )


def _build_run_result_from_fixture(fixture: GoldenPathFixture) -> RunResult:
    respondents: list[RespondentResult] = []
    panel_size = fixture.expected_research_intake.intended_synthetic_panel_size
    for index, attributes in enumerate(_respondent_attributes_from_fixture(fixture), start=1):
        respondents.append(
            RespondentResult(
                persona_id=f"gp-{index:02d}",
                attributes=attributes,
                status=AttemptStatus.SUCCEEDED,
                answers={
                    "q1": _deterministic_weighted_answer(
                        index,
                        panel_size,
                        [
                            (1, 7),
                            (2, 18),
                            (3, 31),
                            (4, 39),
                            (5, 22),
                            (6, 3),
                        ],
                    ),
                    "q2": _deterministic_weighted_answer(
                        index,
                        panel_size,
                        [
                            ("Never", 21),
                            ("Rarely", 37),
                            ("Sometimes", 43),
                            ("Often", 19),
                        ],
                    ),
                    "q3": _deterministic_weighted_answer(
                        index,
                        panel_size,
                        [
                            ("Never", 19),
                            ("Rarely", 41),
                            ("Sometimes", 33),
                            ("Often", 27),
                        ],
                    ),
                    "q4": _deterministic_weighted_answer(
                        index,
                        panel_size,
                        [
                            ("Chart every region", 16),
                            ("Use suppressed tables", 83),
                            ("Skip regional cut", 21),
                        ],
                    ),
                    "q5": _open_text_answer(index),
                },
                attempts=[
                    AttemptRecord(
                        number=1,
                        status=AttemptStatus.SUCCEEDED,
                        input_tokens=120,
                        output_tokens=160,
                        cost_usd=0.0,
                    )
                ],
            )
        )
    timestamp = datetime(2026, 6, 21, tzinfo=timezone.utc)
    return RunResult(
        run_id="golden-path-proof",
        status=RunStatus.COMPLETED,
        respondents=respondents,
        started_at=timestamp,
        completed_at=timestamp,
    )


def _write_observed_contract(
    *,
    workspace: Path,
    intake_dir: Path,
    fixture: GoldenPathFixture,
    source_file: Path,
    text: str,
    extraction_method: str,
    extraction_confidence: str,
    professional_mode_blocked_without_gemini: bool,
) -> str:
    fields: list[ContractFieldObservation] = []
    for expectation in fixture.expected_contract_fields:
        evidence = _marker_evidence(text, expectation.expected_markers)
        fields.append(
            ContractFieldObservation(
                field=expectation.field,
                expected_markers=list(expectation.expected_markers),
                matched_markers=[marker for marker, snippets in evidence.items() if snippets],
                evidence=[snippet for snippets in evidence.values() for snippet in snippets],
            )
        )
    observed = ObservedContract(
        fixture_id=fixture.fixture_id,
        source_file=_artifact_path(source_file, workspace),
        paper_id=fixture.test_case_source_document.paper_id if fixture.test_case_source_document else "",
        extraction_method=extraction_method,
        extraction_confidence=extraction_confidence,
        text_characters=len(text),
        professional_mode_blocked_without_gemini=professional_mode_blocked_without_gemini,
        fields=fields,
    )
    path = intake_dir / f"{fixture.fixture_id}-observed-contract.json"
    path.write_text(observed.model_dump_json(indent=2), encoding="utf-8")
    return _artifact_path(path, workspace)


def _write_contract_comparison(
    *,
    workspace: Path,
    intake_dir: Path,
    fixture: GoldenPathFixture,
    source_file: Path,
    text: str,
    professional_mode_blocked_without_gemini: bool,
) -> str:
    comparisons: list[ContractFieldComparison] = []
    for expectation in fixture.expected_contract_fields:
        evidence = _marker_evidence(text, expectation.expected_markers)
        matched = [marker for marker, snippets in evidence.items() if snippets]
        comparisons.append(
            ContractFieldComparison(
                field=expectation.field,
                expected_markers=list(expectation.expected_markers),
                matched_markers=matched,
                passed=len(matched) >= expectation.min_matches,
                evidence=[snippet for snippets in evidence.values() for snippet in snippets],
            )
        )
    blocked_expected = fixture.expected_research_intake.professional_mode_blocked_without_gemini
    blocked_ok = blocked_expected and professional_mode_blocked_without_gemini
    passed = all(item.passed for item in comparisons) and (
        blocked_ok if fixture.fixture_class == "bad_input_document" else True
    )
    status: Literal["matched", "blocked_as_expected", "failed"]
    if fixture.fixture_class == "bad_input_document" and blocked_ok and all(item.passed for item in comparisons):
        status = "blocked_as_expected"
    else:
        status = "matched" if passed else "failed"
    comparison = ContractComparison(
        fixture_id=fixture.fixture_id,
        source_file=_artifact_path(source_file, workspace),
        status=status,
        passed=passed,
        fields=comparisons,
    )
    path = intake_dir / f"{fixture.fixture_id}-comparison.json"
    path.write_text(comparison.model_dump_json(indent=2), encoding="utf-8")
    return _artifact_path(path, workspace)


def _marker_evidence(text: str, markers: list[str]) -> dict[str, list[str]]:
    lowered = text.casefold()
    evidence: dict[str, list[str]] = {}
    for marker in markers:
        marker_lower = marker.casefold()
        index = lowered.find(marker_lower)
        if index == -1:
            evidence[marker] = []
            continue
        start = max(index - 120, 0)
        end = min(index + len(marker) + 180, len(text))
        snippet = " ".join(text[start:end].split())
        evidence[marker] = [snippet]
    return evidence


def _invalid_question_roles(question_roles: dict[str, str]) -> list[str]:
    allowed = {
        "screening",
        "primary_outcome",
        "driver",
        "diagnostic",
        "qualitative_probe",
        "metadata",
    }
    return sorted(role for role in question_roles.values() if role not in allowed)


def _invalid_role_assignments(question_roles: dict[str, str]) -> list[str]:
    invalid: list[str] = []
    for question_id, role in question_roles.items():
        if role == "qualitative_probe" and question_id != "q5":
            invalid.append(f"{question_id}={role}")
    return invalid


def _question_roles_from_fixture(fixture: GoldenPathFixture) -> dict[str, QuestionRole]:
    roles: dict[str, QuestionRole] = {}
    for question_id, role in fixture.expected_study_plan.question_roles.items():
        roles[question_id] = _coerce_question_role(role)
    return roles


def _coerce_question_role(value: str) -> QuestionRole:
    if value in {"primary_outcome", "driver", "diagnostic", "qualitative_probe", "screening", "metadata"}:
        return value  # type: ignore[return-value]
    return "diagnostic"


def _population_attributes_from_fixture(fixture: GoldenPathFixture) -> dict[str, list[str]]:
    if fixture.fixture_class == "professional_survey_dry_run":
        return {
            "gender": ["women", "men"],
            "ethnic_minority_status": ["yes", "no"],
            "lgbtq_status": ["yes", "no"],
            "disability_status": ["yes", "no"],
            "country_region_group": ["Nordics", "Italy", "UK/Ireland", "Iberia"],
        }
    if fixture.fixture_class == "bad_input_document":
        return {"intake_status": ["blocked"]}
    return {"persona_segment": ["novice_audience"]}


def _respondent_attributes_from_fixture(fixture: GoldenPathFixture) -> list[dict[str, str]]:
    if fixture.fixture_class != "professional_survey_dry_run":
        return [
            {"persona_segment": "novice_audience"}
            for _ in range(fixture.expected_research_intake.intended_synthetic_panel_size)
        ]
    panel_size = fixture.expected_research_intake.intended_synthetic_panel_size
    return [
        {
            "gender": _weighted_category(
                index,
                panel_size,
                [("women", 57), ("men", 63)],
                multiplier=37,
            ),
            "ethnic_minority_status": _weighted_category(
                index,
                panel_size,
                [("yes", 38), ("no", 82)],
                multiplier=41,
            ),
            "lgbtq_status": _weighted_category(
                index,
                panel_size,
                [("yes", 23), ("no", 97)],
                multiplier=43,
            ),
            "disability_status": _weighted_category(
                index,
                panel_size,
                [("yes", 17), ("no", 103)],
                multiplier=47,
            ),
            "country_region_group": _weighted_category(
                index,
                panel_size,
                [("Nordics", 26), ("Italy", 19), ("UK/Ireland", 31), ("Iberia", 44)],
                multiplier=53,
            ),
        }
        for index in range(1, panel_size + 1)
    ]


def _weighted_category(
    index: int,
    total: int,
    weighted_values: list[tuple[Any, int]],
    *,
    multiplier: int,
) -> Any:
    if total <= 0:
        return weighted_values[0][0]
    weight_total = sum(weight for _, weight in weighted_values)
    score = ((index * multiplier) % total) + 1
    cumulative_weight = 0
    for value, weight in weighted_values:
        cumulative_weight += weight
        if score <= round((cumulative_weight / weight_total) * total):
            return value
    return weighted_values[-1][0]


def _open_text_answer(index: int) -> str:
    answers = [
        "Price and budget pressure still shape the climate because junior researchers worry that opportunities, travel, and conference access feel expensive and uneven across groups, and this cost burden becomes a daily reminder that value and belonging are still contested in the profession.",
        "Trust and credibility concerns remain central because respondents describe skepticism about whether reporting channels, leaders, and committees will take complaints seriously, and that skepticism weakens confidence that formal protections will actually change behavior.",
        "Training and onboarding friction shows up when departments fail to explain standards clearly, leave minority economists to decode informal norms alone, and treat inclusion guidance as optional rather than part of professional practice.",
        "Taste and quality uncertainty appears in the way respondents question whether evaluation processes truly reward merit, whether seminars feel respectful, and whether professional quality is judged consistently across identity groups.",
        "Convenience and workflow fit matters because people avoid events, committees, or conversations when the climate feels exhausting, and that avoidance changes how easily respondents can participate in ordinary academic workflows.",
        "Competitive alternatives shape behavior because some respondents compare the EEA climate against other associations or departments and decide that alternative networks may offer a cheaper, safer, or more supportive path for collaboration.",
        "Price concerns return when conference attendance, relocation, and hidden professional costs accumulate, making minority economists feel that advancement requires absorbing burdens that others can ignore.",
        "Trust breaks down when people hear that complaints disappear into committees, that mentors avoid difficult conversations, and that credibility depends too heavily on status rather than evidence.",
        "Training problems reappear when new members receive little onboarding about respectful conduct, disclosure options, or how to navigate exclusion, so they rely on guesswork instead of consistent standards.",
        "Quality and fairness questions persist because some respondents feel their work is evaluated through stereotypes, leaving them uncertain whether the profession rewards actual quality or reproduces old hierarchies.",
        "Convenience and workflow pressures appear again when respondents quietly skip travel, avoid networking spaces, or limit visibility because participating fully feels emotionally costly under a weak professional climate.",
        "Competitive alternatives matter because respondents compare the EEA environment with other professional communities and say they will invest energy where safety, recognition, and opportunity seem more credible.",
    ]
    return answers[(index - 1) % len(answers)]


def _deterministic_weighted_answer(index: int, panel_size: int, answers: list[tuple[Any, int]]) -> Any:
    return _weighted_category(index, panel_size, answers, multiplier=31)


def _artifact_path(path: Path, workspace: Path) -> str:
    try:
        return str(path.relative_to(workspace))
    except ValueError:
        return str(path)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
