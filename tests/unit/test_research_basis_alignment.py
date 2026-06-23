from __future__ import annotations

import hashlib
import json
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from synthetix.reporting.models import ReportModel
from synthetix.reporting.quality import (
    CategoryScores,
    ReportQualityInput,
    ReportQualityScorer,
    build_quality_input,
)
from synthetix.reporting.renderer import ReportArtifacts
from synthetix.research.basis_alignment import ResearchBasisAlignment


def test_professional_report_quality_rejects_missing_research_basis_alignment_texts() -> None:
    quality_input = ReportQualityInput(
        category_scores=CategoryScores(
            analytical_correctness=90,
            segmentation_and_bases=90,
            evidence_traceability=90,
            methodology_and_limitations=90,
            visual_readability_checks=90,
            reproducibility_and_artifact_integrity=90,
        ),
        research_design_tier="professional",
        assumptions=[],
        target_population_summary="",
        sampling_frame_summary="",
        segmentation_plan_summary="",
        analysis_plan_summary="",
        qualitative_coding_summary="",
        standards_alignment_texts=[],
        benchmark_wording_texts=["selected metric pass rate"],
        research_basis_alignment_texts=[],
    )

    result = ReportQualityScorer().evaluate(quality_input)

    assert result.accepted is False
    assert "research_basis_alignment_complete" in result.failed_hard_gates


def test_build_quality_input_populates_research_basis_alignment_texts(tmp_path: Path) -> None:
    report = ReportModel.example()
    json_path = tmp_path / "report.json"
    html_path = tmp_path / "report.html"
    pdf_path = tmp_path / "report.pdf"
    checksums_path = tmp_path / "checksums.json"

    json_path.write_text("{}", encoding="utf-8")
    html_path.write_text(
        "<html><body><p>Synthetic scenario evidence only.</p></body></html>",
        encoding="utf-8",
    )
    pdf = canvas.Canvas(str(pdf_path), pagesize=A4, pageCompression=1, invariant=1)
    pdf.drawString(48, A4[1] - 48, "Synthetic scenario evidence only.")
    pdf.drawString(48, A4[1] - 64, "Human validation remains necessary.")
    pdf.save()
    checksums_path.write_text(
        json.dumps(
            {
                "report.json": hashlib.sha256(json_path.read_bytes()).hexdigest(),
                "report.html": hashlib.sha256(html_path.read_bytes()).hexdigest(),
                "report.pdf": hashlib.sha256(pdf_path.read_bytes()).hexdigest(),
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    quality_input = build_quality_input(
        report,
        ReportArtifacts(
            json_path=json_path,
            html_path=html_path,
            pdf_path=pdf_path,
            checksums_path=checksums_path,
            chart_paths=[],
        ),
    )

    alignment = ResearchBasisAlignment.from_texts(quality_input.research_basis_alignment_texts)

    assert quality_input.research_basis_alignment_texts
    assert alignment.complete is True
    assert {
        "distributional_evaluation",
        "segment_equity_checks",
        "multivariate_clustering_limitation",
        "context_retrieval_limits",
        "human_validation_handoff",
    }.issubset(set(alignment.present_markers))
