from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from synthetix.benchmarking.golden_path import (
    ContractComparison,
    GoldenPathProofSummary,
    load_golden_path_fixtures,
    validate_golden_path_fixture_set,
)


class ReviewFinding(BaseModel):
    category: Literal["contract_extraction", "fixture_design", "product_logic", "report_generation"]
    severity: str
    code: str
    artifact_paths: list[str] = Field(default_factory=list)
    message: str
    expected: str = ""
    observed: str = ""
    remediation: str = ""


class ReviewCategorySummary(BaseModel):
    errors: int = 0
    warnings: int = 0


class GoldenPathReview(BaseModel):
    passed: bool
    summary: dict[str, ReviewCategorySummary] = Field(default_factory=dict)
    findings: list[ReviewFinding] = Field(default_factory=list)
    reviewed_fixture_ids: list[str] = Field(default_factory=list)
    reviewed_artifacts: list[str] = Field(default_factory=list)


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
        findings.append(
            ReviewFinding(
                category="fixture_design",
                severity="error",
                code="fixture_schema",
                message=message,
                expected="Fixture contains full intake, study plan, rationale, chart, warning, and handoff expectations.",
                observed=message,
                remediation="Repair the validation fixture before treating it as a product-quality gate.",
            )
        )

    contract_file = workspace / "research/golden_paper_contract.json"
    if not contract_file.exists():
        findings.append(
            ReviewFinding(
                category="contract_extraction",
                severity="error",
                code="missing_contract",
                artifact_paths=[str(contract_file)],
                message="Golden paper contract is missing.",
                expected="research/golden_paper_contract.json exists and defines methodology constraints.",
                observed="No contract artifact found.",
                remediation="Create the paper-derived contract before reviewing fixtures or OCR proof.",
            )
        )
    else:
        _review_contract_file(contract_file, findings)

    proof_file = proof_path or workspace / "data/golden-path/intake-proof/proof-summary.json"
    if not proof_file.exists():
        findings.append(
            ReviewFinding(
                category="report_generation",
                severity="error",
                code="missing_proof",
                artifact_paths=[str(proof_file)],
                message="Golden-path OCR proof summary is missing.",
                expected="data/golden-path/intake-proof/proof-summary.json",
                observed="No proof summary found.",
                remediation="Run `synthetix golden-path-prove` to generate OCR proof artifacts.",
            )
        )
        proof_summary = None
    else:
        proof_summary = GoldenPathProofSummary.model_validate_json(proof_file.read_text(encoding="utf-8"))
        _review_report_artifacts(workspace, proof_summary, findings)

    if proof_summary is not None:
        for proof in proof_summary.proofs:
            if proof.expected_blocked_without_gemini != proof.professional_mode_blocked_without_gemini:
                findings.append(
                    ReviewFinding(
                        category="product_logic",
                        severity="error",
                        code="ocr_policy_mismatch",
                        artifact_paths=[proof.source_file],
                        message=(
                            f"{proof.fixture_id}: expected blocked_without_gemini="
                            f"{proof.expected_blocked_without_gemini} but observed "
                            f"{proof.professional_mode_blocked_without_gemini}."
                        ),
                        expected=str(proof.expected_blocked_without_gemini),
                        observed=str(proof.professional_mode_blocked_without_gemini),
                        remediation="Fix OCR confidence or professional-mode blocking logic.",
                    )
                )
            if proof.fixture_class == "professional_survey_dry_run" and proof.extraction_confidence == "low":
                findings.append(
                    ReviewFinding(
                        category="contract_extraction",
                        severity="error",
                        code="professional_pdf_low_confidence",
                        artifact_paths=[proof.source_file],
                        message=f"{proof.fixture_id}: professional PDF proof remained low confidence.",
                        expected="medium or high local extraction confidence, or explicit Gemini/manual structured intake.",
                        observed=proof.extraction_confidence,
                        remediation="Use Gemini/manual structured intake or repair the source proof.",
                    )
                )
            if proof.comparison_path is None:
                if proof.source_format != "markdown_brief":
                    findings.append(
                        ReviewFinding(
                            category="contract_extraction",
                            severity="error",
                            code="missing_contract_comparison",
                            artifact_paths=[proof.source_file],
                            message=f"{proof.fixture_id}: field-by-field OCR comparison is missing.",
                            expected="Per-fixture comparison JSON exists.",
                            observed="comparison_path is null.",
                            remediation="Generate observed-contract and comparison artifacts for the real test-case source.",
                        )
                    )
            else:
                _review_contract_comparison(workspace / proof.comparison_path, findings)

    for fixture in fixtures:
        expected = fixture.expected_research_intake
        if expected.target_population_size and expected.intended_synthetic_panel_size >= expected.target_population_size:
            findings.append(
                ReviewFinding(
                    category="fixture_design",
                    severity="error",
                    code="scale_honesty",
                    message=f"{fixture.fixture_id}: synthetic panel size must remain smaller than target population size.",
                    expected="Synthetic panel size is smaller and separately reported.",
                    observed=f"target={expected.target_population_size}, panel={expected.intended_synthetic_panel_size}",
                    remediation="Repair fixture scale expectations.",
                )
            )
        if fixture.fixture_class == "bad_input_document" and not expected.professional_mode_blocked_without_gemini:
            findings.append(
                ReviewFinding(
                    category="fixture_design",
                    severity="error",
                    code="bad_input_policy_missing",
                    message=f"{fixture.fixture_id}: bad-input fixture must explicitly require Gemini or manual structured intake.",
                    expected="professional_mode_blocked_without_gemini=true",
                    observed="false",
                    remediation="Repair the bad-input fixture policy expectation.",
                )
            )
        if fixture.fixture_class == "professional_survey_dry_run":
            if "fleet workflow" in fixture.source_material.body.casefold():
                findings.append(
                    ReviewFinding(
                        category="fixture_design",
                        severity="error",
                        code="contradictory_source_truth",
                        message=f"{fixture.fixture_id}: professional fixture body still references fleet workflow instead of the EEA climate study.",
                        expected="Professional fixture brief aligns with the real EEA climate-survey PDF.",
                        observed=fixture.source_material.body,
                        remediation="Rewrite the professional fixture so the source brief matches the real test-case paper.",
                    )
                )
        if not fixture.expected_human_fieldwork_handoff:
            findings.append(
                ReviewFinding(
                    category="fixture_design",
                    severity="warning",
                    code="missing_handoff",
                    message=f"{fixture.fixture_id}: no human fieldwork handoff expectation is documented.",
                    expected="Human fieldwork handoff expectations present.",
                    observed="missing",
                    remediation="Add handoff language to the fixture.",
                )
            )

    passed = not any(finding.severity == "error" for finding in findings)
    reviewed_artifacts = [str(proof_file)]
    if proof_summary is not None:
        reviewed_artifacts.extend(proof.source_file for proof in proof_summary.proofs)
        reviewed_artifacts.extend(
            path
            for proof in proof_summary.proofs
            for path in (proof.observed_contract_path, proof.comparison_path)
            if path
        )
        reviewed_artifacts.extend(proof_summary.report_artifacts)
        if proof_summary.report_quality_path is not None:
            reviewed_artifacts.append(proof_summary.report_quality_path)
    review = GoldenPathReview(
        passed=passed,
        summary=_summarize_findings(findings),
        findings=findings,
        reviewed_fixture_ids=[fixture.fixture_id for fixture in fixtures],
        reviewed_artifacts=reviewed_artifacts,
    )
    destination = output_path or workspace / "data/golden-path/review-latest.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(review.model_dump_json(indent=2), encoding="utf-8")
    return review


