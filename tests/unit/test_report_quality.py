from __future__ import annotations

from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from synthetix.reporting.quality import (
    REQUIRED_REPORT_SECTIONS,
    ArtifactChecksum,
    AttritionEvidence,
    CategoryScores,
    KeyFindingEvidence,
    PercentageEvidence,
    ReportDepthEvidence,
    ReportQualityInput,
    ReportQualityScorer,
    build_quality_input,
    load_benchmark_registry,
)
from synthetix.reporting.models import AnalyticsChart, QuoteEvidence, ReportAnalytics, ReportModel
from synthetix.reporting.models import Distribution, SegmentCut, ThemeEvidence
from synthetix.reporting.renderer import ReportArtifacts


def valid_quality_input() -> ReportQualityInput:
    return ReportQualityInput(
        category_scores=CategoryScores(
            analytical_correctness=90,
            segmentation_and_bases=90,
            evidence_traceability=90,
            methodology_and_limitations=90,
            visual_readability_checks=80,
            reproducibility_and_artifact_integrity=100,
        ),
        chart_labels=["yes", "no", "unsure"],
        percentages=[
            PercentageEvidence(
                label="Preference share",
                value=62.5,
                numerator=5,
                denominator=8,
            )
        ],
        key_findings=[
            KeyFindingEvidence(
                finding_id="finding-1",
                text="Most respondents preferred the simplified flow.",
                question_id="q1",
                response_evidence=["resp-17", "resp-21"],
            )
        ],
        configured_population_dimensions=["region", "age_group"],
        composition_dimensions=["region"],
        suppression_notes={"age_group": "Suppressed because the displayed slice is too small."},
        sections_present=list(REQUIRED_REPORT_SECTIONS),
        artifact_checksums=[
            ArtifactChecksum(
                path="report.json",
                expected_sha256="a" * 64,
                actual_sha256="a" * 64,
            ),
            ArtifactChecksum(
                path="report.pdf",
                expected_sha256="b" * 64,
                actual_sha256="b" * 64,
            ),
        ],
        non_inferential_warning_present=True,
        claim_texts=[
            "This report describes synthetic scenario evidence within the declared protocol."
        ],
        attrition=AttritionEvidence(
            labels=["succeeded", "failed", "refused"],
            counts={"succeeded": 8, "failed": 1, "refused": 1},
        ),
        report_depth=ReportDepthEvidence(
            pdf_pages=18,
            word_count=4200,
            chart_count=8,
            table_count=10,
            question_count=6,
            segment_cut_count=12,
            qualitative_theme_count=9,
            traceable_quote_count=24,
        ),
        research_design_tier="professional",
        objective_coverage=[
            {
                "objective": "Measure preference.",
                "decision_question": "Should the concept proceed?",
                "covered_question_ids": ["q1", "q2"],
                "status": "covered",
                "notes": "Covered by primary and diagnostic questions.",
            }
        ],
        research_objectives=["Measure preference."],
        decision_questions=["Should the concept proceed?"],
        assumptions=["Synthetic-only evidence."],
        target_population_summary="Declared personas; synthetic respondent",
        sampling_frame_summary="Declared attribute grid",
        segmentation_plan_summary="region; age_group; suppress small cells",
        analysis_plan_summary="topline; crosstab; theme coding",
        qualitative_coding_summary="deterministic; barrier themes; minimum themes=2",
        sample_source_summary="Sample source: declared personas drawn from the target population.",
        synthetic_panel_summary="Synthetic panel size 120 built from the declared attribute grid.",
        synthetic_panel_size=120,
        questionnaire_instrument_summary="Questionnaire instrument uses a structured concept-fit prompt and barrier probe.",
        nonresponse_weighting_summary="No weighting applied; refusals remain in attrition accounting.",
        limitations_texts=[
            "Synthetic scenario evidence only.",
            "Do not infer prevalence, causality, or statistical significance from this report.",
        ],
        provenance_texts=[
            "Model openai/test-model",
            "Provider openrouter",
            "Protocol version 1.0",
            "Blueprint and manifest hashes are recorded.",
        ],
        fieldwork_handoff_texts=[
            "Use this dry run to refine wording and hand off to human fieldwork.",
            "Do not treat synthetic personas as representative of the target population.",
        ],
        standards_alignment_texts=[
            "Purpose and process disclosure for sample source, questionnaire, and fieldwork handoff.",
            "Questionnaire and denominator disclosure for base-size suppression and weighting notes.",
            "Transparency disclosure for provenance and limitations.",
        ],
        research_basis_alignment_texts=[
            "Distributional evaluation is reported through selected metric pass rate wording.",
            "Segment and equity checks are exploratory and non-inferential.",
            "Multivariate clustering and joint respondent structure are not claimed.",
            "Source context and retrieval limits are disclosed.",
            "Human validation and human fieldwork remain required.",
        ],
        benchmark_wording_texts=[
            "Benchmark comparisons use selected metric pass rate wording only."
        ],
        report_warnings=[
            "Synthetic scenario evidence only.",
            "Do not infer prevalence, causality, or statistical significance from this report.",
        ],
        chart_decisions=[
            {
                "question_id": "q1",
                "status": "rendered",
                "reason": "Closed-ended distribution has a stable base and chart-safe categorical labels.",
                "visual_type": "bar",
            }
        ],
        pdf_rendering_mode="weasyprint",
    )


