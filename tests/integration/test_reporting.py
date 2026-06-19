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
    ObjectiveCoverage,
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
                        label="Price sensitivity and value concern",
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
        research_design={
            "study_type": "concept_test",
            "research_objectives": [
                "Measure concept fit by segment.",
                "Identify primary adoption barriers.",
            ],
            "decision_questions": [
                "Should the concept move forward?",
                "Which objections need mitigation first?",
            ],
            "assumptions": [
                "Synthetic responses are exploratory only.",
                "Small synthetic populations can overstate consensus.",
            ],
            "target_population_definition": {
                "inclusion_rules": ["Adults in the target workflow."],
                "exclusion_rules": ["No minors."],
                "unit_of_analysis": "Decision-maker",
                "geography": "United States",
                "timeframe": "Current operating context",
            },
            "sampling_or_simulation_frame": {
                "persona_generation_frame": "Declared region and role attribute grid.",
                "quotas_or_weights": ["No weighting applied."],
                "uncovered_groups": ["Undeclared occupations."],
            },
            "segmentation_plan": {
                "segment_variables": ["region", "role"],
                "planned_cuts": ["region", "role"],
                "minimum_base_rule": "Suppress slices below n=2.",
                "suppression_rule": "Mark suppressed slices explicitly.",
            },
            "question_role_map": {"q1": "primary_outcome", "q2": "qualitative_probe"},
            "analysis_plan": {
                "toplines": ["Concept fit topline."],
                "cross_tabs": ["Concept fit by region and role."],
                "likert_summaries": [],
                "rankings": [],
                "theme_coding": ["Barrier themes from q2."],
                "sensitivity_checks": ["Review failed attempts."],
                "benchmark_checks": [
                    "Any benchmark comparison is described as selected metric pass rate only."
                ],
            },
            "qualitative_coding_plan": {
                "coding_mode": "deterministic",
                "theme_granularity": "Barrier themes",
                "quote_evidence_required": True,
                "minimum_theme_count": 1,
            },
            "report_requirements": {
                "report_tier": "professional",
                "required_sections": [
                    "research_design",
                    "objective_coverage",
                    "standards_alignment_appendix",
                ],
                "minimum_figures": 1,
                "minimum_tables": 2,
                "appendix_requirements": ["Planned-vs-delivered appendix"],
                "audience_level": "professional",
            },
            "disclosure_plan": {
                "synthetic_only_warning": True,
                "non_inferential_limits": True,
                "model_provider_provenance": True,
                "data_quality_notes": ["Synthetic scenario evidence only."],
            },
            "standards_alignment": {
                "iso_20252": ["Purpose and process disclosure."],
                "aapor_disclosure": ["Questionnaire and denominator disclosure."],
                "icc_esomar": ["Transparency disclosure."],
            },
        },
        objective_coverage=[
            ObjectiveCoverage(
                objective="Measure concept fit by segment.",
                decision_question="Should the concept move forward?",
                covered_question_ids=["q1"],
                status="covered",
                notes="Covered by primary outcome toplines and segment cuts.",
            ),
            ObjectiveCoverage(
                objective="Identify primary adoption barriers.",
                decision_question="Which objections need mitigation first?",
                covered_question_ids=["q2"],
                status="covered",
                notes="Covered by qualitative themes and evidence.",
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
    assert "Research design" in html
    assert "Question distributions" in html
    assert "Segment comparisons" in html
    assert "Qualitative themes and evidence" in html
    assert "Failures and sensitivity" in html
    assert "Methodology" in html
    assert "Objective coverage" in html
    assert "Provenance" in html
    assert "Limitations" in html
    assert "Standards-aligned disclosure appendix" in html
    assert "Technical appendix" in html
    assert "Figure 1." in html
    assert "Table 1." in html
    assert "Table 2." in html
    assert "n = 4" in html
    assert "Do not infer prevalence, causality, or statistical significance" in html

    text = "\n".join(page.extract_text() or "" for page in PdfReader(artifacts.pdf_path).pages)
    assert "Board readout: synthetic scenario exploration" in text
    assert "Executive findings" in text
    assert "Research design" in text
    assert "Question distributions" in text
    assert "Objective coverage" in text
    assert "Technical appendix" in text
    assert "Non-inferential use warning" in text

    second_run = render_report(report, tmp_path / "repeat")
    first_chart_bytes = [path.read_bytes() for path in artifacts.chart_paths]
    second_chart_bytes = [path.read_bytes() for path in second_run.chart_paths]
    assert first_chart_bytes == second_chart_bytes

    checksums = json.loads(artifacts.checksums_path.read_text(encoding="utf-8"))
    assert "report.pdf" in checksums
    assert "report.html" in checksums


def test_report_pipeline_uses_theme_tables_not_raw_open_text_charts(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _install_fake_weasyprint(monkeypatch)
    report = _rich_report().model_copy(
        update={
            "questions": [
                QuestionReport(
                    question_id="offset_reaction",
                    prompt="What is your immediate emotional reaction when an online checkout screen prompts you to donate to offset your carbon footprint?",
                    question_type="open_text",
                    response_count=5,
                    distribution=Distribution(
                        labels=[
                            "I feel suspicious because it shifts responsibility to consumers.",
                            "I feel skeptical and cautious about whether the offset is real.",
                        ],
                        values=[3, 2],
                    ),
                    quotes=[
                        "I feel suspicious because it shifts responsibility to consumers.",
                        "I feel skeptical and cautious about whether the offset is real.",
                    ],
                    denominators=DenominatorSummary(
                        total_personas=5,
                        succeeded_personas=5,
                        answered_responses=5,
                        valid_responses=5,
                    ),
                    themes=[
                        ThemeEvidence(
                            theme_id="offset_reaction:theme:1",
                            label="Suspicion about shifting responsibility",
                            count=3,
                            supporting_quote_ids=["offset:p1", "offset:p2", "offset:p3"],
                        ),
                        ThemeEvidence(
                            theme_id="offset_reaction:theme:2",
                            label="Skepticism about impact credibility",
                            count=2,
                            supporting_quote_ids=["offset:p4", "offset:p5"],
                        ),
                    ],
                )
            ]
        }
    )

    artifacts = render_report(report, tmp_path)
    html = artifacts.html_path.read_text(encoding="utf-8")

    assert len(artifacts.chart_paths) == 1
    assert "Suspicion about shifting responsibility" in html
    assert "Skepticism about impact credibility" in html
    assert "I feel suspicious because it shifts responsibility to consumers." in html
    assert "Traceable synthetic evidence" in html


def test_report_pipeline_uses_semantic_theme_labels_for_qualitative_summary(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _install_fake_weasyprint(monkeypatch)
    report = _rich_report()

    artifacts = render_report(report, tmp_path)
    html = artifacts.html_path.read_text(encoding="utf-8")

    assert "Price sensitivity and value concern" in html
    assert "Price would require a very obvious payback story." in html
    assert "most repeated exact-response wording" not in html.casefold()


def test_report_pipeline_wraps_long_chart_labels_for_choice_questions(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _install_fake_weasyprint(monkeypatch)
    report = _rich_report().model_copy(
        update={
            "questions": [
                QuestionReport(
                    question_id="premium_likelihood",
                    prompt="How likely are you to pay an additional $4.50 premium per delivery if a brand displays a carbon-neutral shipping badge at checkout?",
                    question_type="choice",
                    response_count=5,
                    distribution=Distribution(
                        labels=[
                            "Very likely",
                            "Somewhat likely",
                            "Not sure yet",
                            "Somewhat unlikely",
                            "Very unlikely",
                        ],
                        values=[1, 1, 1, 1, 1],
                    ),
                    denominators=DenominatorSummary(
                        total_personas=5,
                        succeeded_personas=5,
                        answered_responses=5,
                        valid_responses=5,
                    ),
                )
            ]
        }
    )

    artifacts = render_report(report, tmp_path)

    assert len(artifacts.chart_paths) == 1
    assert artifacts.chart_paths[0].exists()


def test_renderer_sanitizes_narrative_chart_labels() -> None:
    question = {
        "question_type": "open_text",
        "question_id": "offset_reaction",
        "labels": [
            "I feel suspicious because the company is shifting responsibility onto consumers.",
            "I feel skeptical because I do not trust the carbon-offset claims.",
        ],
    }

    assert renderer._chart_labels(question) == ["Response 1", "Response 2"]


def test_renderer_uses_compact_chart_title() -> None:
    question = {
        "question_type": "choice",
        "question_id": "premium_likelihood",
        "prompt": "How likely are you to pay an additional $4.50 premium per delivery if a brand displays a certified carbon-neutral badge at checkout?",
    }

    assert renderer._chart_title(question) == "Response distribution"


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