def load_review(path: Path) -> GoldenPathReview:
    return GoldenPathReview.model_validate_json(path.read_text(encoding="utf-8"))


def _review_contract_file(path: Path, findings: list[ReviewFinding]) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    required_top_level = [
        "papers",
        "source_basis",
        "study",
        "population",
        "segmentation",
        "question_design",
        "analysis",
        "charts_and_report",
        "honesty",
        "evaluation",
    ]
    missing = [field for field in required_top_level if field not in payload]
    if missing:
        findings.append(
            ReviewFinding(
                category="contract_extraction",
                severity="error",
                code="contract_missing_fields",
                artifact_paths=[str(path)],
                message=f"Golden paper contract is missing fields: {missing}",
                expected=", ".join(required_top_level),
                observed=", ".join(sorted(payload.keys())),
                remediation="Complete the public-paper contract before deriving fixtures.",
            )
        )
    if payload.get("status") == "draft":
        findings.append(
            ReviewFinding(
                category="contract_extraction",
                severity="warning",
                code="contract_draft_status",
                artifact_paths=[str(path)],
                message="Golden paper contract is still marked draft.",
                expected="Reviewed contract metadata should eventually include reviewer and contract-hash values.",
                observed=f"status={payload.get('status')!r}",
                remediation="Finalize reviewer and hash metadata once the contract is stabilized.",
            )
        )