def test_weighted_quality_score_is_deterministic_and_thresholded() -> None:
    result = ReportQualityScorer().evaluate(valid_quality_input())

    assert result.total_score == 90.0
    assert result.raw_total_score == 90.0
    assert result.passes_threshold is True
    assert result.accepted is True
    assert result.failed_hard_gates == []
    assert result.weighted_breakdown == {
        "analytical_correctness": 27.0,
        "segmentation_and_bases": 18.0,
        "evidence_traceability": 13.5,
        "methodology_and_limitations": 13.5,
        "visual_readability_checks": 8.0,
        "reproducibility_and_artifact_integrity": 10.0,
    }


def test_hard_gates_override_high_score() -> None:
    broken = valid_quality_input().model_copy(
        update={
            "chart_labels": [
                "I liked it because it felt much easier to use than before."
            ],
            "percentages": [
                PercentageEvidence(label="Preference share", value=62.5, numerator=5)
            ],
            "key_findings": [
                KeyFindingEvidence(
                    finding_id="finding-1",
                    text="Most respondents preferred the simplified flow.",
                    question_id="q1",
                    response_evidence=[],
                )
            ],
            "composition_dimensions": [],
            "suppression_notes": {},
            "sections_present": ["title", "executive_summary"],
            "artifact_checksums": [
                ArtifactChecksum(
                    path="report.pdf",
                    expected_sha256="a" * 64,
                    actual_sha256="b" * 64,
                )
            ],
            "non_inferential_warning_present": False,
            "report_warnings": [],
            "claim_texts": ["This difference is statistically significant."],
            "chart_decisions": [],
            "rendered_text_artifacts": ["pdf_contains_visible_html_entities"],
            "pdf_rendering_mode": "fallback_plaintext",
            "attrition": AttritionEvidence(
                labels=["succeeded"],
                counts={"succeeded": 10, "failed": 1, "refused": 1},
            ),
            "report_depth": ReportDepthEvidence(
                pdf_pages=2,
                word_count=650,
                chart_count=1,
                table_count=1,
                question_count=1,
                segment_cut_count=0,
                qualitative_theme_count=0,
                traceable_quote_count=1,
            ),
            "category_scores": CategoryScores(
                analytical_correctness=100,
                segmentation_and_bases=100,
                evidence_traceability=100,
                methodology_and_limitations=100,
                visual_readability_checks=100,
                reproducibility_and_artifact_integrity=100,
            ),
            "research_design_tier": "lightweight_exploration",
            "objective_coverage": [],
            "decision_questions": [],
            "assumptions": [],
            "target_population_summary": "",
            "sampling_frame_summary": "",
            "segmentation_plan_summary": "",
            "analysis_plan_summary": "",
            "qualitative_coding_summary": "",
            "standards_alignment_texts": [],
            "benchmark_wording_texts": ["Benchmark accuracy matched the paper."],
            "typed_answer_issues": ["q1 choice labels contain narrative text"],
        }
    )

    result = ReportQualityScorer().evaluate(broken)

    assert result.raw_total_score == 100.0
    assert result.total_score == 0.0
    assert result.passes_threshold is False
    assert result.accepted is False
    assert set(result.failed_hard_gates) == {
        "typed_answer_integrity",
        "no_raw_narrative_chart_labels",
        "every_percentage_has_denominator",
        "key_findings_link_to_question_and_response_evidence",
        "population_dimensions_covered_or_suppressed",
        "required_sections_exist",
        "artifact_checksums_validate",
        "non_inferential_warning_exists",
        "no_inferential_claims",
        "rendered_text_has_no_html_artifacts",
        "attrition_represents_failed_and_refused",
        "professional_report_depth",
        "professional_research_design_required",
        "research_objectives_covered",
        "standards_alignment_disclosure_complete",
        "benchmark_wording_uses_selected_metric_pass_rate",
    }


