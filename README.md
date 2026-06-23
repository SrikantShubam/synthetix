# Synthetix

Synthetix is an experimental survey dry-run platform.

The intended product is not "AI survey results" and not a replacement for human
fieldwork. The goal is to let a novice or professional researcher provide seed
research, constraints, a questionnaire, or a source document and receive an
inspectable dry run:

- what the study appears to be trying to learn
- what the target population and synthetic panel are
- why each question exists
- how synthetic respondents might answer under declared assumptions
- which segment cuts are too small or unsafe to report
- which charts should be rendered, suppressed, or replaced with tables/evidence
- what must still be validated through real human fieldwork

The project is built around a "golden path" research basis: synthetic personas
can be useful for survey pretesting and hypothesis generation when the system is
honest about limits, preserves the study design, and does not leak evaluation
targets into predictions. Synthetix is trying to turn that idea into a usable
open-source product.

## Non-Negotiable Boundary

Synthetix outputs are synthetic scenario evidence only.

Do not use this project to claim:

- representative human research
- prevalence estimates
- causal findings
- statistical significance
- confidence intervals
- ISO, AAPOR, ESOMAR, ICC, or WAPOR certification
- full replication of any paper, table, chart, wording, or qualitative codebook

The project may describe outputs as standards-aligned when the required
disclosures and gates pass. It must not claim standards certification.

## What Works Now

The current implementation has moved beyond the original metric-only benchmark
loop. The useful pieces now in place are:

- `ResearchIntake` before `ResearchDesign`, so source context and study design
  are separated from respondent personas.
- Novice and professional flows over the same backend.
- Local PDF/text/Markdown intake with explicit rules for low-confidence or
  scanned/layout-heavy documents.
- Opt-in Gemini document understanding plumbing for external document parsing,
  guarded by explicit transmission consent and `GEMINI_API_KEY` or
  `GOOGLE_API_KEY`.
- Separate `target_population_size`, `source_sample_size`, and
  `intended_synthetic_panel_size`.
- Golden-path fixtures for novice concept tests, professional dry runs, manual
  intake, and bad-input/scanned-document blocking.
- Professional report gates for research design, objectives, segmentation,
  question roles, qualitative coding, chart decisions, limitations, provenance,
  and human-fieldwork handoff.
- Report proof artifacts generated through the real renderer path, not a fake
  plaintext PDF fallback.
- Chart decision logging: rendered chart, suppressed chart, table replacement,
  or evidence-panel replacement.
- Leakage guardrails against using answer-bearing fixture fields as prediction
  inputs.

Current local verification:

```powershell
uv run pytest -q
# 177 passed

uv run python -m synthetix.cli.app golden-path-prove --workspace .
uv run python -m synthetix.cli.app golden-path-review --workspace .
```

The latest golden-path review passes, with one known warning: the golden-paper
contract is still marked `draft`.

## What Is Still Bad

This project is not production-quality yet.

The automated professional report score can still say `100.0`, but that is a
gate score, not a trustworthy product-quality score. It means the current
structured checks passed. It does not mean the report is as good as a real
professional survey report.

Known weak areas:

- Report writing is still too templated. It now has cross-question synthesis,
  but the narrative is not yet at the level of a strong human research report.
- Charting is still too narrow. The proof currently leans heavily on heatmaps,
  bars, and tables. It needs a better chart policy and more visual forms.
- Question interpretation is still shallow in places. The system explains roles
  and patterns, but it does not always reason deeply about tradeoffs,
  confounding, respondent interpretation, or decision risk.
- The quality score still rewards structure too much. It needs stronger tests
  against boilerplate, duplicated prose, and fake depth.
- The reference/golden-paper contract is still draft metadata, not a fully
  reviewed and locked research contract.
- Professional PDF output exists, but it is not visually comparable to an
  80-page polished reference report. The current goal is honest traceability
  first, presentation quality second.
- Some fixture checks are still too contract-shaped. They are better than the
  original examples, but they can still teach the system to satisfy markers
  instead of producing genuinely useful research reasoning.

Brutal current reviewer estimate:

| Phase | Score |
| --- | ---: |
| OCR / extraction | 88 |
| Input / fixture quality | 84 |
| Research / intake reasoning | 84 |
| Question quality | 78 |
| Output / simulation | 82 |
| Charts | 72 |
| Report generation | 80 |
| Reviewer gates | 88 |
| Overall | 82 |

These are reviewer estimates, not benchmark claims.

## Why The Project Exists

Most survey builders help users collect answers. Synthetix is trying to help
users debug the survey before fieldwork:

- Novice users should get plain-language warnings, question feedback, and a
  safe dry-run report.
- Professional users should get an auditable study plan, segmentation/base-size
  behavior, question rationale, chart decisions, and a clear handoff to human
  fieldwork.

The product should eventually feel closer to a research preflight lab than a
chatbot that invents survey results.

## Development Setup

```powershell
uv sync --extra dev
uv run synthetix validate examples/coffee.yaml
uv run synthetix preflight examples/coffee.yaml
uv run synthetix demo-report
uv run synthetix serve
```

Open `http://127.0.0.1:8000`.

To run a model-backed simulation:

```powershell
$env:SYNTHETIX_OPENROUTER_API_KEY="..."
uv run synthetix run examples/coffee.yaml --yes
```

To use opt-in Gemini document understanding:

```powershell
$env:GEMINI_API_KEY="..."
# or
$env:GOOGLE_API_KEY="..."
```

Gemini is for document understanding only unless a separate model capability
profile is approved.

## Docker

```powershell
Copy-Item .env.example .env
docker compose up --build
```

The Docker image includes WeasyPrint native dependencies. Windows development
may fall back to deterministic ReportLab PDF output if those libraries are not
available.

## Core Commands

```powershell
uv run pytest -q
uv run python -m synthetix.cli.app golden-path-prove --workspace .
uv run python -m synthetix.cli.app golden-path-review --workspace .
uv run python tools/sdlc/sdlc.py status
uv run python tools/sdlc/sdlc.py context
```

## Architecture In Short

- Modular monolith.
- Typer CLI and FastAPI web app share service paths.
- Blueprints are immutable and validated before execution.
- Runs create manifests, enforce token/cost preflight, execute bounded attempts,
  persist provenance in SQLite, and render JSON/HTML/PDF reports.
- OpenRouter is the primary research gateway through allowlisted capability
  profiles.
- Redis, distributed workers, PostgreSQL, vectors, and semantic projection are
  intentionally out of scope until measured workload or validated research need
  justifies them.

## Evaluation Honesty

The phrase "selected metric pass rate" means: the percentage of explicitly
selected benchmark metrics that passed their configured thresholds for a given
evaluation run.

It does not mean:

- survey accuracy
- human-response replication
- paper replication
- chart/table replication
- qualitative-code replication
- report-quality proof

If a score suddenly becomes near-perfect, treat it as suspicious until leakage
review proves otherwise.

