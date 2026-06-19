from __future__ import annotations

from datetime import datetime, timezone

from synthetix.blueprints.models import (
    ChoiceQuestion,
    OpenTextQuestion,
    PopulationSpec,
    ResearchDesign,
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
from synthetix.analysis.reporting import build_report
from synthetix.reporting.quality import ReportQualityScorer, build_quality_input


def _professional_blueprint() -> SimulationBlueprint:
    return SimulationBlueprint(
        title="Professional report study",
        purpose="Assess fit and barriers.",
        population=PopulationSpec(
            size=4,
            seed=11,
            attributes={"region": ["urban", "rural"], "role": ["operator", "manager"]},
        ),
        questions=[
            ChoiceQuestion(id="q1", prompt="Would you adopt it?", options=["Yes", "No"]),
            OpenTextQuestion(id="q2", prompt="What is the primary barrier?"),
        ],
        research_design=ResearchDesign(
            study_type="concept_test",
            research_objectives=["Measure concept fit.", "Identify barrier themes."],
            decision_questions=["Should the concept proceed?", "What objections matter most?"],
            assumptions=["Synthetic responses are exploratory only."],
            target_population_definition={
                "inclusion_rules": ["Adults in the target workflow."],
                "exclusion_rules": ["No minors."],
                "geography": "United States",
                "timeframe": "Current period",
                "unit_of_analysis": "Decision-maker",
            },
            sampling_or_simulation_frame={
                "persona_generation_frame": "Declared attribute grid.",
                "quotas_or_weights": ["No weighting applied."],
                "uncovered_groups": ["Undeclared occupations."],
            },
            segmentation_plan={
                "segment_variables": ["region", "role"],
                "planned_cuts": ["region", "role"],
                "minimum_base_rule": "Suppress cuts below n=2.",
                "suppression_rule": "Mark suppressed cuts explicitly.",
            },
            question_role_map={"q1": "primary_outcome", "q2": "qualitative_probe"},
            analysis_plan={
                "toplines": ["Overall concept fit topline."],
                "cross_tabs": ["Concept fit by region."],
                "likert_summaries": [],
                "rankings": [],
                "theme_coding": ["Barrier themes for q2."],
                "sensitivity_checks": ["Check failed attempts."],
                "benchmark_checks": ["Use selected metric pass rate wording only."],
            },
            qualitative_coding_plan={
                "coding_mode": "deterministic",
                "theme_granularity": "Barrier themes",
                "quote_evidence_required": True,
                "minimum_theme_count": 1,
            },
            report_requirements={
                "report_tier": "professional",
                "required_sections": ["research_design", "objective_coverage", "standards_alignment_appendix"],
                "minimum_figures": 1,
                "minimum_tables": 2,
                "appendix_requirements": ["Planned-vs-delivered appendix"],
                "audience_level": "professional",
            },
            disclosure_plan={
                "synthetic_only_warning": True,
                "non_inferential_limits": True,
                "model_provider_provenance": True,
                "data_quality_notes": ["Synthetic evidence only."],
            },
            standards_alignment={
                "iso_20252": ["Purpose disclosure."],
                "aapor_disclosure": ["Questionnaire disclosure."],
                "icc_esomar": ["Transparency disclosure."],
            },
        ),
    )


def _run_result() -> RunResult:
    return RunResult(
        run_id="run-1",
        status=RunStatus.COMPLETED,
        respondents=[
            RespondentResult(
                persona_id="p1",
                attributes={"region": "urban", "role": "operator"},
                status=AttemptStatus.SUCCEEDED,
                answers={"q1": "Yes", "q2": "Price pressure is the main barrier."},
                attempts=[AttemptRecord(number=1, status=AttemptStatus.SUCCEEDED)],
            ),
            RespondentResult(
                persona_id="p2",
                attributes={"region": "rural", "role": "manager"},
                status=AttemptStatus.SUCCEEDED,
                answers={"q1": "No", "q2": "Training effort looks too high."},
                attempts=[AttemptRecord(number=1, status=AttemptStatus.SUCCEEDED)],
            ),
        ],
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
    )


def test_professional_report_quality_requires_explicit_research_design_sections(tmp_path) -> None:
    blueprint = _professional_blueprint()
    manifest = RunManifest.create(
        run_id="run-1",
        blueprint=blueprint,
        source_hashes={},
        model_id="openai/test-model",
        provider="openrouter",
        parameters={},
    )
    report = build_report(blueprint, _run_result(), manifest)

    quality = build_quality_input(
        report,
        type(
            "Artifacts",
            (),
            {
                "json_path": tmp_path / "report.json",
                "html_path": tmp_path / "report.html",
                "pdf_path": tmp_path / "report.pdf",
                "checksums_path": tmp_path / "checksums.json",
                "chart_paths": [],
            },
        )(),
    )

    assert quality.research_design_tier == "professional"
    assert len(quality.objective_coverage) == 2
    assert quality.benchmark_wording_texts


def test_lightweight_report_cannot_pass_professional_quality_gate() -> None:
    blueprint = SimulationBlueprint(
        title="Legacy study",
        purpose="Explore reactions.",
        population=PopulationSpec(size=2, seed=2),
        questions=[ChoiceQuestion(id="q1", prompt="Would you adopt it?", options=["Yes", "No"])],
    )
    manifest = RunManifest.create(
        run_id="run-legacy",
        blueprint=blueprint,
        source_hashes={},
        model_id="openai/test-model",
        provider="openrouter",
        parameters={},
    )
    report = build_report(blueprint, _run_result().model_copy(update={"run_id": "run-legacy"}), manifest)
    quality_input = build_quality_input(
        report,
        type(
            "Artifacts",
            (),
            {
                "json_path": __import__("pathlib").Path("missing.json"),
                "html_path": __import__("pathlib").Path("missing.html"),
                "pdf_path": __import__("pathlib").Path("missing.pdf"),
                "checksums_path": __import__("pathlib").Path("missing.checksums"),
                "chart_paths": [],
            },
        )(),
    )
    quality_input = quality_input.model_copy(
        update={
            "sections_present": list(quality_input.sections_present) + [
                "research_design",
                "objective_coverage",
                "standards_alignment_appendix",
            ],
            "artifact_checksums": [],
            "non_inferential_warning_present": True,
        }
    )

    score = ReportQualityScorer().evaluate(quality_input)

    assert score.accepted is False
    assert "professional_research_design_required" in score.failed_hard_gates
