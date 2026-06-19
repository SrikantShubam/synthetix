# ResearchDesign / StudyPlan Test Plan

## Schema Tests

- Complete professional `ResearchDesign` validates.
- Missing research objectives fail professional report mode.
- Missing target population definition fails professional report mode.
- Missing analysis plan fails professional report mode.
- Missing disclosure plan fails professional report mode.
- Existing v1 blueprints derive `lightweight_exploration` study plans.

## Prompt Contract Tests

- Execution prompt includes objective, assumptions summary, question role, and answer contract.
- Persona prompt remains respondent-focused.
- Prompt does not ask synthetic respondents to write methodology, analyze results, or produce report conclusions.

## Report Tests

- Report fails when findings do not map to research objectives.
- Report fails when decision questions are unanswered.
- Report fails when planned segment cuts are missing without suppression notes.
- Report fails when qualitative probes lack themes and traceable quote evidence.
- Report includes standards-alignment disclosure appendix.
- Report uses `selected metric pass rate`, not broad `accuracy` claims.

## Orchestrator Tests

- `09-research-design-study-plan` is routed to `gpt-5.4`.
- `gpt-5.4-mini` cannot edit standards/governance files for this task.
- Failed study-plan/report checks keep the task active.
- Quality loop creates or continues repair tasks when output is substandard.

## Benchmark Semantics Tests

- Numeric comparator still computes selected metric pass/fail using tolerances.
- User-facing output explains score numerator and denominator.
- Output explicitly excludes full paper/report/table/chart/wording equivalence unless separately evaluated.
