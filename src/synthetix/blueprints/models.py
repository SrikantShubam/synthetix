from __future__ import annotations

import hashlib
from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field, model_validator


class PopulationSpec(BaseModel):
    size: int = Field(ge=1, le=10_000)
    seed: int = Field(ge=0)
    attributes: dict[str, list[str]] = Field(default_factory=dict)
    psychographics: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_attributes(self) -> "PopulationSpec":
        empty = [name for name, values in self.attributes.items() if not values]
        if empty:
            raise ValueError(f"Population attributes cannot be empty: {', '.join(empty)}")
        return self


class ModelSelection(BaseModel):
    profile: str = "openrouter-default"
    temperature: float = Field(default=0.2, ge=0, le=2)
    max_output_tokens: int = Field(default=500, ge=1, le=20_000)
    seed: int | None = None


class BaseQuestion(BaseModel):
    id: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")
    prompt: str = Field(min_length=1, max_length=10_000)
    required: bool = True


class OpenTextQuestion(BaseQuestion):
    type: Literal["open_text"] = "open_text"


class ChoiceQuestion(BaseQuestion):
    type: Literal["choice"] = "choice"
    options: list[str] = Field(min_length=2, max_length=50)

    @model_validator(mode="after")
    def validate_options(self) -> "ChoiceQuestion":
        if len(set(self.options)) != len(self.options):
            raise ValueError("Choice options must be unique")
        return self


class LikertQuestion(BaseQuestion):
    type: Literal["likert"] = "likert"
    minimum: int = 1
    maximum: int = 5
    minimum_label: str = "Strongly disagree"
    maximum_label: str = "Strongly agree"

    @model_validator(mode="after")
    def validate_scale(self) -> "LikertQuestion":
        if self.maximum <= self.minimum:
            raise ValueError("Likert maximum must exceed minimum")
        return self


Question = Annotated[
    Union[OpenTextQuestion, ChoiceQuestion, LikertQuestion],
    Field(discriminator="type"),
]

QuestionRole = Literal[
    "screening",
    "primary_outcome",
    "driver",
    "diagnostic",
    "qualitative_probe",
    "metadata",
]


class TargetPopulationDefinition(BaseModel):
    inclusion_rules: list[str] = Field(default_factory=list)
    exclusion_rules: list[str] = Field(default_factory=list)
    geography: str = ""
    timeframe: str = ""
    unit_of_analysis: str = ""


class SamplingOrSimulationFrame(BaseModel):
    persona_generation_frame: str = ""
    quotas_or_weights: list[str] = Field(default_factory=list)
    uncovered_groups: list[str] = Field(default_factory=list)


class SegmentationPlan(BaseModel):
    segment_variables: list[str] = Field(default_factory=list)
    planned_cuts: list[str] = Field(default_factory=list)
    minimum_base_rule: str = ""
    suppression_rule: str = ""


class AnalysisPlan(BaseModel):
    toplines: list[str] = Field(default_factory=list)
    cross_tabs: list[str] = Field(default_factory=list)
    likert_summaries: list[str] = Field(default_factory=list)
    rankings: list[str] = Field(default_factory=list)
    theme_coding: list[str] = Field(default_factory=list)
    sensitivity_checks: list[str] = Field(default_factory=list)
    benchmark_checks: list[str] = Field(default_factory=list)


class QualitativeCodingPlan(BaseModel):
    coding_mode: Literal["deterministic", "model_assisted", "human_coded", "mixed"] = (
        "deterministic"
    )
    theme_granularity: str = ""
    quote_evidence_required: bool = True
    minimum_theme_count: int = Field(default=1, ge=0)


class ReportRequirements(BaseModel):
    report_tier: Literal["lightweight_exploration", "professional"] = "lightweight_exploration"
    required_sections: list[str] = Field(default_factory=list)
    minimum_figures: int = Field(default=0, ge=0)
    minimum_tables: int = Field(default=0, ge=0)
    appendix_requirements: list[str] = Field(default_factory=list)
    audience_level: str = "exploratory"


class DisclosurePlan(BaseModel):
    synthetic_only_warning: bool = True
    non_inferential_limits: bool = True
    model_provider_provenance: bool = True
    data_quality_notes: list[str] = Field(default_factory=list)


class StandardsAlignment(BaseModel):
    iso_20252: list[str] = Field(default_factory=list)
    aapor_disclosure: list[str] = Field(default_factory=list)
    icc_esomar: list[str] = Field(default_factory=list)


