# Synthetix

Synthetix is a self-hosted synthetic scenario-exploration engine. It generates
model-conditioned responses from declared personas for hypothesis generation.
It is not representative human research and must not be used to infer prevalence,
causality, or statistical significance.

## Quick start

```powershell
uv sync --extra dev
uv run synthetix validate examples/coffee.yaml
uv run synthetix preflight examples/coffee.yaml
uv run synthetix demo-report
uv run synthetix serve
```

Open `http://127.0.0.1:8000`. To execute or parse documents:

```powershell
$env:SYNTHETIX_OPENROUTER_API_KEY="..."
uv run synthetix run examples/coffee.yaml --yes
```

## Docker

```powershell
Copy-Item .env.example .env
docker compose up --build
```

The Docker image includes WeasyPrint's native dependencies. Windows development
falls back to deterministic ReportLab output if those libraries are unavailable.

## Supported workflow

- JSON/YAML blueprint validation without model calls
- PDF, Markdown, and text questionnaire extraction with explicit transmission consent
- OpenRouter requests pinned to an allowlisted model and upstream provider
- Worst-case token and cost preflight
- Seeded population generation and bounded execution
- Complete retry, refusal, and failure retention
- SQLite run provenance and report artifacts
- Minimal server-rendered ingestion, status, result, and PDF views

Only `openrouter-default` is certified in this baseline. Additional models require
a capability profile and conformance tests.

