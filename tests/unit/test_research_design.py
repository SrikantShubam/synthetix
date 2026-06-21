from __future__ import annotations

import pytest
from pydantic import ValidationError

from synthetix.blueprints.models import (
    ChoiceQuestion,
    ModelSelection,
    OpenTextQuestion,
    PopulationSpec,
    ResearchIntake,
    ResearchDesign,
    SimulationBlueprint,
)
from synthetix.execution.executor import build_execution_user_prompt
from synthetix.population.sampler import sample_population


def _professional_blueprint() -> SimulationBlueprint:
    return SimulationBlueprint(
        title="Professional study",
        purpose="Assess adoption barriers and segment-specific fit.",
        population=PopulationSpec(
            size=4,
            seed=9,
            attributes={"region": ["urban", "rural"], "role": ["operator", "manager"]},
        ),
        model=ModelSelection(profile="openrouter-test"),
        questions=[
            ChoiceQuestion(id="q1", prompt="Would you adopt it?", options=["yes", "no"]),
            OpenTextQuestion(id="q2", prompt="Why or why not?"),
        ],
        research_design=ResearchDesign(
            study_type="concept_test",
            research_objectives=[
                "Measure synthetic concept fit.",
                "Identify barriers by segment.",
            ],
            decision_questions=[
                "Should the concept move to human fieldwork?",
                "Which segment-specific objections require mitigation?",
            ],
            assumptions=[
                "Synthetic responses are exploratory only.",
                "Segment differences are directional rather than inferential.",
            ],
            target_population_definition={
                "inclusion_rules": ["Adults responsible for the workflow under study."],
                "exclusion_rules": ["No minors."],
                "geography": "United States",
                "timeframe": "Current operating conditions",
                "unit_of_analysis": "Decision-maker",
            },
            sampling_or_simulation_frame={
                "persona_generation_frame": "Declared attribute grid over region and role.",
                "quotas_or_weights": ["No weighting applied."],
                "uncovered_groups": ["Undeclared occupations outside the attribute grid."],
            },
            segmentation_plan={
                "segment_variables": ["region", "role"],
                "planned_cuts": ["region", "role", "region x role"],
                "minimum_base_rule": "Suppress segment summaries below n=2.",
                "suppression_rule": "Report suppression instead of unstable cuts.",
            },
            question_role_map={"q1": "primary_outcome", "q2": "qualitative_probe"},
            analysis_plan={
                "toplines": ["Overall adoption topline."],
                "cross_tabs": ["Adoption by region and role."],
                "likert_summaries": [],
                "rankings": [],
                "theme_coding": ["Barrier themes from q2."],
                "sensitivity_checks": ["Check whether refusals cluster by segment."],
                "benchmark_checks": [],
            },
            qualitative_coding_plan={
                "coding_mode": "deterministic",
                "theme_granularity": "Barrier theme",
                "quote_evidence_required": True,
                "minimum_theme_count": 2,
            },
            report_requirements={
                "report_tier": "professional",
                "required_sections": [
                    "research_design",
                    "objective_coverage",
                    "standards_alignment_appendix",
                ],
                "minimum_figures": 2,
                "minimum_tables": 3,
                "appendix_requirements": ["Planned-vs-delivered appendix"],
                "audience_level": "professional",
            },
            disclosure_plan={
                "synthetic_only_warning": True,
                "non_inferential_limits": True,
                "model_provider_provenance": True,
                "data_quality_notes": ["Synthetic-only simulation frame disclosure."],
            },
            standards_alignment={
                "iso_20252": ["Purpose, population, and process disclosure."],
                "aapor_disclosure": ["Questionnaire and denominator disclosure."],
                "icc_esomar": ["Transparency and synthetic-method disclosure."],
            },
        ),
    )


def test_legacy_blueprint_derives_lightweight_research_design() -> None:
    blueprint = SimulationBlueprint(
        title="Legacy study",
        purpose="Explore concept reactions.",
        population=PopulationSpec(size=3, seed=4, attributes={"region": ["urban", "rural"]}),
        questions=[
            ChoiceQuestion(id="q1", prompt="Would you adopt it?", options=["yes", "no"]),
            OpenTextQuestion(id="q2", prompt="Why?"),
        ],
    )

    assert blueprint.research_design is not None
    assert blueprint.research_design.report_requirements.report_tier == "lightweight_exploration"
    assert blueprint.research_design.question_role_map == {
        "q1": "primary_outcome",
        "q2": "qualitative_probe",
    }
    assert blueprint.research_intake is not None
    assert blueprint.research_intake.mode == "novice"
    assert blueprint.research_intake.intended_synthetic_panel_size == 3