class ResearchDesign(BaseModel):
    study_type: Literal[
        "preliminary_simulation",
        "questionnaire_dry_run",
        "benchmark_replication",
        "concept_test",
        "policy_reaction",
        "custom",
    ] = "preliminary_simulation"
    research_objectives: list[str] = Field(default_factory=list)
    decision_questions: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    target_population_definition: TargetPopulationDefinition = Field(
        default_factory=TargetPopulationDefinition
    )
    sampling_or_simulation_frame: SamplingOrSimulationFrame = Field(
        default_factory=SamplingOrSimulationFrame
    )
    segmentation_plan: SegmentationPlan = Field(default_factory=SegmentationPlan)
    question_role_map: dict[str, QuestionRole] = Field(default_factory=dict)
    analysis_plan: AnalysisPlan = Field(default_factory=AnalysisPlan)
    qualitative_coding_plan: QualitativeCodingPlan = Field(
        default_factory=QualitativeCodingPlan
    )
    report_requirements: ReportRequirements = Field(default_factory=ReportRequirements)
    disclosure_plan: DisclosurePlan = Field(default_factory=DisclosurePlan)
    standards_alignment: StandardsAlignment = Field(default_factory=StandardsAlignment)
    source_mode: Literal["derived", "explicit", "confirmed"] = "explicit"

    def requires_professional_quality_gate(self) -> bool:
        return self.report_requirements.report_tier == "professional"

    @classmethod
    def example(
        cls,
        *,
        question_role_map: dict[str, QuestionRole] | None = None,
    ) -> "ResearchDesign":
        return cls(
            study_type="concept_test",
            research_objectives=["Measure concept fit."],
            decision_questions=["Should the concept proceed?"],
            assumptions=["Synthetic outputs are exploratory only."],
            target_population_definition=TargetPopulationDefinition(
                inclusion_rules=["Declared adults in the target workflow."],
                exclusion_rules=["Undeclared populations are out of scope."],
                geography="United States",
                timeframe="Current period",
                unit_of_analysis="Decision-maker",
            ),
            sampling_or_simulation_frame=SamplingOrSimulationFrame(
                persona_generation_frame="Declared attribute grid.",
                quotas_or_weights=["No weighting applied."],
                uncovered_groups=["Undeclared occupations."],
            ),
            segmentation_plan=SegmentationPlan(
                segment_variables=["region"],
                planned_cuts=["region"],
                minimum_base_rule="Suppress cuts below n=2.",
                suppression_rule="Mark suppressed cuts explicitly.",
            ),
            question_role_map=question_role_map or {},
            analysis_plan=AnalysisPlan(
                toplines=["Primary topline."],
                cross_tabs=["Primary cut by region."],
                sensitivity_checks=["Review invalid attempts."],
                benchmark_checks=["Use selected metric pass rate wording only."],
            ),
            qualitative_coding_plan=QualitativeCodingPlan(
                coding_mode="deterministic",
                theme_granularity="Barrier themes",
                quote_evidence_required=True,
                minimum_theme_count=1,
            ),
            report_requirements=ReportRequirements(
                report_tier="professional",
                required_sections=[
                    "research_design",
                    "objective_coverage",
                    "standards_alignment_appendix",
                ],
                minimum_figures=1,
                minimum_tables=2,
                appendix_requirements=["Planned-vs-delivered appendix"],
                audience_level="professional",
            ),
            disclosure_plan=DisclosurePlan(
                synthetic_only_warning=True,
                non_inferential_limits=True,
                model_provider_provenance=True,
                data_quality_notes=["Synthetic evidence only."],
            ),
            standards_alignment=StandardsAlignment(
                iso_20252=["Purpose and process disclosure."],
                aapor_disclosure=["Questionnaire and denominator disclosure."],
                icc_esomar=["Transparency disclosure."],
            ),
        )

    def validate_for_question_ids(self, question_ids: list[str]) -> None:
        if not self.requires_professional_quality_gate():
            return
        required_list_fields = {
            "research_objectives": self.research_objectives,
            "decision_questions": self.decision_questions,
            "assumptions": self.assumptions,
            "analysis_plan.toplines": self.analysis_plan.toplines,
        }
        missing_lists = [name for name, values in required_list_fields.items() if not values]
        if missing_lists:
            raise ValueError(
                "Professional ResearchDesign is missing required fields: "
                + ", ".join(missing_lists)
            )
        population = self.target_population_definition
        if (
            not population.inclusion_rules
            or not population.unit_of_analysis.strip()
            or not self.segmentation_plan.segment_variables
            or not self.segmentation_plan.minimum_base_rule.strip()
            or not self.segmentation_plan.suppression_rule.strip()
        ):
            raise ValueError(
                "Professional ResearchDesign must define target population and segmentation rules"
            )
        if not self.question_role_map:
            raise ValueError("Professional ResearchDesign must define question roles")
        missing_roles = [question_id for question_id in question_ids if question_id not in self.question_role_map]
        if missing_roles:
            raise ValueError(
                "Professional ResearchDesign is missing question role assignments for: "
                + ", ".join(missing_roles)
            )
        if not self.qualitative_coding_plan.theme_granularity.strip():
            raise ValueError("Professional ResearchDesign must define qualitative coding granularity")
        if not self.report_requirements.required_sections:
            raise ValueError("Professional ResearchDesign must define report requirements")
        if not self.disclosure_plan.data_quality_notes:
            raise ValueError("Professional ResearchDesign must define disclosure data-quality notes")
        alignment = self.standards_alignment
        if not (alignment.iso_20252 and alignment.aapor_disclosure and alignment.icc_esomar):
            raise ValueError("Professional ResearchDesign must define standards alignment references")

    @classmethod
    def derive_lightweight(cls, *, title: str, purpose: str, population: PopulationSpec, questions: list[Question]) -> "ResearchDesign":
        question_role_map: dict[str, QuestionRole] = {}
        for index, question in enumerate(questions):
            if question.type == "open_text":
                role: QuestionRole = "qualitative_probe"
            elif index == 0:
                role = "primary_outcome"
            else:
                role = "driver"
            question_role_map[question.id] = role
        segment_variables = sorted(population.attributes.keys())
        planned_cuts = list(segment_variables)
        return cls(
            study_type="preliminary_simulation",
            research_objectives=[purpose],
            decision_questions=[
                "What synthetic response patterns, barriers, or segment differences should be inspected next?"
            ],
            assumptions=[
                "Synthetic responses are exploratory scenario evidence only.",
                "Outputs are not representative human survey results.",
            ],
            target_population_definition=TargetPopulationDefinition(
                inclusion_rules=["Synthetic personas sampled from declared blueprint attributes."],
                exclusion_rules=["Undeclared real-world populations are out of scope."],
                unit_of_analysis="Synthetic respondent",
            ),
            sampling_or_simulation_frame=SamplingOrSimulationFrame(
                persona_generation_frame=f"Declared synthetic population for '{title}'.",
                quotas_or_weights=["No weighting applied."],
                uncovered_groups=["Any population segment not declared in the blueprint attributes."],
            ),
            segmentation_plan=SegmentationPlan(
                segment_variables=segment_variables,
                planned_cuts=planned_cuts,
                minimum_base_rule="Suppress segment summaries below n=2.",
                suppression_rule="Mark segment summaries as suppressed instead of overstating unstable slices.",
            ),
            question_role_map=question_role_map,
            analysis_plan=AnalysisPlan(
                toplines=["Per-question toplines for declared questions."],
                cross_tabs=[f"{variable} segment cut" for variable in segment_variables],
                theme_coding=[
                    f"Open-text theme review for {question.id}"
                    for question in questions
                    if question.type == "open_text"
                ],
                sensitivity_checks=[
                    "Review whether small synthetic populations overstate apparent consensus."
                ],
                benchmark_checks=[
                    "Any benchmark output must be described as selected metric pass rate only."
                ],
            ),
            qualitative_coding_plan=QualitativeCodingPlan(
                coding_mode="deterministic",
                theme_granularity="Repeated response wording",
                quote_evidence_required=True,
                minimum_theme_count=1,
            ),
            report_requirements=ReportRequirements(
                report_tier="lightweight_exploration",
                required_sections=["executive_summary", "limitations"],
                audience_level="exploratory",
            ),
            disclosure_plan=DisclosurePlan(
                synthetic_only_warning=True,
                non_inferential_limits=True,
                model_provider_provenance=True,
                data_quality_notes=["Lightweight derived study plan for backward-compatible exploratory runs."],
            ),
            standards_alignment=StandardsAlignment(
                iso_20252=["Standards-aligned disclosure is limited in lightweight mode."],
                aapor_disclosure=["Lightweight runs disclose synthetic-only methodology and denominators where available."],
                icc_esomar=["Lightweight runs include transparency and limitations language only."],
            ),
            source_mode="derived",
        )


class SimulationBlueprint(BaseModel):
    schema_version: Literal["1.0"] = "1.0"
    title: str = Field(min_length=1, max_length=200)
    purpose: str = Field(min_length=1, max_length=2_000)
    population: PopulationSpec
    model: ModelSelection = Field(default_factory=ModelSelection)
    questions: list[Question] = Field(min_length=1, max_length=100)
    research_design: ResearchDesign | None = None
    limitations: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_question_ids(self) -> "SimulationBlueprint":
        ids = [question.id for question in self.questions]
        if len(ids) != len(set(ids)):
            raise ValueError("Question IDs must be unique")
        if self.research_design is None:
            self.research_design = ResearchDesign.derive_lightweight(
                title=self.title,
                purpose=self.purpose,
                population=self.population,
                questions=self.questions,
            )
        self.research_design.validate_for_question_ids(ids)
        return self

    def canonical_json(self) -> str:
        return self.model_dump_json(exclude_none=True, by_alias=True)

    def content_hash(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()