def test_professional_objective_coverage_requires_decision_question() -> None:
    quality_input = valid_quality_input().model_copy(
        update={
            "objective_coverage": [
                {
                    "objective": "Preserve comparison context without overclaiming.",
                    "decision_question": None,
                    "covered_question_ids": ["q1", "q2"],
                    "status": "covered",
                    "notes": "Questions are present but no decision question is mapped.",
                }
            ]
        }
    )

    result = ReportQualityScorer().evaluate(quality_input)

    assert result.accepted is False
    assert "research_objectives_covered" in result.failed_hard_gates


def test_professional_chart_decisions_require_visual_and_replacement_types() -> None:
    broken = valid_quality_input().model_copy(
        update={
            "chart_decisions": [
                {
                    "question_id": "q1",
                    "status": "rendered",
                    "reason": "Closed-ended distribution has a stable base and chart-safe categorical labels.",
                },
                {
                    "question_id": "q2",
                    "status": "replaced_with_evidence_panel",
                    "reason": "Open-text evidence is better shown through coded themes and quotes than a raw chart.",
                },
                {
                    "question_id": "q3",
                    "status": "suppressed",
                    "reason": "Question base is too small for a stable chart.",
                },
            ]
        }
    )

    result = ReportQualityScorer().evaluate(broken)

    assert result.accepted is False
    assert "chart_decision_missing_visual_type" in result.failed_hard_gates
    assert "chart_decision_missing_replacement_type" in result.failed_hard_gates


def test_professional_quality_rejects_toy_synthetic_panel_size() -> None:
    broken = valid_quality_input().model_copy(
        update={
            "synthetic_panel_size": 12,
            "synthetic_panel_summary": "Synthetic panel size 12 built from the declared attribute grid.",
        }
    )

    result = ReportQualityScorer().evaluate(broken)

    assert result.accepted is False
    assert "professional_synthetic_panel_size" in result.failed_hard_gates


def test_missing_checksum_artifacts_fail_hard_gate() -> None:
    broken = valid_quality_input().model_copy(update={"artifact_checksums": []})

    result = ReportQualityScorer().evaluate(broken)

    assert result.accepted is False
    assert "artifact_checksums_validate" in result.failed_hard_gates


def test_shallow_two_page_report_fails_professional_depth_gate() -> None:
    shallow = valid_quality_input().model_copy(
        update={
            "report_depth": ReportDepthEvidence(
                pdf_pages=2,
                word_count=700,
                chart_count=1,
                table_count=2,
                question_count=1,
                segment_cut_count=1,
                qualitative_theme_count=1,
                traceable_quote_count=2,
            )
        }
    )

    result = ReportQualityScorer().evaluate(shallow)

    assert result.accepted is False
    assert "professional_report_depth" in result.failed_hard_gates