def test_professional_research_intake_requires_scale_and_question_rationales() -> None:
    blueprint = _professional_blueprint()
    with pytest.raises(ValidationError, match="ResearchIntake"):
        SimulationBlueprint(
            **blueprint.model_dump(mode="python")
            | {
                "research_intake": ResearchIntake(
                    mode="professional",
                    source_type="manual",
                    research_context="Dry run for a professional study.",
                    target_population_summary="Adults in the workflow.",
                    source_sample_size=400,
                    intended_synthetic_panel_size=4,
                    constraints=["Synthetic outputs are exploratory only."],
                    design_choices=["Segment by region and role."],
                    questionnaire_signals=["Need primary outcome plus barrier probe."],
                    segment_variables=["region", "role"],
                    expected_analyses=["Topline adoption read."],
                    unresolved_gaps=[],
                    question_rationales={"q1": "Primary adoption measure."},
                    extraction_confidence="high",
                    extraction_method="manual",
                    external_processing_used=False,
                )
            }
        )


def test_execution_prompt_separates_research_intake_from_study_design() -> None:
    blueprint = _professional_blueprint().model_copy(
        update={
            "research_intake": ResearchIntake(
                mode="professional",
                source_type="manual",
                research_context="Source brief describes a pre-fieldwork concept test for workflow adoption.",
                target_population_summary="Adults responsible for the workflow under study.",
                target_population_size=12000,
                source_sample_size=800,
                intended_synthetic_panel_size=4,
                constraints=["Do not overstate subgroup precision from the dry run."],
                design_choices=["Keep one primary outcome and one barrier probe."],
                questionnaire_signals=["Need a fit question and a rationale follow-up."],
                segment_variables=["region", "role"],
                expected_analyses=["Adoption topline and region cut."],
                unresolved_gaps=["Income segmentation is not yet specified."],
                question_rationales={
                    "q1": "Measures adoption intent for the core decision.",
                    "q2": "Captures the main adoption barrier in the respondent's own words.",
                },
                extraction_confidence="high",
                extraction_method="manual",
                external_processing_used=False,
            )
        }
    )

    prompt = build_execution_user_prompt(blueprint)

    assert "Research intake context:" in prompt
    assert "Target/source scale: target_population_size=12000; source_sample_size=800; synthetic_panel_size=4" in prompt
    assert "Question rationale:" in prompt
    assert "q1: Measures adoption intent for the core decision." in prompt
    assert "Answer only as the synthetic respondent described in the system prompt." in prompt
    assert "write the methodology" not in prompt.casefold()


def test_professional_research_design_requires_objectives() -> None:
    with pytest.raises(ValidationError, match="research_objectives"):
        SimulationBlueprint(
            **(
                _professional_blueprint().model_dump(mode="python")
                | {
                    "research_design": _professional_blueprint()
                    .research_design.model_copy(update={"research_objectives": []})
                }
            )
        )


def test_professional_research_design_requires_question_roles_for_all_questions() -> None:
    with pytest.raises(ValidationError, match="question role"):
        SimulationBlueprint(
            **_professional_blueprint().model_dump(mode="python")
            | {
                "research_design": _professional_blueprint()
                .research_design.model_copy(update={"question_role_map": {"q1": "primary_outcome"}})
            }
        )


def test_execution_prompt_includes_study_design_context_and_answer_contract() -> None:
    blueprint = _professional_blueprint()

    prompt = build_execution_user_prompt(blueprint)

    assert "Study objectives:" in prompt
    assert "Assumptions summary:" in prompt
    assert "Question roles:" in prompt
    assert "q1: primary_outcome" in prompt
    assert "q2: qualitative_probe" in prompt
    assert "Return a JSON object with a 'responses' array" in prompt
    assert "write the methodology" not in prompt.casefold()
    assert "report conclusions" not in prompt.casefold()


def test_persona_prompt_remains_respondent_focused() -> None:
    blueprint = _professional_blueprint()
    persona = sample_population(blueprint.population)[0]

    prompt = persona.prompt().casefold()

    assert "you are a synthetic scenario persona" in prompt
    assert "methodology" not in prompt
    assert "report conclusion" not in prompt