def _review_contract_comparison(path: Path, findings: list[ReviewFinding]) -> None:
    raw_payload = json.loads(path.read_text(encoding="utf-8"))
    comparison = ContractComparison.model_validate(raw_payload)
    if comparison.status == "failed":
        findings.append(
            ReviewFinding(
                category="contract_extraction",
                severity="error",
                code="contract_comparison_failed",
                artifact_paths=[str(path)],
                message=f"{comparison.fixture_id}: contract comparison status is failed.",
                expected="matched or blocked_as_expected",
                observed=comparison.status,
                remediation="Repair observed extraction or the expected contract before treating this fixture as passing.",
            )
        )
    if not comparison.fields:
        findings.append(
            ReviewFinding(
                category="contract_extraction",
                severity="error",
                code="empty_contract_comparison",
                artifact_paths=[str(path)],
                message=f"{comparison.fixture_id}: contract comparison has no fields.",
                expected="Field-by-field comparisons are required for proof-bearing fixtures.",
                observed="fields=[]",
                remediation="Populate expected_contract_fields and regenerate the proof.",
            )
        )
        return
    raw_fields = raw_payload.get("fields", [])
    for field, raw_field in zip(comparison.fields, raw_fields, strict=False):
        evidence_snippets = raw_field.get("evidence_snippets")
        substantive_evidence = raw_field.get("substantive_evidence")
        if (
            evidence_snippets == []
            or substantive_evidence is False
            or (not field.evidence and field.passed)
        ):
            findings.append(
                ReviewFinding(
                    category="contract_extraction",
                    severity="error",
                    code="contract_sparse_evidence",
                    artifact_paths=[str(path)],
                    message=f"{comparison.fixture_id}: field '{field.field}' only has shallow marker evidence.",
                    expected="Marker matches must include substantive surrounding OCR context.",
                    observed=json.dumps(raw_field),
                    remediation="Require sentence-level OCR excerpts rather than bare marker hits.",
                )
            )
        if field.passed:
            continue
        findings.append(
            ReviewFinding(
                category="contract_extraction",
                severity="error",
                code="contract_value_mismatch",
                artifact_paths=[str(path)],
                message=f"{comparison.fixture_id}: OCR comparison failed for field '{field.field}'.",
                expected=", ".join(field.expected_markers),
                observed=", ".join(field.matched_markers) or "no markers matched",
                remediation="Review the OCR output side by side with the expected test-case contract.",
            )
        )


def _review_report_artifacts(
    workspace: Path,
    proof_summary: GoldenPathProofSummary,
    findings: list[ReviewFinding],
) -> None:
    if not proof_summary.report_artifacts:
        findings.append(
            ReviewFinding(
                category="report_generation",
                severity="error",
                code="missing_report_proof",
                message="Golden-path proof run did not emit local report artifacts.",
                expected="report.json, report.html, report.pdf, checksums, and chart assets.",
                observed="No report artifacts listed.",
                remediation="Regenerate proof artifacts through the normal reporting path.",
            )
        )
    else:
        missing = [
            artifact
            for artifact in proof_summary.report_artifacts
            if not (workspace / artifact).exists()
        ]
        if missing:
            findings.append(
                ReviewFinding(
                    category="report_generation",
                    severity="error",
                    code="missing_report_artifact",
                    artifact_paths=missing,
                    message="Golden-path proof run references report artifacts that are missing.",
                    expected="Every listed report artifact exists on disk.",
                    observed=", ".join(missing),
                    remediation="Regenerate the proof report artifacts.",
                )
            )
    if proof_summary.report_quality_path is None:
        findings.append(
            ReviewFinding(
                category="report_generation",
                severity="error",
                code="missing_report_quality",
                message="Golden-path proof did not emit report-quality evidence.",
                expected="report_quality.json exists and shows the rendered report passes the professional quality gate.",
                observed="report_quality_path is null.",
                remediation="Write report-quality evidence from the real golden-path report run.",
            )
        )
        return
    quality_path = workspace / proof_summary.report_quality_path
    if not quality_path.exists():
        findings.append(
            ReviewFinding(
                category="report_generation",
                severity="error",
                code="missing_report_quality_file",
                artifact_paths=[proof_summary.report_quality_path],
                message="Golden-path proof references a report-quality file that is missing.",
                expected="report_quality.json exists on disk.",
                observed=proof_summary.report_quality_path,
                remediation="Regenerate the proof report artifacts.",
            )
        )
        return
    payload = json.loads(quality_path.read_text(encoding="utf-8"))
    score = payload.get("score", {})
    if not score.get("accepted"):
        findings.append(
            ReviewFinding(
                category="report_generation",
                severity="error",
                code="professional_report_quality_failed",
                artifact_paths=[str(quality_path)],
                message="Golden-path proof report failed the professional quality scorer.",
                expected="report_quality.accepted=true",
                observed=json.dumps(
                    {
                        "accepted": score.get("accepted"),
                        "total_score": score.get("total_score"),
                        "failed_hard_gates": [
                            gate.get("name")
                            for gate in score.get("hard_gates", [])
                            if not gate.get("passed")
                        ],
                    }
                ),
                remediation="Generate the proof report through the real reporting path and meet the professional depth and evidence gates.",
            )
        )


def _summarize_findings(findings: list[ReviewFinding]) -> dict[str, ReviewCategorySummary]:
    summary = {
        "contract_extraction": ReviewCategorySummary(),
        "fixture_design": ReviewCategorySummary(),
        "product_logic": ReviewCategorySummary(),
        "report_generation": ReviewCategorySummary(),
    }
    for finding in findings:
        bucket = summary[finding.category]
        if finding.severity == "error":
            bucket.errors += 1
        elif finding.severity == "warning":
            bucket.warnings += 1
    return summary
