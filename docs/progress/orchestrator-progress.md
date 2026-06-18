# Orchestrator Progress

## Dispatch: 00-product-goals

- model: `gpt-5.4`
- allowed paths: `goals.md, docs/specs/00-product-goals.md`
- forbidden paths: `research/source_of_truth, data/benchmark-results/holdout`
- checks: `spec_presence, unit_tests`
- implementation prompt ready: `True`


### Accepted: 00-product-goals

- artifacts: `goals.md, docs/specs/00-product-goals.md`
- checks: `{'spec_presence': True, 'unit_tests': True}`

## Dispatch: 01-benchmark-thresholds

- model: `gpt-5.4`
- allowed paths: `docs/specs/01-benchmark-thresholds.md, src/synthetix`
- forbidden paths: `research/source_of_truth, data/benchmark-results/holdout`
- checks: `unit_tests, holdout_contamination, benchmark_classifier`
- implementation prompt ready: `True`


### Accepted: 01-benchmark-thresholds

- artifacts: `docs/specs/01-benchmark-thresholds.md, src/synthetix`
- checks: `{'unit_tests': True, 'holdout_contamination': True, 'benchmark_classifier': True}`

## Dispatch: 02-pipeline-predicted-metrics

- model: `gpt-5.4-mini`
- allowed paths: `src/synthetix, tests, data/benchmark-predictions`
- forbidden paths: `research/source_of_truth, data/benchmark-results/holdout`
- checks: `unit_tests, integration_tests, benchmark_comparison`
- implementation prompt ready: `True`


### Blocked: 02-pipeline-predicted-metrics

- reason: Missing passing checks: benchmark_comparison
- checks: `{'unit_tests': True, 'integration_tests': True, 'benchmark_comparison': False}`

## Dispatch: 02-pipeline-predicted-metrics

- model: `gpt-5.4-mini`
- allowed paths: `src/synthetix, tests, data/benchmark-predictions`
- forbidden paths: `research/source_of_truth, data/benchmark-results/holdout`
- checks: `unit_tests, integration_tests, benchmark_comparison`
- implementation prompt ready: `True`


### Accepted: 02-pipeline-predicted-metrics

- artifacts: `src/synthetix, tests, data/benchmark-predictions`
- checks: `{'unit_tests': True, 'integration_tests': True, 'benchmark_comparison': True}`

## Dispatch: 03-professional-report-pdf

- model: `gpt-5.4`
- allowed paths: `src/synthetix/reporting, src/synthetix/analysis, tests`
- forbidden paths: `research/source_of_truth, data/benchmark-results/holdout`
- checks: `unit_tests, report_quality, report_artifacts`
- implementation prompt ready: `True`


### Accepted: 03-professional-report-pdf

- artifacts: `src/synthetix/reporting, src/synthetix/analysis, tests`
- checks: `{'unit_tests': True, 'report_quality': True, 'report_artifacts': True}`

## Dispatch: 04-transparent-simulation-dashboard

- model: `gpt-5.4-mini`
- allowed paths: `src/synthetix/web, tests`
- forbidden paths: `research/source_of_truth, data/benchmark-results/holdout`
- checks: `unit_tests, integration_tests`
- implementation prompt ready: `True`


### Accepted: 04-transparent-simulation-dashboard

- artifacts: `src/synthetix/web, tests`
- checks: `{'unit_tests': True, 'integration_tests': True}`

## Dispatch: 05-validation-and-holdout-readiness

- model: `gpt-5.4`
- allowed paths: `research/benchmark_program/validation, docs/specs/05-validation-and-holdout-readiness.md`
- forbidden paths: `research/source_of_truth/holdout_papers`
- checks: `validation_evidence, holdout_contamination`
- implementation prompt ready: `True`


### Blocked: 05-validation-and-holdout-readiness

- reason: Missing passing checks: validation_evidence
- checks: `{'validation_evidence': False, 'holdout_contamination': True}`

## Dispatch: 05-validation-and-holdout-readiness

- model: `gpt-5.4`
- allowed paths: `research/benchmark_program/validation, docs/specs/05-validation-and-holdout-readiness.md`
- forbidden paths: `research/source_of_truth/holdout_papers`
- checks: `validation_evidence, holdout_contamination`
- implementation prompt ready: `True`


### Accepted: 05-validation-and-holdout-readiness

- artifacts: `research/benchmark_program/validation, docs/specs/05-validation-and-holdout-readiness.md`
- checks: `{'validation_evidence': True, 'holdout_contamination': True}`

## Dispatch: 06-agent-orchestrator-loop

- model: `gpt-5.4`
- allowed paths: `src/synthetix/orchestration, tests, docs/specs`
- forbidden paths: `research/source_of_truth, data/benchmark-results/holdout`
- checks: `unit_tests, integration_tests, policy_gates`
- implementation prompt ready: `True`


### Accepted: 06-agent-orchestrator-loop

- artifacts: `src/synthetix/orchestration, tests, docs/specs`
- checks: `{'unit_tests': True, 'integration_tests': True, 'policy_gates': True}`

