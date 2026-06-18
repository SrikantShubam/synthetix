# Research Assets

This directory contains locked external references for Synthetix benchmarking.

## Policy

- These PDFs are `source_of_truth` references.
- These PDFs are `holdout` benchmark assets.
- They are allowed for `benchmarking`, `evaluation`, and `human_vs_ai_comparison`.
- They are forbidden for `training`, `prompt_tuning`, `few_shot_examples`, `benchmark-driven model selection on the same set`, and any loop that adapts the system directly against these exact benchmark targets.

In short: this is test data. Do not train on it. Do not tune on it. Do not claim generalization from repeated optimization against the same papers.

## Layout

- `research/source_of_truth/holdout_papers/ai_persona/`
  Primary papers about AI persona simulation, replication quality, and limits.
- `research/source_of_truth/holdout_papers/survey_benchmarks/`
  Human-survey benchmark papers with explicit populations and reported findings.
- `research/source_of_truth/manifest.json`
  Machine-readable manifest with usage restrictions and benchmark roles.

## Immediate benchmark set

### AI persona holdout papers

1. `2603.19791_text_based_personas_privacy_decisions.pdf`
   Primary positive benchmark. Reported up to `88%` predictive accuracy in privacy-decision settings.

2. `2605.10659_when_can_digital_personas_reliably_approximate_human_survey_findings.pdf`
   Best methodology paper for realistic expectations on survey personas.

3. `2606.09013_beyond_averages_distributional_replication.pdf`
   Important guardrail paper. Mean agreement is not enough.

4. `2208.10264_using_llms_to_simulate_multiple_humans.pdf`
   Foundational replication paper for classic human-subject studies.

5. `2604.19787_llm_agents_predict_social_media_reactions.pdf`
   Strong narrower benchmark with `70.7%` overall reaction prediction accuracy.

### Human survey holdout paper

1. `2202.14036_external_validity_online_privacy_security_surveys.pdf`
   Human benchmark with explicit samples:
   `MTurk n=800`, gender-balanced `Prolific n=800`, representative `Prolific n=800`, compared to `Pew n=4272`.

## Intended use inside Synthetix

For each paper, build a benchmark fixture with:

- `population_definition`
- `human_sample_size`
- `segment_variables`
- `questionnaire_or_task`
- `reported_findings`
- `comparison_metric`
- `evaluation_only = true`

The system should compare its AI-persona outputs to these references. It should not learn from them inside the same evaluation path.
