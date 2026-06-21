from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field

from synthetix.benchmarking.golden_path import (
    GoldenPathProofSummary,
    load_golden_path_fixtures,
    validate_golden_path_fixture_set,
)


class ReviewFinding(BaseModel):
    severity: str
    code: str
    message: str


class GoldenPathReview(BaseModel):
    passed: bool
    findings: list[ReviewFinding] = Field(default_factory=list)
    reviewed_fixture_ids: list[str] = Field(default_factory=list)


def review_golden_path_workspace(
    workspace: Path,
    *,
    validation_dir: Path | None = None,
    proof_path: Path | None = None,
    output_path: Path | None = None,
) -> GoldenPathReview:
    fixture_dir = validation_dir or workspace / "research/benchmark_program/validation"
    fixtures = load_golden_path_fixtures(fixture_dir)
    findings: list[ReviewFinding] = []

    for message in validate_golden_path_fixture_set(fixtures):
        findings.append(ReviewFinding(severity="error", code="fixture_schema", message=message))

    proof_file = proof_path or workspace / "data/golden-path/intake-proof/proof-summary.json"
    if not proof_file.exists():
        findings.append(
            ReviewFinding(
                severity="error",
                code="missing_proof",
                message="Golden-path OCR proof summary is missing.",
            )
        )
        proof_summary = None
    else:
        proof_summary = GoldenPathProofSummary.model_validate_json(proof_file.read_text(encoding="utf-8"))

    if proof_summary is not None:
        for proof in proof_summary.proofs:
            if proof.expected_blocked_without_gemini != proof.professional_mode_blocked_without_gemini:
                findings.append(
                    ReviewFinding(
                        severity="error",
                        code="ocr_policy_mismatch",
                        message=(
                            f"{proof.fixture_id}: expected blocked_without_gemini="
                            f"{proof.expected_blocked_without_gemini} but observed "
                            f"{proof.professional_mode_blocked_without_gemini}."
                        ),
                    )
                )
            if proof.fixture_class == "professional_survey_dry_run" and proof.extraction_confidence == "low":
                findings.append(
                    ReviewFinding(
                        severity="error",
                        code="professional_pdf_low_confidence",
                        message=f"{proof.fixture_id}: professional PDF proof remained low confidence.",
                    )
                )
        if not proof_summary.report_artifacts:
            findings.append(
                ReviewFinding(
                    severity="warning",
                    code="missing_report_proof",
                    message="Golden-path proof run did not emit local report artifacts.",
                )
            )

    for fixture in fixtures:
        expected = fixture.expected_research_intake
        if expected.target_population_size and expected.intended_synthetic_panel_size >= expected.target_population_size:
            findings.append(
                ReviewFinding(
                    severity="error",
                    code="scale_honesty",
                    message=(
                        f"{fixture.fixture_id}: synthetic panel size must remain smaller than target population size."
                    ),
                )
            )
        if fixture.fixture_class == "bad_input_document" and not expected.professional_mode_blocked_without_gemini:
            findings.append(
                ReviewFinding(
                    severity="error",
                    code="bad_input_policy_missing",
                    message=(
                        f"{fixture.fixture_id}: bad-input fixture must explicitly require Gemini or manual structured intake."
                    ),
                )
            )
        if not fixture.expected_human_fieldwork_handoff:
            findings.append(
                ReviewFinding(
                    severity="warning",
                    code="missing_handoff",
                    message=f"{fixture.fixture_id}: no human fieldwork handoff expectation is documented.",
                )
            )

    passed = not any(finding.severity == "error" for finding in findings)
    review = GoldenPathReview(
        passed=passed,
        findings=findings,
        reviewed_fixture_ids=[fixture.fixture_id for fixture in fixtures],
    )
    destination = output_path or workspace / "data/golden-path/review-latest.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(review.model_dump_json(indent=2), encoding="utf-8")
    return review


def load_review(path: Path) -> GoldenPathReview:
    return GoldenPathReview.model_validate_json(path.read_text(encoding="utf-8"))