def test_build_quality_input_derives_real_gate_inputs(tmp_path: Path) -> None:
    report = ReportModel.example()
    json_path = tmp_path / "report.json"
    html_path = tmp_path / "report.html"
    pdf_path = tmp_path / "report.pdf"
    checksums_path = tmp_path / "checksums.json"
    json_path.write_text("{}", encoding="utf-8")
    html_path.write_text(
        "<html><body><section><h2>Report warnings and chart decisions</h2><h3>Report warnings</h3><p>Synthetic scenario evidence only.</p><p>Do not infer prevalence, causality, or statistical significance from this report.</p><h3>Chart decision log</h3><p>q1: rendered. Closed-ended distribution has a stable base and chart-safe categorical labels.</p></section></body></html>",
        encoding="utf-8",
    )
    pdf = canvas.Canvas(str(pdf_path), pagesize=A4, pageCompression=1, invariant=1)
    pdf.drawString(48, A4[1] - 48, "Report warnings and chart decisions")
    pdf.drawString(48, A4[1] - 56, "Chart decision log")
    pdf.drawString(48, A4[1] - 64, "Synthetic scenario evidence only.")
    pdf.drawString(
        48,
        A4[1] - 80,
        "Do not infer prevalence, causality, or statistical significance from this report.",
    )
    pdf.drawString(48, A4[1] - 96, "q1: rendered. Closed-ended distribution has a stable base and chart-safe categorical labels.")
    pdf.save()
    checksums_path.write_text(
        '{"report.json":"44136fa355b3678a1146ad16f7e8649e94fb4fc21f e77e8310c060f61caaff8a"}'.replace(" ", ""),
        encoding="utf-8",
    )
    artifacts = ReportArtifacts(
        json_path=json_path,
        html_path=html_path,
        pdf_path=pdf_path,
        checksums_path=checksums_path,
        chart_paths=[],
    )

    quality_input = build_quality_input(report, artifacts)

    assert quality_input.non_inferential_warning_present is True
    assert quality_input.report_warnings
    assert quality_input.chart_decisions
    assert quality_input.rendered_text_artifacts == []
    assert quality_input.pdf_rendering_mode == "weasyprint"
    assert set(REQUIRED_REPORT_SECTIONS).issubset(set(quality_input.sections_present))
    assert "research_design" in quality_input.sections_present
    assert "objective_coverage" in quality_input.sections_present
    assert "standards_alignment_appendix" in quality_input.sections_present
    assert quality_input.configured_population_dimensions == ["region"]
    assert quality_input.artifact_checksums[0].path == "report.json"
    assert quality_input.research_design_tier == "professional"
    assert quality_input.report_warnings
    assert quality_input.chart_decisions


