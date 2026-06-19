---
name: sdlc-reviewer
description: Use when reviewing or verifying SDLC-governed agent work, including comparing implementation against accepted plan, constraints, tests, Gryph activity evidence, Promptfoo final compliance, and producing a go/no-go decision.
---

# SDLC Reviewer

Review from evidence, not chat memory.

Workflow:

1. Run or inspect `python tools/sdlc/sdlc.py ingest-gryph --since 1d`.
2. Run or inspect `python tools/sdlc/sdlc.py context`.
3. Read `sdlc/context/agent_brief.md` first.
3. Read `sdlc/plans/accepted_plan.md`.
4. Read `sdlc/constraints.json`.
5. Read `sdlc/qa/test_strategy.md` and `sdlc/qa/qa_checklist.md`.
6. Read `sdlc/gryph_summary.json`.
7. Run `python tools/sdlc/sdlc.py eval final` when ready for final compliance.

Findings first. Prioritize:

- dropped constraints
- implementation outside accepted scope
- missing tests or failed verification
- risky file or command activity from Gryph
- skipped SDLC gates

Return a go/no-go decision with blockers.
