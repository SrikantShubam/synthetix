# Gemini Primary, Groq Fallback, And Promptfoo Gates Spec

## Purpose

Use Gemini as the primary SDLC Promptfoo gate provider, with Groq as secondary fallback and OpenRouter as tertiary fallback, without weakening research reproducibility. Keep product runtime policy conservative until Gemini is explicitly certified there.

## Required Behavior

- SDLC Promptfoo gates try providers in this order: Gemini primary, Groq secondary, OpenRouter tertiary.
- Gemini and Groq may be used for SDLC Promptfoo gates only when their model IDs are allowlisted in `sdlc/eval_policy.json`.
- OpenRouter remains a tertiary SDLC gate fallback only when the allowlisted OpenRouter model is available.
- Promptfoo gate inputs must still pass `sdlc/eval_policy.json` allowlist checks.
- Product research runs keep OpenRouter as the primary gateway.
- Groq product fallback is disabled by default and requires:
  - a verified capability profile,
  - explicit user confirmation,
  - manifest recording of primary provider failure and fallback provider use,
  - no silent fallback for locked benchmark or holdout research runs.
- API keys are read only from environment variables or `.env` and never written to manifests, reports, or databases.

## Acceptance Criteria

- `python tools/sdlc/sdlc.py eval plan`, `readiness`, and `final` try Gemini first, then Groq, then OpenRouter when policy permits.
- SDLC eval policy rejects unapproved model IDs or forbidden file inputs.
- Product fallback profiles are visible in capability metadata but do not run automatically in benchmark or holdout mode.
- Tests cover policy parsing for Gemini, Groq, and OpenRouter Promptfoo provider model IDs plus environment loading without exposing secrets.

## Agent Allocation

- Assigned model: `gpt-5.4`
- Reason: provider fallback policy affects reproducibility, external transmission, and SDLC gates.
