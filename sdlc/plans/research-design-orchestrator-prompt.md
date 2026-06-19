# Orchestrator Prompt: ResearchDesign / StudyPlan

You are the Synthetix SDLC orchestrator. Implement the accepted ResearchDesign / StudyPlan plan as a gated loop, not a one-shot patch.

## Before Acting

1. Read `AGENTS.md`.
2. Read `sdlc/state.json`.
3. Read `sdlc/context/static_context.md` and `sdlc/context/dynamic_context.md`.
4. Read `sdlc/constraints.json`, `sdlc/qa/acceptance_criteria.json`, `sdlc/plans/accepted_plan.md`, and `sdlc/subagents.yaml`.
5. Run `python tools/sdlc/sdlc.py status`.

## Primary Objective

Add a professional ResearchDesign / StudyPlan layer that separates respondent personas from the study design. The study plan must define objectives, assumptions, target population, segmentation plan, question roles, analysis plan, qualitative coding plan, report requirements, and standards-alignment disclosure.

## Required SDLC Updates

- Ensure `docs/specs/09-research-design-study-plan.md` exists.
- Ensure `docs/protocols/research-design-standards-alignment.md` exists.
- Ensure `sdlc/constraints.json` includes `C017`.
- Ensure `sdlc/qa/acceptance_criteria.json` includes `A018` through `A021`.
- Add task `09-research-design-study-plan` to the orchestrator catalog.

## Implementation Rules

- Do not touch `research/source_of_truth` or `data/benchmark-results/holdout`.
- Do not claim ISO, AAPOR, ESOMAR, ICC, or WAPOR certification.
- Use `standards-aligned` only.
- Preserve backward compatibility by deriving lightweight study plans for old blueprints.
- Lightweight runs may execute but must not pass professional-report quality gates.
- Replace broad `accuracy` wording with `selected metric pass rate`.
- Do not imply benchmark scores mean full survey-paper, full table, full chart, full wording, or full report replication.

## Loop Behavior

1. Implement the smallest vertical slice.
2. Write or update tests first where practical.
3. Run targeted unit and integration tests.
4. Run SDLC context refresh.
5. Evaluate the active task gates.
6. If study-plan or report output is substandard, record rejection notes and create or continue the repair task.
7. Continue until `research_design_schema`, `study_plan_validation`, `standards_alignment_checklist`, `prompt_contract_tests`, `report_objective_coverage`, `professional_report_quality`, `unit_tests`, `integration_tests`, and `policy_gates` pass.
8. Stop only for hard blockers, forbidden path risk, failed policy gate, or final ship approval.

## Required Evidence Before Claiming Success

- Passing schema tests.
- Passing prompt contract tests.
- Passing report objective-coverage tests.
- Passing orchestrator loop tests.
- Updated SDLC context.
- Clear explanation of what `selected metric pass rate` means.