def test_build_quality_input_caps_traceable_quote_count_to_rendered_evidence(tmp_path: Path) -> None:
    report = ReportModel.example()
    question = report.questions[0].model_copy(
        update={
            "themes": [
                ThemeEvidence(
                    theme_id="q1:theme:price",
                    label="Price concern",
                    count=60,
                    supporting_quote_ids=[f"q1:p{index}" for index in range(1, 61)],
                )
            ],
            "segment_cuts": [
                SegmentCut(
                    attribute="region",
                    value=f"segment-{index}",
                    base_count=10,
                    themes=[
                        ThemeEvidence(
                            theme_id=f"q1:segment:{index}:theme:price",
                            label="Price concern",
                            count=10,
                            supporting_quote_ids=[f"q1:p{quote}" for quote in range(1, 11)],
                        )
                    ],
                )
                for index in range(1, 6)
            ],
            "quote_evidence": [
                QuoteEvidence(
                    quote_id=f"q1:p{index}",
                    persona_id=f"p{index}",
                    text=f"Evidence row {index}.",
                    attributes={"region": "urban"},
                )
                for index in range(1, 61)
            ]
        }
    )
    report = report.model_copy(update={"questions": [question]})
    json_path = tmp_path / "report.json"
    html_path = tmp_path / "report.html"
    pdf_path = tmp_path / "report.pdf"
    checksums_path = tmp_path / "checksums.json"
    json_path.write_text("{}", encoding="utf-8")
    html_path.write_text("<html><body>bounded quote evidence</body></html>", encoding="utf-8")
    pdf = canvas.Canvas(str(pdf_path), pagesize=A4, pageCompression=1, invariant=1)
    pdf.drawString(48, A4[1] - 48, "bounded quote evidence")
    pdf.save()
    checksums_path.write_text("{}", encoding="utf-8")
    artifacts = ReportArtifacts(
        json_path=json_path,
        html_path=html_path,
        pdf_path=pdf_path,
        checksums_path=checksums_path,
        chart_paths=[],
    )

    quality_input = build_quality_input(report, artifacts)

    assert quality_input.report_depth.traceable_quote_count == 20
    assert quality_input.report_depth.qualitative_theme_count == 1


def test_build_quality_input_sanitizes_narrative_chart_labels(tmp_path: Path) -> None:
    report = ReportModel.example().model_copy(
        update={
            "questions": [
                ReportModel.example().questions[0].model_copy(
                    update={
                        "question_type": "open_text",
                        "distribution": Distribution(
                            labels=[
                                "I feel suspicious because the company is shifting responsibility onto consumers.",
                                "I feel skeptical because I do not trust the carbon-offset claims.",
                            ],
                            values=[3, 2],
                        ),
                    }
                )
            ]
        }
    )
    (tmp_path / "report.json").write_text("{}", encoding="utf-8")
    (tmp_path / "report.html").write_text(
        "<html><body>Non-inferential synthetic evidence only.</body></html>",
        encoding="utf-8",
    )
    (tmp_path / "report.pdf").write_bytes(b"%PDF-1.4\n")
    (tmp_path / "checksums.json").write_text(
        '{"report.json":"44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a","report.html":"","report.pdf":""}',
        encoding="utf-8",
    )
    artifacts = ReportArtifacts(
        json_path=tmp_path / "report.json",
        html_path=tmp_path / "report.html",
        pdf_path=tmp_path / "report.pdf",
        checksums_path=tmp_path / "checksums.json",
        chart_paths=[],
    )

    input_model = build_quality_input(report, artifacts)

    assert input_model.chart_labels == ["Response 1", "Response 2"]


def test_build_quality_input_flags_prose_labels_for_typed_questions(tmp_path: Path) -> None:
    report = ReportModel.example().model_copy(
        update={
            "questions": [
                ReportModel.example().questions[0].model_copy(
                    update={
                        "question_type": "choice",
                        "distribution": Distribution(
                            labels=[
                                "Yes, because the value proposition feels fair.",
                                "No, because it is too expensive.",
                            ],
                            values=[3, 2],
                        ),
                    }
                )
            ]
        }
    )
    (tmp_path / "report.json").write_text("{}", encoding="utf-8")
    (tmp_path / "report.html").write_text(
        "<html><body>Non-inferential synthetic evidence only.</body></html>",
        encoding="utf-8",
    )
    (tmp_path / "report.pdf").write_bytes(b"%PDF-1.4\n")
    (tmp_path / "checksums.json").write_text(
        '{"report.json":"44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a","report.html":"","report.pdf":""}',
        encoding="utf-8",
    )
    artifacts = ReportArtifacts(
        json_path=tmp_path / "report.json",
        html_path=tmp_path / "report.html",
        pdf_path=tmp_path / "report.pdf",
        checksums_path=tmp_path / "checksums.json",
        chart_paths=[],
    )

    input_model = build_quality_input(report, artifacts)
    score = ReportQualityScorer().evaluate(input_model)

    assert input_model.typed_answer_issues
    assert "typed_answer_integrity" in score.failed_hard_gates


