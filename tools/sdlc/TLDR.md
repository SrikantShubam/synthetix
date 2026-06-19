# SDLC Toolkit TLDR

This repo uses a local SDLC governor around Codex and Claude Code.

## What Records Reality

Gryph records agent actions automatically through Codex and Claude Code hooks:

- file reads
- file writes
- commands
- diffs
- sessions
- failed or blocked tool activity

Use:

```powershell
python tools/sdlc/sdlc.py ingest-gryph --since 1d
python tools/sdlc/sdlc.py context
python tools/sdlc/sdlc.py context-health
```

## What Enforces The Process

The SDLC governor stores phase state and generated context:

```text
sdlc/state.json
sdlc/constraints.json
sdlc/plans/accepted_plan.md
sdlc/qa/acceptance_criteria.json
sdlc/qa/test_strategy.md
sdlc/subagents.yaml
sdlc/context/static_context.md
sdlc/context/dynamic_context.md
sdlc/context/agent_brief.md
```

Start with `sdlc/context/agent_brief.md`. Open `static_context.md`,
`accepted_plan.md`, or full specs only when the active task needs that detail.
Use `context-health` to spot oversized SDLC files before they become token drag.

Check current state:

```powershell
python tools/sdlc/sdlc.py status
```

## How To Use With Codex

First read:

```text
sdlc/context/agent_brief.md
```

Then read the task-specific spec, plan, or constraints only as needed.

Planning:

```text
Use sdlc-planner to plan this feature. Do not implement yet.
```

Implementation:

```text
Use sdlc-implementer to implement the accepted plan. First check SDLC status and refuse if blocked.
```

Review:

```text
Use sdlc-reviewer to verify the work using Gryph evidence, tests, constraints, and final compliance.
```

## Gates

Run when provider/API config is available:

```powershell
python tools/sdlc/sdlc.py eval plan
python tools/sdlc/sdlc.py eval readiness
python tools/sdlc/sdlc.py eval final
```

Promptfoo is approved for this pet project only through
`sdlc/eval_policy.json`. The CLI checks the approved provider/model and
allowlisted files before sending SDLC gate inputs to OpenRouter.

Promptfoo runtime state is forced into repo-local ignored paths:

```text
.cache/npm
.cache/promptfoo
```

Implementation should not start unless:

- accepted plan exists
- constraints exist
- acceptance criteria exist
- test strategy exists
- subagent split exists
- readiness gate passes or is explicitly deferred

## Synthetix Non-Negotiables

- Synthetic responses are simulation evidence, not representative human research.
- Never claim prevalence, confidence intervals, causality, statistical significance, or replacement of human surveys.
- Holdout/source-of-truth papers are evaluation-only.
- Unsupported benchmark domains must be not_benchmarkable.
- OpenRouter fallback stays disabled for research runs.
- API keys stay in environment variables and never in manifests.

## Current Project State

- Specs `00` through `06` are accepted.
- Development quality loop reached target.
- Frozen validation cycle `002` passed.
- Holdout actual-vs-predicted remains blocked until locked holdout target JSON fixtures are authored and reviewed.

## Subagent Routing

- `gpt-5.4` owns planning, constraints, scientific boundary, benchmark/holdout governance, architecture decisions, and final review.
- `gpt-5.4-mini` owns bounded implementation, unit tests, CLI/data-contract plumbing, dashboard plumbing, and narrow bug fixes after the plan is accepted.
- `gpt-5.4-mini` must not edit holdout/source-of-truth paths, scientific-boundary docs, security policy, product positioning, `sdlc/constraints.json`, or `sdlc/plans/accepted_plan.md`.
