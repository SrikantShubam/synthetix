---
name: sdlc-planner
description: Use when planning or revising a feature under the local SDLC governor, including requirements, constraint extraction, multiple solution alternatives, plan diffs, accepted plan preparation, and Promptfoo plan-gate validation.
---

# SDLC Planner

Use the repo-local SDLC governor. Do not implement application code in this skill.

Workflow:

1. Run or inspect `python tools/sdlc/sdlc.py status`.
2. Read `sdlc/context/agent_brief.md` first.
3. Read `sdlc/context/static_context.md` and `sdlc/context/dynamic_context.md` only when the brief does not contain enough detail.
4. Create or revise plan files under `sdlc/plans/`.
5. Extract non-negotiable constraints into `sdlc/constraints.json`.
6. Produce 2-3 solution alternatives for meaningful features.
7. Generate plan diffs with `python tools/sdlc/sdlc.py diff-plan <before> <after>`.
8. Run `python tools/sdlc/sdlc.py eval plan` before accepting a plan.
9. Do not move to implementation until the user approves the accepted plan and readiness gates pass.

Required plan sections:

- Problem
- Goals
- Non-goals
- Constraints
- Assumptions
- Open questions
- Solution alternatives
- Tradeoffs
- Acceptance criteria
- Test strategy outline
- Subagent/task split outline