def test_build_quality_input_flags_escaped_html_entities_in_rendered_text(tmp_path: Path) -> None:
    report = ReportModel.example()
    (tmp_path / "report.json").write_text("{}", encoding="utf-8")
    (tmp_path / "report.html").write_text(
        "<html><body>Report warnings and chart decisions.<p>Bad entity: &amp;amp;</p></body></html>",
        encoding="utf-8",
    )
    pdf_path = tmp_path / "report.pdf"
    pdf = canvas.Canvas(str(pdf_path), pagesize=A4, pageCompression=1, invariant=1)
    pdf.drawString(48, A4[1] - 48, "Report warnings and chart decisions.")
    pdf.drawString(48, A4[1] - 64, "Bad entity: &amp;")
    pdf.save()
    (tmp_path / "checksums.json").write_text(
        '{"report.json":"44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a","report.html":"","report.pdf":""}',
        encoding="utf-8",
    )
    artifacts = ReportArtifacts(
        json_path=tmp_path / "report.json",
        html_path=tmp_path / "report.html",
        pdf_path=tmp_path / "report.pdf",
        checksums_path=tmp_path / "checksums.json",
        chart_paths=[],
    )

    quality_input = build_quality_input(report, artifacts)
    score = ReportQualityScorer().evaluate(quality_input)

    assert "html_contains_visible_html_entities" in quality_input.rendered_text_artifacts
    assert "pdf_contains_visible_html_entities" in quality_input.rendered_text_artifacts
    assert "rendered_text_has_no_html_artifacts" in score.failed_hard_gates


def test_generic_standards_alignment_texts_are_insufficient_for_professional_quality() -> None:
    broken = valid_quality_input().model_copy(
        update={
            "standards_alignment_texts": ["Purpose and process disclosure."],
        }
    )

    result = ReportQualityScorer().evaluate(broken)

    assert result.accepted is False
    assert "standards_alignment_disclosure_complete" in result.failed_hard_gates


def test_professional_standards_alignment_requires_substantive_disclosure_topics() -> None:
    broken = valid_quality_input().model_copy(
        update={
            "target_population_summary": "Declared personas.",
            "sampling_frame_summary": "Declared attribute grid.",
            "segmentation_plan_summary": "Region cuts.",
            "analysis_plan_summary": "Analysis.",
            "qualitative_coding_summary": "Coding.",
            "standards_alignment_texts": [
                "Questionnaire disclosure.",
                "Transparency disclosure.",
            ],
        }
    )

    result = ReportQualityScorer().evaluate(broken)

    assert result.accepted is False
    assert "standards_alignment_disclosure_complete" in result.failed_hard_gates


def test_rendered_html_entity_artifacts_fail_quality_gate() -> None:
    broken = valid_quality_input().model_copy(
        update={"rendered_text_artifacts": ["pdf_contains_visible_html_entities"]}
    )

    result = ReportQualityScorer().evaluate(broken)

    assert result.accepted is False
    assert "rendered_text_has_no_html_artifacts" in result.failed_hard_gates


def test_professional_fallback_pdf_mode_fails_quality_gate() -> None:
    broken = valid_quality_input().model_copy(update={"pdf_rendering_mode": "fallback_plaintext"})

    result = ReportQualityScorer().evaluate(broken)

    assert result.accepted is False
    assert result.total_score == 74.0
    assert "professional_pdf_uses_production_renderer" in result.failed_hard_gates


def test_professional_structured_reportlab_mode_passes_pdf_gate() -> None:
    quality_input = valid_quality_input().model_copy(update={"pdf_rendering_mode": "reportlab_structured"})

    result = ReportQualityScorer().evaluate(quality_input)

    assert result.accepted is True
    assert "professional_pdf_uses_production_renderer" not in result.failed_hard_gates


