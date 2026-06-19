# Agent Operating Rules

This repository uses an enforced SDLC workflow for AI coding agents.

Before acting:
1. Inspect `sdlc/state.json`.
2. Read `sdlc/context/dynamic_context.md`.
3. Read `sdlc/context/static_context.md`.
4. Obey the current SDLC phase.

Implementation is forbidden unless:
- `current_phase` is `implementation`
- `sdlc/plans/accepted_plan.md` exists
- `sdlc/constraints.json` exists
- `sdlc/qa/acceptance_criteria.json` exists
- `sdlc/qa/test_strategy.md` exists
- `sdlc/subagents.yaml` exists
- implementation readiness eval has passed

Do not manually write audit history. Gryph records agent actions.

Promptfoo external evals may run automatically only when `sdlc/eval_policy.json`
approves the provider/model and every eval input file is allowlisted. If the
policy blocks an eval, mark the gate deferred or failed; do not override it.

Use `python tools/sdlc/sdlc.py status` before coding and
`python tools/sdlc/sdlc.py context` after material work.

Do not drop constraints unless the user explicitly approves removal.
Do not claim success without verification evidence.
Prefer small vertical slices over broad rewrites.
Stop when product or architecture decisions are unclear.

Benchmark and leakage guardrails:
- Do not require `actual_targets`, answer keys, or equivalent ground-truth structures to generate predictions.
- Do not read or derive predictions from benchmark-answer-bearing fixture fields such as `human_reference_summary`, `calibration_clues`, `registry_summary`, or equivalent proxy fields.
- If benchmark scores collapse after leakage removal, treat prior high scores as contaminated and invalid, not as a regression to hide or explain away.
- If a change produces suspiciously large benchmark gains or near-perfect fixture scores, stop and perform an explicit leakage review before claiming improvement.
- Report and chart improvements must come from backend analytics contracts, deterministic aggregation, or presentation logic; do not game quality by leaking expected outputs or raw answer-bearing text into visuals.
