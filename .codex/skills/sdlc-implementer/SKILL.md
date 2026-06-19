---
name: sdlc-implementer
description: Use when implementing an already accepted SDLC plan in Codex, with phase gate checks, TDD discipline, scoped context, Gryph-backed activity evidence, and refusal to code when implementation is blocked.
---

# SDLC Implementer

Before editing code:

1. Run or inspect `python tools/sdlc/sdlc.py status`.
2. Read `sdlc/state.json`.
3. Read `sdlc/context/agent_brief.md` first.
4. Read `sdlc/context/static_context.md` and `sdlc/context/dynamic_context.md` only when the brief does not contain enough detail for the active task.
5. Confirm `current_phase` is `implementation`.
6. Confirm implementation readiness eval has passed in `sdlc/state.json`.

If implementation is blocked, stop and report the blockers. Do not edit application code.

During implementation:

- Follow `sdlc/plans/accepted_plan.md`.
- Follow `sdlc/qa/test_strategy.md`.
- Keep changes small and scoped.
- Prefer tests before implementation where practical.
- Let Gryph record actions; do not manually write audit history.
- After material work, run `python tools/sdlc/sdlc.py ingest-gryph --since 1d`, `python tools/sdlc/sdlc.py context`, and inspect `python tools/sdlc/sdlc.py context-health` when SDLC files feel large.

Stop if:

- constraints conflict
- product or architecture decisions are unclear
- the same fix fails repeatedly
- verification evidence is missing