def test_build_quality_input_counts_segment_level_qualitative_themes(tmp_path: Path) -> None:
    base_question = ReportModel.example().questions[0]
    report = ReportModel.example().model_copy(
        update={
            "questions": [
                base_question.model_copy(
                    update={
                        "question_type": "open_text",
                        "distribution": Distribution(),
                        "themes": [
                            ThemeEvidence(
                                theme_id="q1:theme:1",
                                label="Price sensitivity and value concern",
                                count=2,
                                supporting_quote_ids=["q1:p1", "q1:p2"],
                            )
                        ],
                        "segment_cuts": [
                            SegmentCut(
                                attribute="region",
                                value="urban",
                                base_count=2,
                                themes=[
                                    ThemeEvidence(
                                        theme_id="q1:theme:urban",
                                        label="Convenience and workflow fit",
                                        count=1,
                                        supporting_quote_ids=["q1:p3"],
                                    )
                                ],
                            )
                        ],
                    }
                )
            ]
        }
    )
    (tmp_path / "report.json").write_text("{}", encoding="utf-8")
    (tmp_path / "report.html").write_text(
        "<html><body>Non-inferential synthetic evidence only.</body></html>",
        encoding="utf-8",
    )
    (tmp_path / "report.pdf").write_bytes(b"%PDF-1.4\n")
    (tmp_path / "checksums.json").write_text(
        '{"report.json":"44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a","report.html":"","report.pdf":""}',
        encoding="utf-8",
    )

    input_model = build_quality_input(
        report,
        ReportArtifacts(
            json_path=tmp_path / "report.json",
            html_path=tmp_path / "report.html",
            pdf_path=tmp_path / "report.pdf",
            checksums_path=tmp_path / "checksums.json",
            chart_paths=[],
        ),
    )

    assert input_model.report_depth.qualitative_theme_count == 2
    assert input_model.report_depth.traceable_quote_count >= 3


def test_build_quality_input_counts_only_rendered_chart_artifacts(tmp_path: Path) -> None:
    report = ReportModel.example().model_copy(
        update={
            "analytics": ReportAnalytics(
                population_charts=[
                    AnalyticsChart(
                        chart_id="population:region",
                        title="Region composition",
                        chart_family="population_segment",
                        visual_type="donut",
                        labels=["urban", "rural"],
                        values=[1, 1],
                        denominator=2,
                    )
                ]
            )
        }
    )
    (tmp_path / "report.json").write_text("{}", encoding="utf-8")
    (tmp_path / "report.html").write_text(
        "<html><body>Non-inferential synthetic evidence only.</body></html>",
        encoding="utf-8",
    )
    (tmp_path / "report.pdf").write_bytes(b"%PDF-1.4\n")
    (tmp_path / "checksums.json").write_text(
        '{"report.json":"44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a","report.html":"","report.pdf":""}',
        encoding="utf-8",
    )

    input_model = build_quality_input(
        report,
        ReportArtifacts(
            json_path=tmp_path / "report.json",
            html_path=tmp_path / "report.html",
            pdf_path=tmp_path / "report.pdf",
            checksums_path=tmp_path / "checksums.json",
            chart_paths=[],
        ),
    )

    assert input_model.report_depth.chart_count == 0


def test_benchmark_registry_metadata_is_authoritative_without_restricted_downloads() -> None:
    registry = load_benchmark_registry(
        Path("docs/benchmarks/registry.json")
    )

    assert registry.version == "1.0"
    assert [entry.benchmark_id for entry in registry.entries] == [
        "food_and_you_2",
        "stack_overflow_survey",
        "ess",
        "wvs",
    ]

    entries = {entry.benchmark_id: entry for entry in registry.entries}
    assert entries["food_and_you_2"].access_tier == "registration_required"
    assert entries["food_and_you_2"].download_permitted is False
    assert entries["stack_overflow_survey"].access_tier == "public"
    assert entries["stack_overflow_survey"].download_permitted is False
    assert entries["ess"].access_tier == "registration_required"
    assert entries["wvs"].access_tier == "registration_required"
