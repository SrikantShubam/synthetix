# Transparent Simulation Dashboard Spec

## Purpose

Expose how each simulation was built and what responses were generated through a minimal server-rendered UI.

## Required Behavior

- Views: population segments, respondent table, response table, question distributions, benchmark status, and report download.
- Show segment counts and respondent-level attributes where available.
- Show response-level records or sampled response records with safe escaping.
- Keep FastAPI, Jinja2, and vanilla JavaScript; no SPA or frontend router.

## Acceptance Criteria

- Users can inspect segmentation and synthetic responses from the results UI.
- Benchmark status appears in the results view when available.
- UI remains server-rendered and progressively enhanced.
- Unsupported benchmark status is visible rather than hidden.

## Agent Allocation

- Assigned model: `gpt-5.4-mini`
- Reason: bounded UI template and route work.
