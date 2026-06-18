import html
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest
from pypdf import PdfReader
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from synthetix.reporting.models import (
    DenominatorSummary,
    Distribution,
    ExecutiveFinding,
    FailureSummary,
    MethodologySummary,
    ProvenanceSummary,
    QuestionReport,
    ReportModel,
    SegmentComposition,
    SegmentCompositionEntry,
    SegmentCut,
    ThemeEvidence,
)
from synthetix.reporting import renderer
from synthetix.reporting.renderer import render_report


def _rich_report() -> ReportModel:
    return ReportModel(
        run_id="board-readout",
        title="Board readout: synthetic scenario exploration",
        purpose=(
            "Assess concept fit, adoption barriers, and segment-specific objections "
            "across a small synthetic population."
        ),
        generated_at=datetime(2026, 1, 1, 8, 30, tzinfo=timezone.utc),
        executive_summary=(
            "Executive view: concept fit is strongest among urban operators, while "
            "rural operators surface price and onboarding friction."
        ),
        population={
            "size": 4,
            "seed": 17,
            "attributes": {"region": ["urban", "rural"], "role": ["operator", "manager"]},
        },
        questions=[
            QuestionReport(
                question_id="q1",
                prompt="Would this concept fit your workflow?",
                question_type="choice",
                response_count=4,
                distribution=Distribution(labels=["Yes", "Maybe", "No"], values=[2, 1, 1]),
                quotes=[
                    "It would slot into our workflow quickly.",
                    "The value is clear if onboarding is lightweight.",
                ],
                denominators=DenominatorSummary(
                    total_personas=4,
                    succeeded_personas=3,
                    answered_responses=4,
                    valid_responses=4,
                ),
                segment_cuts=[
                    SegmentCut(
                        attribute="region",
                        value="urban",
                        base_count=2,
                        distribution=Distribution(labels=["Yes", "Maybe", "No"], values=[2, 0, 0]),
                    ),
                    SegmentCut(
                        attribute="region",
                        value="rural",
                        base_count=2,
                        distribution=Distribution(labels=["Yes", "Maybe", "No"], values=[0, 1, 1]),
                    ),
                ],
            ),
            QuestionReport(
                question_id="q2",
                prompt="What is the primary adoption barrier?",
                question_type="open_text",
                response_count=3,
                distribution=Distribution(),
                quotes=[
                    "Price would require a very obvious payback story.",
                    "Training effort would need to stay low.",
                ],
                denominators=DenominatorSummary(
                    total_personas=4,
                    succeeded_personas=3,
                    answered_responses=3,
                    valid_responses=3,
                ),
                themes=[
                    ThemeEvidence(
                        theme_id="q2:theme:1",
                        label="Price would require a very obvious payback story.",
                        count=2,
                        supporting_quote_ids=["q2:p1", "q2:p2"],
                    )
                ],
            ),
        ],
        executive_findings=[
            ExecutiveFinding(
                finding_id="finding-1",
                title="Concept fit concentrates in urban respondents",
                summary="Urban synthetic respondents showed the clearest immediate fit.",
                question_id="q1",
            ),
            ExecutiveFinding(
                finding_id="finding-2",
                title="Adoption risk is economic before it is functional",
                summary="Negative responses referenced price pressure before missing features.",
                question_id="q2",
                evidence_quote_ids=["q2:p1", "q2:p2"],
            ),
        ],
        segment_composition=[
            SegmentComposition(
                attribute="region",
                segments=[
                    SegmentCompositionEntry(value="urban", count=2, share=0.5),
                    SegmentCompositionEntry(value="rural", count=2, share=0.5),
                ],
            ),
            SegmentComposition(
                attribute="role",
                segments=[
                    SegmentCompositionEntry(value="operator", count=2, share=0.5),
                    SegmentCompositionEntry(value="manager", count=2, share=0.5),
                ],
            ),
        ],
        sensitivity_notes=[
            "Small synthetic populations can overstate apparent consensus.",
            "Changing the seed or model may materially alter theme frequency.",
        ],
        methodology=MethodologySummary(
            approach="Synthetic persona scenario exploration with deterministic aggregation.",
            response_generation="One response per persona per question after retries.",
            quality_controls=[
                "Refusals retained in failure accounting.",
                "Question distributions reported with explicit denominators.",
            ],
        ),
        failures=FailureSummary(
            total_personas=4,
            succeeded=3,
            failed=1,
            retries=2,
            classifications={"refused": 1},
        ),
        provenance=ProvenanceSummary(
            model_id="openai/test-model",
            provider="openrouter",
            blueprint_hash="a" * 64,
            manifest_hash="b" * 64,
            protocol_version="1.0",
        ),
        token_usage=1432,
        cost_usd=0.2468,
        limitations=[
            "Synthetic personas are not sampled human respondents.",
            "Outputs are descriptive scenario evidence only.",
        ],
        manifest={"run_id": "board-readout", "seed": 17, "source_documents": ["brief.md"]},
    )


