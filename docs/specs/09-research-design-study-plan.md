# ResearchDesign / StudyPlan Layer

## Purpose

Add a professional study-design layer between ingestion and execution. Personas define who the AI respondent is simulating. `ResearchDesign` defines why the study exists, what assumptions it rests on, how questions should be interpreted, how segments should be analyzed, and what the final report must prove it covered.

This layer is standards-aligned, not standards-certified. It should follow the disclosure and quality principles in ISO 20252-style market, opinion, and social research service requirements, AAPOR disclosure expectations, and ICC/ESOMAR ethics and transparency guidance.

## Required Behavior

- Every simulation has a `ResearchDesign`, either explicit or derived.
- Existing v1 blueprints without `research_design` remain valid, but receive a derived `lightweight_exploration` study plan.
- A derived lightweight plan may execute, but cannot pass the professional-report quality gate.
- Professional reports require explicit or confirmed study-plan coverage for objectives, assumptions, target population, segmentation, question roles, analysis plan, qualitative coding plan, report requirements, and disclosure plan.
- Model prompts keep personas respondent-focused. Study-design context is supplied separately and compactly.
- Reports are judged against planned objectives and analyses, not only against whatever response data exists.
- Benchmark scores are labeled as selected metric pass rates, not as broad accuracy or full-paper replication.

## ResearchDesign Contract

Add a Pydantic model named `ResearchDesign` and attach it to `SimulationBlueprint`.

Required fields for professional report mode:

- `study_type`: `preliminary_simulation`, `questionnaire_dry_run`, `benchmark_replication`, `concept_test`, `policy_reaction`, or `custom`
- `research_objectives`: one or more concrete objectives
- `decision_questions`: decisions the user wants the report to support
- `assumptions`: population, context, behavioral, and model-limit assumptions
- `target_population_definition`: inclusion rules, exclusion rules, geography/timeframe when applicable, and unit of analysis
- `sampling_or_simulation_frame`: persona generation frame, quotas/weights if any, and uncovered groups
- `segmentation_plan`: required segment variables, planned cuts, minimum base rule, and suppression rule
- `question_role_map`: each question tagged as `screening`, `primary_outcome`, `driver`, `diagnostic`, `qualitative_probe`, or `metadata`
- `analysis_plan`: required toplines, cross-tabs, Likert summaries, rankings, theme coding, sensitivity checks, and benchmark checks
- `qualitative_coding_plan`: coding mode, theme granularity, quote-evidence requirement, and minimum theme count
- `report_requirements`: report tier, required sections, minimum figures/tables, appendix requirements, and audience level
- `disclosure_plan`: synthetic-only warning, non-inferential limits, model/provider provenance, and data-quality notes
- `standards_alignment`: references to `iso_20252`, `aapor_disclosure`, and `icc_esomar`

## Pipeline Changes

- JSON/YAML ingestion accepts `research_design` directly.
- Document ingestion extracts or proposes a study plan for user review before approval.
- Validation blocks professional report mode when objectives, target population, mapped questions, analysis plan, or disclosure plan are missing.
- Execution prompts include study objective, assumptions summary, question role, and answer contract.
- Analysis builds planned-vs-delivered outputs from the analysis plan.
- Reporting includes research objectives, assumptions, study design, planned analyses, objective coverage, assumptions review, standards-alignment disclosure, and planned-vs-delivered appendix.

## Orchestrator Loop Requirements

- Add task `09-research-design-study-plan` to the orchestrator catalog.
- Assign policy/schema/report semantics to `gpt-5.4`.
- Assign bounded plumbing/tests/UI display to `gpt-5.4-mini` only after the contract is accepted.
- If study-plan quality is incomplete, keep the task active and record rejection notes.
- If report output is shallow, vague, missing objectives, missing planned analyses, or missing qualitative evidence, reject it and create or continue a repair task.
- If a benchmark score jumps suspiciously after study-plan/report changes, require leakage review before acceptance.

## Acceptance Criteria

- Complete professional `ResearchDesign` validates.
- Old blueprints derive `lightweight_exploration` study plans.
- Professional report mode fails without objectives, target population, mapped questions, analysis plan, and disclosure plan.
- Execution prompt includes compact study design context while persona prompt remains respondent-focused.
- Reports map findings back to objectives and decision questions.
- Reports include assumptions, segmentation plan, planned-vs-delivered analysis, qualitative coding evidence, limitations, and standards-alignment disclosure appendix.
- Benchmark displays use `selected_metric_pass_rate` language and explain exclusions.
- The orchestrator loops until `research_design_schema`, `study_plan_validation`, `standards_alignment_checklist`, `prompt_contract_tests`, `report_objective_coverage`, `professional_report_quality`, `unit_tests`, `integration_tests`, and `policy_gates` pass.

## Agent Allocation

- Assigned model: `gpt-5.4`
- Reason: study-design semantics, standards alignment, scientific boundaries, report claims, and loop acceptance require high judgment.
