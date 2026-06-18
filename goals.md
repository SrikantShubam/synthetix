# Synthetix Goals

## Product Positioning

Synthetix is a transparent survey simulation sandbox. It helps users explore what could happen before they run a real survey, without claiming to replace representative human research.

The product is inspired by a seed-material-to-simulation workflow: users provide a survey idea, questionnaire, research brief, or population definition; Synthetix creates a synthetic respondent panel, runs the preliminary simulation, exposes the segmentation and responses, and produces a professional report.

## Primary Objective

Help students, researchers, founders, marketers, and professionals test survey assumptions early:

- what response patterns may appear
- which segments may differ
- which questions may be weak or ambiguous
- where a real human survey is still needed
- whether the simulation class has benchmark support

## Core Goals

1. Preliminary simulation: produce directional survey-simulation evidence before real fieldwork.
2. Transparent segmentation: show how the population was constructed and how respondents were assigned to segments.
3. Inspectable responses: preserve raw and aggregated synthetic responses so users can audit the result.
4. Benchmark calibration: compare supported domains against published benchmark evidence and mark unsupported domains as not benchmarkable.
5. Professional reporting: generate a clear PDF with methodology, distributions, segments, themes, limitations, and provenance.
6. Guardrailed claims: never present synthetic responses as representative polling, population prevalence, statistical significance, or causal inference.
7. Human-survey handoff: recommend when and how to proceed to real survey work.

## Benchmark And Ground-Truth Policy

The papers under `research/source_of_truth/` are source-of-truth holdout assets. They are allowed for benchmarking, evaluation, and human-vs-AI comparison. They are not allowed for training, prompt tuning, few-shot examples, benchmark-driven model selection on the same set, or self-improvement against the same holdout targets.

Development fixtures may be used for iteration only when they do not reuse exact holdout targets. Validation fixtures must be separate from development before any external performance claim.

## Report Quality Goal

The final report must be easy for a consumer to understand and rigorous enough for a professional to review. It must explain the setup, population, segmentation, synthetic responses, benchmark status, limitations, and recommended next steps.

## Non-Goals

- Replace human surveys.
- Claim population prevalence from synthetic respondents.
- Claim statistical significance or causal inference.
- Pretend benchmark confidence exists for unsupported domains.
- Hide failed responses, retries, refusals, or attrition.

## Current Readiness

Development benchmark fixtures and actual-vs-predicted comparison infrastructure exist. The remaining product gap is automatic emission of predicted metrics from the pipeline, validation fixture expansion, professional report hardening, transparent dashboard inspection, and a gated orchestrator loop.
