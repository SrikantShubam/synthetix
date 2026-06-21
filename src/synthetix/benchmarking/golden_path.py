from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from synthetix.ingestion.documents import DocumentLimits, extract_document
from synthetix.ingestion.intake import ensure_professional_document_intake_allowed
from synthetix.reporting.models import ReportModel


FixtureClass = Literal[
    "novice_concept_test",
    "professional_survey_dry_run",
    "bad_input_document",
]


class GoldenPathSourceMaterial(BaseModel):
    format: Literal["markdown_brief", "pdf_brief", "scanned_pdf_simulation"]
    title: str
    body: str


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


class GoldenPathProofSummary(BaseModel):
    fixture_count: int
    classes_present: list[FixtureClass]
    proofs: list[FixtureProof] = Field(default_factory=list)
    report_artifacts: list[str] = Field(default_factory=list)


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
        if fixture.expected_research_intake.mode == "professional" and not fixture.expected_research_intake.segment_variables:
            findings.append(f"{fixture.fixture_id}: professional fixture missing segment_variables")
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

    proof_root = output_dir or workspace / "data/golden-path"
    source_dir = proof_root / "source-docs"
    intake_dir = proof_root / "intake-proof"
    report_dir = proof_root / "report-proof"
    source_dir.mkdir(parents=True, exist_ok=True)
    intake_dir.mkdir(parents=True, exist_ok=True)

    proofs: list[FixtureProof] = []
    for fixture in fixtures:
        source_file = _write_source_material(source_dir, fixture)
        extraction_method = "structured_brief"
        extraction_confidence = "n/a"
        blocked_without_gemini = False
        if source_file.suffix.lower() == ".pdf":
            extracted = extract_document(
                source_file,
                DocumentLimits(max_bytes=10_000_000, max_pdf_pages=10),
            )
            extraction_method = extracted.extraction_method
            extraction_confidence = extracted.extraction_confidence
            try:
                ensure_professional_document_intake_allowed(
                    extracted,
                    professional_mode=fixture.expected_research_intake.mode == "professional",
                    used_gemini=False,
                )
            except ValueError:
                blocked_without_gemini = True
        proofs.append(
            FixtureProof(
                fixture_id=fixture.fixture_id,
                fixture_class=fixture.fixture_class,
                source_file=str(source_file.relative_to(workspace)),
                source_format=fixture.source_material.format,
                extraction_method=extraction_method,
                extraction_confidence=extraction_confidence,
                professional_mode_blocked_without_gemini=blocked_without_gemini,
                expected_blocked_without_gemini=fixture.expected_research_intake.professional_mode_blocked_without_gemini,
            )
        )

    report_artifacts = _write_report_proof(report_dir, workspace)
    summary = GoldenPathProofSummary(
        fixture_count=len(fixtures),
        classes_present=sorted({fixture.fixture_class for fixture in fixtures}),
        proofs=proofs,
        report_artifacts=report_artifacts,
    )
    summary_path = intake_dir / "proof-summary.json"
    summary_path.write_text(summary.model_dump_json(indent=2), encoding="utf-8")
    return summary


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


def _write_report_proof(report_dir: Path, workspace: Path) -> list[str]:
    report_dir.mkdir(parents=True, exist_ok=True)
    report = ReportModel.example()
    json_path = report_dir / "report.json"
    html_path = report_dir / "report.html"
    pdf_path = report_dir / "report.pdf"
    json_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    html_path.write_text(
        (
            "<html><body><h1>Golden Path Proof Report</h1>"
            "<p>This deterministic artifact proves a local PDF/report path exists in the workspace.</p>"
            "</body></html>"
        ),
        encoding="utf-8",
    )
    pdf = canvas.Canvas(str(pdf_path), pagesize=A4, pageCompression=1, invariant=1)
    pdf.drawString(48, A4[1] - 48, "Golden Path Proof Report")
    pdf.drawString(48, A4[1] - 64, "This deterministic artifact proves a local PDF/report path exists in the workspace.")
    pdf.save()
    return [
        str(json_path.relative_to(workspace)),
        str(html_path.relative_to(workspace)),
        str(pdf_path.relative_to(workspace)),
    ]