def _json_default(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError(f"Unsupported value: {value!r}")


def _install_fake_weasyprint(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeHTML:
        def __init__(self, string: str, base_url: str, url_fetcher: Any) -> None:
            self.string = string

        def write_pdf(self, target: Path, pdf_variant: str, pdf_tags: bool) -> None:
            pdf = canvas.Canvas(str(target), pagesize=A4, pageCompression=1, invariant=1)
            text = html.unescape(re.sub(r"<[^>]+>", "\n", self.string))
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            y = A4[1] - 48
            for line in lines[:120]:
                if y < 54:
                    pdf.showPage()
                    y = A4[1] - 48
                pdf.drawString(48, y, line[:100])
                y -= 12
            pdf.save()

    def _fake_url_fetcher(url: str) -> dict[str, Any]:
        return {"string": "", "mime_type": "text/plain"}

    monkeypatch.setattr(renderer, "_load_weasyprint", lambda: (FakeHTML, _fake_url_fetcher))


def test_report_pipeline_renders_executive_and_appendix_sections(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _install_fake_weasyprint(monkeypatch)
    report = _rich_report()
    artifacts = render_report(report, tmp_path)

    assert artifacts.json_path.exists()
    assert artifacts.html_path.exists()
    assert artifacts.pdf_path.exists()
    assert artifacts.checksums_path.exists()
    assert len(artifacts.chart_paths) == 1

    html = artifacts.html_path.read_text(encoding="utf-8")
    assert "Table of contents" in html
    assert "Executive findings" in html
    assert "Population composition" in html
    assert "Question distributions" in html
    assert "Segment comparisons" in html
    assert "Qualitative themes and evidence" in html
    assert "Failures and sensitivity" in html
    assert "Methodology" in html
    assert "Provenance" in html
    assert "Limitations" in html
    assert "Technical appendix" in html
    assert "Figure 1." in html
    assert "Table 1." in html
    assert "Table 2." in html
    assert "n = 4" in html
    assert "Do not infer prevalence, causality, or statistical significance" in html

    text = "\n".join(page.extract_text() or "" for page in PdfReader(artifacts.pdf_path).pages)
    assert "Board readout: synthetic scenario exploration" in text
    assert "Executive findings" in text
    assert "Question distributions" in text
    assert "Technical appendix" in text
    assert "Non-inferential use warning" in text

    second_run = render_report(report, tmp_path / "repeat")
    first_chart_bytes = [path.read_bytes() for path in artifacts.chart_paths]
    second_chart_bytes = [path.read_bytes() for path in second_run.chart_paths]
    assert first_chart_bytes == second_chart_bytes

    checksums = json.loads(artifacts.checksums_path.read_text(encoding="utf-8"))
    assert "report.pdf" in checksums
    assert "report.html" in checksums


def test_report_pipeline_fails_explicitly_without_weasyprint(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        renderer,
        "_load_weasyprint",
        lambda: (_ for _ in ()).throw(
            RuntimeError(
                "WeasyPrint is required to render report PDFs; install WeasyPrint for production output."
            )
        ),
    )

    with pytest.raises(RuntimeError, match="WeasyPrint is required to render report PDFs"):
        render_report(ReportModel.example(), tmp_path)

    assert (tmp_path / "report.json").exists()
    assert (tmp_path / "report.html").exists()
    assert not (tmp_path / "report.pdf").exists()
