# Test Strategy

## Default Verification

- Run `uv run pytest` for broad regression coverage.
- Run targeted tests under `tests/unit/` for changed modules.
- Keep `ruff` and `mypy` expectations aligned with `pyproject.toml` when changes affect typing or style.

## Domain-Specific Checks

- Blueprint changes: run blueprint validation tests and at least one `uv run synthetix validate examples/coffee.yaml`.
- Guardrail/preflight changes: run guardrail tests and preflight examples.
- OpenRouter/model gateway changes: run profile and OpenRouter tests; do not require live API calls unless explicitly requested.
- Benchmark changes: run benchmark classifier/runtime/prediction/frozen evaluation tests and the relevant benchmark comparison command.
- Report changes: run report quality/reporting analytics tests and inspect generated report artifacts when layout changes.
- Web changes: run web/dashboard tests and inspect pages manually when UI behavior changes.
- Orchestrator changes: run orchestrator loop tests and verify forbidden-path gates.

## Holdout Rules

- Do not read, tune against, or mutate holdout/source-of-truth assets unless the active task is explicitly holdout-readiness.
- Holdout actual-vs-predicted remains blocked until locked holdout target JSON fixtures are authored and reviewed.
- Any predictor changes after a frozen validation result start a new development cycle and require clear provenance.

## SDLC/Gryph Checks

- Before implementation, run or inspect `python tools/sdlc/sdlc.py status`.
- After agent work, run `python tools/sdlc/sdlc.py ingest-gryph --since 1d`.
- Regenerate context with `python tools/sdlc/sdlc.py context`.
- Run Promptfoo gates when provider configuration is available:
  - `python tools/sdlc/sdlc.py eval plan`
  - `python tools/sdlc/sdlc.py eval readiness`
  - `python tools/sdlc/sdlc.py eval final`
