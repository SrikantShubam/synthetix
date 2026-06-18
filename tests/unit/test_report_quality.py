from __future__ import annotations

from pathlib import Path

from synthetix.reporting.quality import (
    REQUIRED_REPORT_SECTIONS,
    ArtifactChecksum,
    AttritionEvidence,
    CategoryScores,
    KeyFindingEvidence,
    PercentageEvidence,
    ReportQualityInput,
    ReportQualityScorer,
    build_quality_input,
    load_benchmark_registry,
)
from synthetix.reporting.models import ReportModel
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
    )


def test_weighted_quality_score_is_deterministic_and_thresholded() -> None:
    result = ReportQualityScorer().evaluate(valid_quality_input())

    assert result.total_score == 90.0
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
            "claim_texts": ["This difference is statistically significant."],
            "attrition": AttritionEvidence(
                labels=["succeeded"],
                counts={"succeeded": 10, "failed": 1, "refused": 1},
            ),
            "category_scores": CategoryScores(
                analytical_correctness=100,
                segmentation_and_bases=100,
                evidence_traceability=100,
                methodology_and_limitations=100,
                visual_readability_checks=100,
                reproducibility_and_artifact_integrity=100,
            ),
        }
    )

    result = ReportQualityScorer().evaluate(broken)

    assert result.total_score == 100.0
    assert result.passes_threshold is True
    assert result.accepted is False
    assert set(result.failed_hard_gates) == {
        "no_raw_narrative_chart_labels",
        "every_percentage_has_denominator",
        "key_findings_link_to_question_and_response_evidence",
        "population_dimensions_covered_or_suppressed",
        "required_sections_exist",
        "artifact_checksums_validate",
        "non_inferential_warning_exists",
        "no_inferential_claims",
        "attrition_represents_failed_and_refused",
    }


def test_missing_checksum_artifacts_fail_hard_gate() -> None:
    broken = valid_quality_input().model_copy(update={"artifact_checksums": []})

    result = ReportQualityScorer().evaluate(broken)

    assert result.accepted is False
    assert "artifact_checksums_validate" in result.failed_hard_gates


def test_build_quality_input_derives_real_gate_inputs(tmp_path: Path) -> None:
    report = ReportModel.example()
    json_path = tmp_path / "report.json"
    html_path = tmp_path / "report.html"
    pdf_path = tmp_path / "report.pdf"
    checksums_path = tmp_path / "checksums.json"
    json_path.write_text("{}", encoding="utf-8")
    html_path.write_text(
        "<html><body>Non-inferential synthetic evidence only.</body></html>",
        encoding="utf-8",
    )
    pdf_path.write_bytes(b"%PDF-1.4\n")
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
    assert set(quality_input.sections_present) == set(REQUIRED_REPORT_SECTIONS)
    assert quality_input.configured_population_dimensions == ["region"]
    assert quality_input.artifact_checksums[0].path == "report.json"


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
