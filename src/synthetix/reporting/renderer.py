from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, cast
from urllib.parse import urlparse

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from jinja2 import Environment, select_autoescape
from matplotlib.ticker import MaxNLocator

from synthetix.reporting.models import ReportModel


REPORT_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{{ view.title }}</title>
  <link rel="stylesheet" href="{{ stylesheet_href }}">
</head>
<body class="report-body">
  <header class="report-running-header">
    <div class="running-header-title">{{ view.title }}</div>
    <div class="running-header-meta">Run {{ view.run_id }} · Generated {{ view.generated_at_display }}</div>
  </header>
  <footer class="report-running-footer">
    <span>Non-inferential synthetic evidence only.</span>
    <span>Page <span class="page-number"></span></span>
  </footer>
  <main class="report-shell">
    <section class="cover-section">
      <p class="eyebrow">Final report</p>
      <h1>{{ view.title }}</h1>
      <p class="report-purpose">{{ view.purpose }}</p>
      <div class="report-meta-grid">
        <div><span>Run ID</span><strong>{{ view.run_id }}</strong></div>
        <div><span>Generated UTC</span><strong>{{ view.generated_at_display }}</strong></div>
        <div><span>Succeeded</span><strong>{{ view.failures.succeeded }}</strong></div>
        <div><span>Failed</span><strong>{{ view.failures.failed }}</strong></div>
        <div><span>Retries</span><strong>{{ view.failures.retries }}</strong></div>
        <div><span>Token usage</span><strong>{{ view.token_usage }}</strong></div>
      </div>
      <aside class="report-warning">
        <strong>Non-inferential use warning.</strong>
        Synthetic scenario exploration is not representative human research. Do not infer prevalence, causality, or statistical significance from this report.
      </aside>
      <section class="summary-card">
        <h2 id="executive-summary">Executive summary</h2>
        <p>{{ view.executive_summary }}</p>
      </section>
    </section>

    <nav class="toc-card" aria-labelledby="table-of-contents">
      <h2 id="table-of-contents">Table of contents</h2>
      <ol>
      {% for section in view.toc %}
        <li><a href="#{{ section.id }}">{{ section.label }}</a></li>
      {% endfor %}
      </ol>
    </nav>

    <section id="executive-findings" class="report-section">
      <h2>Executive findings</h2>
      <div class="finding-list">
      {% for finding in view.executive_findings %}
        <article class="finding-card">
          <h3>{{ finding.title }}</h3>
          <p>{{ finding.summary }}</p>
          {% if finding.evidence %}
          <p class="evidence-line"><strong>Evidence:</strong> {{ finding.evidence }}</p>
          {% endif %}
        </article>
      {% endfor %}
      </div>
    </section>

    <section id="research-design" class="report-section">
      <h2>Research design</h2>
      <p><strong>Study type:</strong> {{ view.research_design.study_type }}</p>
      <p><strong>Report tier:</strong> {{ view.research_design.report_tier }}</p>
      <h3>Research objectives</h3>
      <ul>
      {% for item in view.research_design.objectives %}
        <li>{{ item }}</li>
      {% endfor %}
      </ul>
      <h3>Decision questions</h3>
      <ul>
      {% for item in view.research_design.decision_questions %}
        <li>{{ item }}</li>
      {% endfor %}
      </ul>
      <h3>Assumptions</h3>
      <ul>
      {% for item in view.research_design.assumptions %}
        <li>{{ item }}</li>
      {% endfor %}
      </ul>
      <p><strong>Target population:</strong> {{ view.research_design.target_population }}</p>
      <p><strong>Simulation frame:</strong> {{ view.research_design.simulation_frame }}</p>
      <p><strong>Segmentation plan:</strong> {{ view.research_design.segmentation_plan }}</p>
      <p><strong>Analysis plan:</strong> {{ view.research_design.analysis_plan }}</p>
      <p><strong>Qualitative coding plan:</strong> {{ view.research_design.qualitative_coding }}</p>
    </section>

    <section id="population-composition" class="report-section">
      <h2>Population composition</h2>
      {% if view.population_summary %}
      <p>{{ view.population_summary }}</p>
      {% endif %}
      <table class="report-table">
        <caption>Table {{ view.population_table_number }}. Population composition and segment counts.</caption>
        <thead>
          <tr><th scope="col">Segment</th><th scope="col">Category</th><th scope="col">Count</th><th scope="col">Share</th></tr>
        </thead>
        <tbody>
        {% for row in view.population_rows %}
          <tr>
            <td>{{ row.segment }}</td>
            <td>{{ row.category }}</td>
            <td>{{ row.count }}</td>
            <td>{{ row.share }}</td>
          </tr>
        {% endfor %}
        </tbody>
      </table>
    </section>

	    <section id="question-distributions" class="report-section">
	      <h2>Question distributions</h2>
      {% for question in view.questions %}
      <article class="question-block">
        <div class="question-header">
          <div>
            <p class="section-kicker">{{ question.question_id }}</p>
            <h3>{{ question.prompt }}</h3>
          </div>
          <p class="denominator">Base n = {{ question.denominator }}</p>
        </div>
        {% if question.chart_path %}
        <figure class="chart-figure">
          <img src="{{ question.chart_path }}" alt="Distribution chart for {{ question.prompt }}">
          <figcaption>Figure {{ question.figure_number }}. {{ question.prompt }} distribution (n = {{ question.denominator }}).</figcaption>
        </figure>
        {% endif %}
        <table class="report-table">
          <caption>Table {{ question.table_number }}. {{ question.prompt }} counts and shares (n = {{ question.denominator }}).</caption>
          <thead>
            <tr><th scope="col">Response label</th><th scope="col">Count</th><th scope="col">Share</th></tr>
          </thead>
          <tbody>
          {% for row in question.rows %}
            <tr>
              <td>{{ row.label }}</td>
              <td>{{ row.value }}</td>
              <td>{{ row.share }}</td>
            </tr>
          {% endfor %}
          </tbody>
        </table>
        {% if question.quotes %}
        <div class="quote-group">
          <h4>Traceable synthetic evidence</h4>
          <ul>
          {% for quote in question.quotes %}
            <li>{{ quote }}</li>
          {% endfor %}
          </ul>
        </div>
        {% endif %}
      </article>
	      {% endfor %}
	    </section>

	    <section id="question-interpretation" class="report-section">
	      <h2>Question interpretation and implications</h2>
	      {% for item in view.question_interpretations %}
	      <article class="interpretation-card">
	        <h3>{{ item.question_id }}: {{ item.role }}</h3>
	        <p><strong>What was measured:</strong> {{ item.measurement }}</p>
	        <p><strong>Observed pattern:</strong> {{ item.pattern }}</p>
	        <p><strong>Interpretation:</strong> {{ item.interpretation }}</p>
	        <p><strong>Decision implication:</strong> {{ item.decision_implication }}</p>
	        <p><strong>Quality note:</strong> {{ item.quality_note }}</p>
	      </article>
	      {% endfor %}
	    </section>

    <section id="segment-comparisons" class="report-section">
      <h2>Segment comparisons</h2>
      {% for comparison in view.segment_comparisons %}
      <table class="report-table">
        <caption>Table {{ comparison.table_number }}. {{ comparison.title }} (n = {{ comparison.denominator }}).</caption>
        <thead>
          <tr><th scope="col">Segment</th><th scope="col">n</th><th scope="col">Summary</th></tr>
        </thead>
        <tbody>
        {% for row in comparison.rows %}
          <tr>
            <td>{{ row.name }}</td>
            <td>{{ row.n }}</td>
            <td>{{ row.summary }}</td>
          </tr>
        {% endfor %}
        </tbody>
      </table>
      {% else %}
      <p>No segment comparisons were available.</p>
      {% endfor %}
    </section>

    <section id="qualitative-themes" class="report-section">
      <h2>Qualitative themes and evidence</h2>
      {% for theme in view.qualitative_themes %}
      <article class="theme-card">
        <h3>{{ theme.theme }}</h3>
        <p>{{ theme.summary }}</p>
        {% if theme.evidence %}
        <ul>
        {% for item in theme.evidence %}
          <li>{{ item }}</li>
        {% endfor %}
        </ul>
        {% endif %}
      </article>
      {% else %}
      <p>No qualitative themes were provided.</p>
      {% endfor %}
    </section>

    <section id="failures-sensitivity" class="report-section">
      <h2>Failures and sensitivity</h2>
      <div class="report-meta-grid compact">
        <div><span>Total personas</span><strong>{{ view.failures.total_personas }}</strong></div>
        <div><span>Succeeded</span><strong>{{ view.failures.succeeded }}</strong></div>
        <div><span>Failed</span><strong>{{ view.failures.failed }}</strong></div>
        <div><span>Retries</span><strong>{{ view.failures.retries }}</strong></div>
      </div>
      <table class="report-table">
        <caption>Table {{ view.failure_table_number }}. Failure classifications.</caption>
        <thead>
          <tr><th scope="col">Classification</th><th scope="col">Count</th></tr>
        </thead>
        <tbody>
        {% for row in view.failure_rows %}
          <tr><td>{{ row.classification }}</td><td>{{ row.count }}</td></tr>
        {% endfor %}
        </tbody>
      </table>
      {% if view.sensitivity_notes %}
      <div class="callout-card">
        <h3>Sensitivity notes</h3>
        <ul>
        {% for note in view.sensitivity_notes %}
          <li>{{ note }}</li>
        {% endfor %}
        </ul>
      </div>
      {% endif %}
    </section>

    <section id="methodology" class="report-section">
      <h2>Methodology</h2>
      <p>{{ view.methodology.approach }}</p>
      {% if view.methodology.response_generation %}
      <p><strong>Response generation:</strong> {{ view.methodology.response_generation }}</p>
      {% endif %}
      {% if view.methodology.quality_controls %}
      <ul>
      {% for item in view.methodology.quality_controls %}
        <li>{{ item }}</li>
      {% endfor %}
      </ul>
      {% endif %}
    </section>

	    <section id="objective-coverage" class="report-section">
	      <h2>Objective coverage</h2>
      <table class="report-table">
        <caption>Table {{ view.objective_coverage_table_number }}. Planned objectives and delivered evidence.</caption>
        <thead>
          <tr><th scope="col">Objective</th><th scope="col">Decision question</th><th scope="col">Covered questions</th><th scope="col">Status</th><th scope="col">Notes</th></tr>
        </thead>
        <tbody>
        {% for row in view.objective_coverage %}
          <tr>
            <td>{{ row.objective }}</td>
            <td>{{ row.decision_question }}</td>
            <td>{{ row.covered_questions }}</td>
            <td>{{ row.status }}</td>
            <td>{{ row.notes }}</td>
          </tr>
        {% endfor %}
        </tbody>
	      </table>
	      {% for row in view.planned_vs_delivered %}
	      <article class="interpretation-card">
	        <h3>{{ row.objective }}</h3>
	        <p><strong>Decision question:</strong> {{ row.decision_question }}</p>
	        <p><strong>Delivered evidence:</strong> {{ row.delivered_evidence }}</p>
	        <p><strong>Residual gap:</strong> {{ row.residual_gap }}</p>
	      </article>
	      {% endfor %}
	    </section>

    <section id="provenance" class="report-section">
      <h2>Provenance</h2>
      <table class="report-table">
        <caption>Table {{ view.provenance_table_number }}. Provenance and audit metadata.</caption>
        <tbody>
        {% for row in view.provenance_rows %}
          <tr><th scope="row">{{ row.label }}</th><td>{{ row.value }}</td></tr>
        {% endfor %}
        </tbody>
      </table>
    </section>

    <section id="limitations" class="report-section">
      <h2>Limitations</h2>
      <ul>
      {% for item in view.limitations %}
        <li>{{ item }}</li>
      {% endfor %}
      </ul>
    </section>

	    <section id="standards-alignment-appendix" class="report-section">
	      <h2>Standards-aligned disclosure appendix</h2>
	      <p>{{ view.standards_alignment.summary }}</p>
      <ul>
      {% for item in view.standards_alignment.disclosure_items %}
        <li>{{ item }}</li>
      {% endfor %}
      </ul>
	      <p><strong>Benchmark wording:</strong> {{ view.standards_alignment.benchmark_wording }}</p>
	    </section>

	    <section id="quote-evidence-appendix" class="report-section page-break">
	      <h2>Quote evidence appendix</h2>
	      <p>This appendix preserves the synthetic response evidence used for theme coding and finding support. Quote IDs are deterministic and tie each quote back to the question and synthetic persona.</p>
	      {% for block in view.quote_evidence_blocks %}
	      <h3>{{ block.question_id }}</h3>
	      <table class="report-table">
	        <caption>Quote evidence for {{ block.question_id }}.</caption>
	        <thead>
	          <tr><th scope="col">Quote ID</th><th scope="col">Attributes</th><th scope="col">Text</th></tr>
	        </thead>
	        <tbody>
	        {% for row in block.rows %}
	          <tr><td>{{ row.quote_id }}</td><td>{{ row.attributes }}</td><td>{{ row.text }}</td></tr>
	        {% endfor %}
	        </tbody>
	      </table>
	      {% endfor %}
	    </section>

	    <section id="technical-appendix" class="report-section page-break">
      <h2>Technical appendix</h2>
      <h3>Immutable manifest</h3>
      <pre class="code-block">{{ view.manifest_json }}</pre>
    </section>
  </main>
</body>
</html>
"""


PACKAGE_DIR = Path(__file__).resolve().parents[1]
REPORT_STYLESHEET = PACKAGE_DIR / "web" / "static" / "reporting.css"


@dataclass(frozen=True)
class ReportArtifacts:
    json_path: Path
    html_path: Path
    pdf_path: Path
    checksums_path: Path
    chart_paths: list[Path]


def _checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json_default(value: Any) -> str:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return str(value)


def _safe_url_fetcher(url: str) -> dict[str, Any]:
    _, default_url_fetcher = _load_weasyprint()

    parsed = urlparse(url)
    if parsed.scheme not in {"", "file", "data"}:
        raise ValueError("Remote assets are disabled during report rendering")
    return cast(dict[str, Any], default_url_fetcher(url))


def _coerce_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return {str(key): item for key, item in value.items()}
    return {}


def _coerce_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, Iterable) and not isinstance(value, (str, bytes, Mapping)):
        return list(value)
    return []


def _coerce_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _coerce_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _coerce_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "item"


def _looks_like_narrative_label(label: str) -> bool:
    stripped = label.strip()
    tokens = re.findall(r"[A-Za-z0-9']+", stripped)
    if len(tokens) > 5:
        return True
    if len(stripped) > 48:
        return True
    return any(marker in stripped for marker in (".", "!", "?", ";", ":", "\n"))


def _chart_labels(question: Mapping[str, Any]) -> list[str]:
    labels = [_coerce_text(label) for label in _coerce_list(question.get("labels"))]
    question_type = _coerce_text(question.get("question_type"))
    if question_type == "open_text" or any(_looks_like_narrative_label(label) for label in labels):
        return [f"Response {index}" for index, _ in enumerate(labels, start=1)]
    return labels


def _chart_title(question: Mapping[str, Any]) -> str:
    question_type = _coerce_text(question.get("question_type"))
    if question_type == "open_text":
        return "Top repeated response variants"
    return "Response distribution"


def _wrap_tick_label(label: str, width: int = 16) -> str:
    words = label.split()
    if not words:
        return label
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if len(candidate) <= width:
            current = candidate
            continue
        lines.append(current)
        current = word
    lines.append(current)
    return "\n".join(lines)


def _format_share(value: int, denominator: int) -> str:
    if denominator <= 0:
        return "0%"
    return f"{(value / denominator) * 100:.0f}%"


def _report_payload(report: ReportModel) -> dict[str, Any]:
    return {str(key): value for key, value in report.model_dump(mode="python").items()}


def _build_population_rows(payload: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    summary = ""
    rows: list[dict[str, Any]] = []
    for item in _coerce_list(payload.get("segment_composition")):
        segment_row = _coerce_mapping(item)
        segment_name = _coerce_text(segment_row.get("attribute"), "Population").replace("_", " ").title()
        for entry in _coerce_list(segment_row.get("segments")):
            row = _coerce_mapping(entry)
            share_value = row.get("share")
            share = (
                f"{_coerce_float(share_value) * 100:.0f}%"
                if isinstance(share_value, (float, int))
                else _coerce_text(share_value, "n/a")
            )
            rows.append(
                {
                    "segment": segment_name,
                    "category": _coerce_text(row.get("value"), "Unspecified"),
                    "count": _coerce_int(row.get("count")),
                    "share": share,
                }
            )
    if rows:
        summary = "Observed synthetic respondent composition across declared population dimensions."
        return summary, rows

    population = _coerce_mapping(payload.get("population"))
    summary = summary or f"Declared synthetic population size: {_coerce_int(population.get('size'))}."
    attributes = _coerce_mapping(population.get("attributes"))
    for raw_segment, values in attributes.items():
        segment = str(raw_segment)
        labels = [_coerce_text(value) for value in _coerce_list(values)]
        for label in labels:
            rows.append(
                {
                    "segment": segment.replace("_", " ").title(),
                    "category": label,
                    "count": 1,
                    "share": "Declared attribute",
                }
            )
    if not rows:
        rows.append(
            {
                "segment": "Population",
                "category": "Declared size",
                "count": _coerce_int(population.get("size")),
                "share": "100%",
            }
        )
    return summary, rows


def _build_executive_findings(payload: dict[str, Any]) -> list[dict[str, str]]:
    findings = []
    for item in _coerce_list(payload.get("executive_findings")):
        row = _coerce_mapping(item)
        findings.append(
            {
                "title": _coerce_text(row.get("title"), "Executive finding"),
                "summary": _coerce_text(
                    row.get("summary"),
                    "",
                ),
                "evidence": _coerce_text(
                    row.get("question_id"),
                    "",
                ),
            }
        )
    if findings:
        return findings
    return [
        {
            "title": "Summary finding",
            "summary": _coerce_text(payload.get("executive_summary")),
            "evidence": "",
        }
    ]


def _build_research_design(payload: dict[str, Any]) -> dict[str, Any]:
    research_design = _coerce_mapping(payload.get("research_design"))
    target_population = _coerce_mapping(research_design.get("target_population_definition"))
    simulation_frame = _coerce_mapping(research_design.get("sampling_or_simulation_frame"))
    segmentation_plan = _coerce_mapping(research_design.get("segmentation_plan"))
    analysis_plan = _coerce_mapping(research_design.get("analysis_plan"))
    qualitative_coding = _coerce_mapping(research_design.get("qualitative_coding_plan"))
    return {
        "study_type": _coerce_text(research_design.get("study_type"), "preliminary_simulation"),
        "report_tier": _coerce_text(
            _coerce_mapping(research_design.get("report_requirements")).get("report_tier"),
            "lightweight_exploration",
        ),
        "objectives": [_coerce_text(item) for item in _coerce_list(research_design.get("research_objectives"))],
        "decision_questions": [
            _coerce_text(item) for item in _coerce_list(research_design.get("decision_questions"))
        ],
        "assumptions": [_coerce_text(item) for item in _coerce_list(research_design.get("assumptions"))],
        "target_population": "; ".join(
            filter(
                None,
                [
                    ", ".join(_coerce_text(item) for item in _coerce_list(target_population.get("inclusion_rules"))),
                    _coerce_text(target_population.get("unit_of_analysis")),
                    _coerce_text(target_population.get("geography")),
                    _coerce_text(target_population.get("timeframe")),
                ],
            )
        ),
        "simulation_frame": "; ".join(
            filter(
                None,
                [
                    _coerce_text(simulation_frame.get("persona_generation_frame")),
                    ", ".join(_coerce_text(item) for item in _coerce_list(simulation_frame.get("quotas_or_weights"))),
                ],
            )
        ),
        "segmentation_plan": "; ".join(
            filter(
                None,
                [
                    ", ".join(_coerce_text(item) for item in _coerce_list(segmentation_plan.get("segment_variables"))),
                    ", ".join(_coerce_text(item) for item in _coerce_list(segmentation_plan.get("planned_cuts"))),
                    _coerce_text(segmentation_plan.get("minimum_base_rule")),
                    _coerce_text(segmentation_plan.get("suppression_rule")),
                ],
            )
        ),
        "analysis_plan": "; ".join(
            _coerce_text(item)
            for key in (
                "toplines",
                "cross_tabs",
                "likert_summaries",
                "rankings",
                "theme_coding",
                "sensitivity_checks",
                "benchmark_checks",
            )
            for item in _coerce_list(analysis_plan.get(key))
            if _coerce_text(item)
        ),
        "qualitative_coding": "; ".join(
            filter(
                None,
                [
                    _coerce_text(qualitative_coding.get("coding_mode")),
                    _coerce_text(qualitative_coding.get("theme_granularity")),
                    (
                        "Quote evidence required"
                        if qualitative_coding.get("quote_evidence_required")
                        else "Quote evidence optional"
                    ),
                ],
            )
        ),
    }


def _build_questions(payload: dict[str, Any]) -> list[dict[str, Any]]:
    views: list[dict[str, Any]] = []
    for index, item in enumerate(_coerce_list(payload.get("questions")), start=1):
        question = _coerce_mapping(item)
        distribution = _coerce_mapping(question.get("distribution"))
        labels = [_coerce_text(label) for label in _coerce_list(distribution.get("labels"))]
        values = [_coerce_int(value) for value in _coerce_list(distribution.get("values"))]
        chart = _coerce_mapping(question.get("chart"))
        chart_labels = [_coerce_text(label) for label in _coerce_list(chart.get("labels"))]
        chart_values = [_coerce_int(value) for value in _coerce_list(chart.get("values"))]
        chart_full_labels = [_coerce_text(label) for label in _coerce_list(chart.get("full_labels"))]
        denominators = _coerce_mapping(question.get("denominators"))
        denominator = _coerce_int(denominators.get("valid_responses"), default=sum(values))
        table_labels = labels
        table_values = values
        if not table_labels and chart_labels and chart_values:
            table_labels = chart_full_labels or chart_labels
            table_values = chart_values
        rows = [
            {
                "label": label,
                "value": value,
                "share": _format_share(value, denominator),
            }
            for label, value in zip(table_labels, table_values)
        ]
        views.append(
            {
                "question_id": _coerce_text(question.get("question_id"), f"q{index}"),
                "prompt": _coerce_text(question.get("prompt"), f"Question {index}"),
                "question_type": _coerce_text(question.get("question_type"), "open_text"),
                "denominator": denominator,
                "labels": labels,
                "values": values,
                "chart_labels": chart_labels or labels,
                "chart_values": chart_values or values,
                "chart_family": _coerce_text(chart.get("chart_family")),
                "rows": rows,
                "quotes": [_coerce_text(quote) for quote in _coerce_list(question.get("quotes"))],
                "segment_cuts": _coerce_list(question.get("segment_cuts")),
                "themes": _coerce_list(question.get("themes")),
                "figure_number": index,
            }
        )
    return views


def _top_response_text(question: dict[str, Any]) -> str:
    labels = [_coerce_text(label) for label in _coerce_list(question.get("labels"))]
    values = [_coerce_int(value) for value in _coerce_list(question.get("values"))]
    denominator = _coerce_int(question.get("denominator"))
    if labels and values:
        top_index = max(range(len(values)), key=values.__getitem__)
        return f"{labels[top_index]} was the most common valid response ({values[top_index]}/{denominator})."
    themes = [_coerce_mapping(theme) for theme in _coerce_list(question.get("themes"))]
    if themes:
        top_theme = max(themes, key=lambda theme: _coerce_int(theme.get("count")))
        return (
            f"{_coerce_text(top_theme.get('label'))} was the leading coded theme "
            f"({_coerce_int(top_theme.get('count'))}/{denominator})."
        )
    return "No valid pattern was available for interpretation."


def _build_question_interpretations(payload: dict[str, Any], questions: list[dict[str, Any]]) -> list[dict[str, str]]:
    research_design = _coerce_mapping(payload.get("research_design"))
    roles = _coerce_mapping(research_design.get("question_role_map"))
    decision_questions = [
        _coerce_text(item)
        for item in _coerce_list(research_design.get("decision_questions"))
        if _coerce_text(item)
    ]
    decision_text = "; ".join(decision_questions) or "Use as exploratory input before fieldwork."
    interpretations: list[dict[str, str]] = []
    for question in questions:
        question_id = _coerce_text(question.get("question_id"))
        question_type = _coerce_text(question.get("question_type"))
        role = _coerce_text(roles.get(question_id), "unmapped")
        pattern = _top_response_text(question)
        if question_type in {"choice", "likert"}:
            measurement = (
                "This closed-ended item captures a bounded synthetic response pattern. "
                "The denominator is the count of valid synthetic answers after type validation."
            )
            quality_note = (
                "Closed-ended labels are treated as measurement categories only; rationale belongs in a separate qualitative probe."
            )
        else:
            measurement = (
                "This qualitative item captures rationale or diagnostic feedback. Themes are coded from synthetic quotes and retain quote IDs."
            )
            quality_note = (
                "Theme counts indicate repeated synthetic rationale patterns, not population prevalence or statistical significance."
            )
        interpretations.append(
            {
                "question_id": question_id,
                "role": role.replace("_", " "),
                "measurement": measurement,
                "pattern": pattern,
                "interpretation": (
                    f"The observed pattern supports the '{role.replace('_', ' ')}' role by showing where "
                    "synthetic respondents converge and where additional human validation would be needed."
                ),
                "decision_implication": (
                    f"Use this evidence to inform: {decision_text}. Any launch, pricing, or fieldwork decision requires human validation."
                ),
                "quality_note": quality_note,
            }
        )
    return interpretations


def _build_segment_comparisons(questions: list[dict[str, Any]], start_table_number: int) -> list[dict[str, Any]]:
    comparisons: list[dict[str, Any]] = []
    table_number = start_table_number
    for question in questions:
        rows = []
        for segment in _coerce_list(question.get("segment_cuts")):
            row = _coerce_mapping(segment)
            if row.get("suppressed"):
                continue
            distribution = _coerce_mapping(row.get("distribution"))
            labels = [_coerce_text(label) for label in _coerce_list(distribution.get("labels"))]
            values = [_coerce_int(value) for value in _coerce_list(distribution.get("values"))]
            summary = ""
            if labels and values:
                top_index = max(range(len(values)), key=values.__getitem__)
                summary = f"{labels[top_index]} ({values[top_index]}/{_coerce_int(row.get('base_count'))})"
            elif _coerce_list(row.get("themes")):
                theme = _coerce_mapping(_coerce_list(row.get("themes"))[0])
                summary = _coerce_text(theme.get("label"))
            rows.append(
                {
                    "name": _coerce_text(row.get("value"), "Segment"),
                    "n": _coerce_int(row.get("base_count")),
                    "summary": summary,
                }
            )
        if not rows:
            continue
        comparisons.append(
            {
                "title": f"Segment comparison for {question['question_id']}",
                "denominator": _coerce_int(question.get("denominator")),
                "rows": rows,
                "table_number": table_number,
            }
        )
        table_number += 1
    return comparisons


def _build_qualitative_themes(payload: dict[str, Any]) -> list[dict[str, Any]]:
    views = []
    for question in _coerce_list(payload.get("questions")):
        question_row = _coerce_mapping(question)
        for item in _coerce_list(question_row.get("themes")):
            theme = _coerce_mapping(item)
            views.append(
                {
                    "theme": _coerce_text(theme.get("label"), "Theme"),
                    "summary": (
                        f"The coded theme for { _coerce_text(question_row.get('question_id')) } "
                        f"appeared in { _coerce_int(theme.get('count')) } traceable synthetic responses."
                    ),
                    "evidence": [
                        _coerce_text(entry)
                        for entry in _coerce_list(theme.get("supporting_quote_ids"))
                    ],
                }
            )
    return views


def _build_planned_vs_delivered(payload: dict[str, Any]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in _coerce_list(payload.get("objective_coverage")):
        coverage = _coerce_mapping(item)
        covered_questions = [
            _coerce_text(question_id)
            for question_id in _coerce_list(coverage.get("covered_question_ids"))
            if _coerce_text(question_id)
        ]
        status = _coerce_text(coverage.get("status"), "unknown")
        rows.append(
            {
                "objective": _coerce_text(coverage.get("objective")),
                "decision_question": _coerce_text(coverage.get("decision_question")),
                "delivered_evidence": (
                    f"Covered by {', '.join(covered_questions)} with status {status}. "
                    f"{_coerce_text(coverage.get('notes'))}"
                ),
                "residual_gap": (
                    "No inferential or representative claim is supported; the next step is human fieldwork "
                    "or a larger calibrated benchmark before operational decisions."
                ),
            }
        )
    return rows


def _build_quote_evidence_blocks(payload: dict[str, Any]) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    for question in _coerce_list(payload.get("questions")):
        question_row = _coerce_mapping(question)
        quote_rows = []
        for quote in _coerce_list(question_row.get("quote_evidence")):
            quote_row = _coerce_mapping(quote)
            attributes = _coerce_mapping(quote_row.get("attributes"))
            quote_rows.append(
                {
                    "quote_id": _coerce_text(quote_row.get("quote_id")),
                    "attributes": "; ".join(
                        f"{key}={value}" for key, value in sorted(attributes.items())
                    ),
                    "text": _coerce_text(quote_row.get("text")),
                }
            )
        if quote_rows:
            blocks.append(
                {
                    "question_id": _coerce_text(question_row.get("question_id")),
                    "rows": quote_rows,
                }
            )
    return blocks


def _build_objective_coverage(payload: dict[str, Any]) -> list[dict[str, str]]:
    rows = []
    for item in _coerce_list(payload.get("objective_coverage")):
        objective_row = _coerce_mapping(item)
        rows.append(
            {
                "objective": _coerce_text(objective_row.get("objective")),
                "decision_question": _coerce_text(objective_row.get("decision_question")),
                "covered_questions": ", ".join(
                    _coerce_text(question_id)
                    for question_id in _coerce_list(objective_row.get("covered_question_ids"))
                ),
                "status": _coerce_text(objective_row.get("status")),
                "notes": _coerce_text(objective_row.get("notes")),
            }
        )
    return rows


def _build_standards_alignment(payload: dict[str, Any]) -> dict[str, Any]:
    research_design = _coerce_mapping(payload.get("research_design"))
    alignment = _coerce_mapping(research_design.get("standards_alignment"))
    disclosure = _coerce_mapping(research_design.get("disclosure_plan"))
    analysis_plan = _coerce_mapping(research_design.get("analysis_plan"))
    items = [
        *_coerce_list(alignment.get("iso_20252")),
        *_coerce_list(alignment.get("aapor_disclosure")),
        *_coerce_list(alignment.get("icc_esomar")),
        *_coerce_list(disclosure.get("data_quality_notes")),
    ]
    return {
        "summary": "This appendix documents standards-aligned disclosure behavior only. It is not a certification claim.",
        "disclosure_items": [_coerce_text(item) for item in items],
        "benchmark_wording": "; ".join(
            _coerce_text(item) for item in _coerce_list(analysis_plan.get("benchmark_checks"))
        ),
    }


def _build_methodology(payload: dict[str, Any], provenance: dict[str, Any]) -> dict[str, Any]:
    methodology = _coerce_mapping(payload.get("methodology"))
    if methodology:
        return {
            "approach": _coerce_text(
                methodology.get("approach"),
                "Synthetic persona scenario exploration with deterministic aggregation.",
            ),
            "response_generation": _coerce_text(methodology.get("response_generation")),
            "quality_controls": [
                _coerce_text(item) for item in _coerce_list(methodology.get("quality_controls"))
            ],
        }
    return {
        "approach": (
            "Responses were generated from declared synthetic persona attributes under "
            f"protocol { _coerce_text(provenance.get('protocol_version'), 'unknown') }."
        ),
        "response_generation": "All retries and failures are retained in the output accounting.",
        "quality_controls": [
            "Question distributions are shown with explicit denominators.",
            "Remote assets are disabled during PDF rendering.",
        ],
    }


def _build_provenance_rows(provenance: dict[str, Any]) -> list[dict[str, str]]:
    ordered_keys = [
        ("Model", provenance.get("model_id")),
        ("Provider", provenance.get("provider")),
        ("Protocol version", provenance.get("protocol_version")),
        ("Blueprint hash", provenance.get("blueprint_hash")),
        ("Manifest hash", provenance.get("manifest_hash")),
    ]
    return [
        {"label": label, "value": _coerce_text(value)}
        for label, value in ordered_keys
        if value not in {None, ""}
    ]


def _build_failure_rows(failures: dict[str, Any]) -> list[dict[str, Any]]:
    classifications = _coerce_mapping(failures.get("classifications"))
    rows = [
        {"classification": key, "count": _coerce_int(value)}
        for key, value in sorted(classifications.items())
    ]
    if rows:
        return rows
    return [{"classification": "None recorded", "count": 0}]


def _build_report_view(payload: dict[str, Any]) -> dict[str, Any]:
    provenance = _coerce_mapping(payload.get("provenance"))
    failures = _coerce_mapping(payload.get("failures"))
    population_summary, population_rows = _build_population_rows(payload)
    questions = _build_questions(payload)
    next_table_number = 2
    for question in questions:
        question["table_number"] = next_table_number
        next_table_number += 1
    segment_comparisons = _build_segment_comparisons(questions, next_table_number)
    next_table_number += len(segment_comparisons)
    failure_table_number = next_table_number
    objective_coverage = _build_objective_coverage(payload)
    objective_coverage_table_number = failure_table_number + 1
    provenance_table_number = objective_coverage_table_number + 1

    return {
        "title": _coerce_text(payload.get("title"), "Synthetic scenario exploration"),
        "purpose": _coerce_text(payload.get("purpose")),
        "run_id": _coerce_text(payload.get("run_id")),
        "generated_at_display": _json_default(payload.get("generated_at")),
        "executive_summary": _coerce_text(payload.get("executive_summary")),
        "executive_findings": _build_executive_findings(payload),
        "research_design": _build_research_design(payload),
        "population_summary": population_summary,
        "population_rows": population_rows,
        "population_table_number": 1,
	        "questions": questions,
	        "question_interpretations": _build_question_interpretations(payload, questions),
	        "segment_comparisons": segment_comparisons,
	        "qualitative_themes": _build_qualitative_themes(payload),
        "failures": {
            "total_personas": _coerce_int(failures.get("total_personas")),
            "succeeded": _coerce_int(failures.get("succeeded")),
            "failed": _coerce_int(failures.get("failed")),
            "retries": _coerce_int(failures.get("retries")),
        },
        "failure_rows": _build_failure_rows(failures),
        "failure_table_number": failure_table_number,
        "sensitivity_notes": [
            _coerce_text(item)
            for item in _coerce_list(payload.get("sensitivity_notes"))
        ],
        "methodology": _build_methodology(payload, provenance),
	        "objective_coverage": objective_coverage,
	        "planned_vs_delivered": _build_planned_vs_delivered(payload),
        "objective_coverage_table_number": objective_coverage_table_number,
        "provenance_rows": _build_provenance_rows(provenance),
        "provenance_table_number": provenance_table_number,
        "token_usage": _coerce_int(payload.get("token_usage")),
        "cost_usd": _coerce_float(payload.get("cost_usd")),
        "limitations": [_coerce_text(item) for item in _coerce_list(payload.get("limitations"))],
	        "standards_alignment": _build_standards_alignment(payload),
	        "quote_evidence_blocks": _build_quote_evidence_blocks(payload),
        "manifest_json": json.dumps(
            _coerce_mapping(payload.get("manifest")),
            indent=2,
            sort_keys=True,
            default=_json_default,
        ),
        "toc": [
            {"id": "executive-findings", "label": "Executive findings"},
            {"id": "research-design", "label": "Research design"},
            {"id": "population-composition", "label": "Population composition"},
	            {"id": "question-distributions", "label": "Question distributions"},
	            {"id": "question-interpretation", "label": "Question interpretation and implications"},
	            {"id": "segment-comparisons", "label": "Segment comparisons"},
            {"id": "qualitative-themes", "label": "Qualitative themes and evidence"},
            {"id": "failures-sensitivity", "label": "Failures and sensitivity"},
            {"id": "methodology", "label": "Methodology"},
            {"id": "objective-coverage", "label": "Objective coverage"},
            {"id": "provenance", "label": "Provenance"},
            {"id": "limitations", "label": "Limitations"},
	            {"id": "standards-alignment-appendix", "label": "Standards-aligned disclosure appendix"},
	            {"id": "quote-evidence-appendix", "label": "Quote evidence appendix"},
	            {"id": "technical-appendix", "label": "Technical appendix"},
        ],
    }


def _render_charts(questions: list[dict[str, Any]], output_dir: Path) -> list[Path]:
    files: list[Path] = []
    for question in questions:
        if not question["chart_labels"]:
            question["chart_path"] = ""
            continue
        chart_question = {
            "question_type": question.get("question_type"),
            "labels": question.get("chart_labels"),
        }
        display_labels = _chart_labels(chart_question)
        values = [_coerce_int(value) for value in _coerce_list(question.get("chart_values"))]
        path = output_dir / f"figure-{question['figure_number']:02d}-{_slugify(question['question_id'])}.png"
        figure, axis = plt.subplots(figsize=(8.4, 4.8), dpi=144)
        figure.patch.set_facecolor("white")
        axis.set_facecolor("white")
        wrapped_labels = [_wrap_tick_label(label) for label in display_labels]
        chart_family = _coerce_text(question.get("chart_family"))
        if chart_family == "question_themes":
            bars = axis.barh(wrapped_labels, values, color="#1f5f78", height=0.62)
            axis.set_xlabel("Theme mentions", fontsize=9)
        else:
            bars = axis.bar(wrapped_labels, values, color="#1f5f78", width=0.62)
            axis.set_ylabel("Synthetic responses", fontsize=9)
        axis.set_title(_chart_title(question), loc="left", fontsize=11, pad=12)
        axis.yaxis.set_major_locator(MaxNLocator(integer=True))
        axis.grid(axis="y", color="#d7dee3", linewidth=0.8)
        axis.set_axisbelow(True)
        for spine in ("top", "right"):
            axis.spines[spine].set_visible(False)
        axis.margins(x=0.05)
        for bar, value in zip(bars, values):
            if chart_family == "question_themes":
                axis.text(
                    bar.get_width() + 0.03,
                    bar.get_y() + bar.get_height() / 2,
                    str(value),
                    ha="left",
                    va="center",
                    fontsize=8,
                    color="#102a43",
                )
            else:
                axis.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + 0.03,
                    str(value),
                    ha="center",
                    va="bottom",
                    fontsize=8,
                    color="#102a43",
                )
        axis.tick_params(axis="x", labelrotation=0, labelsize=8, pad=8)
        axis.tick_params(axis="y", labelsize=8)
        figure.tight_layout()
        figure.savefig(path, metadata={"Software": "Synthetix"}, dpi=120)
        plt.close(figure)
        question["chart_path"] = path.resolve().as_uri()
        files.append(path)
    return files


def _render_html(view: dict[str, Any]) -> str:
    environment = Environment(autoescape=select_autoescape(["html", "xml"]))
    template = environment.from_string(REPORT_TEMPLATE)
    return template.render(view=view, stylesheet_href=REPORT_STYLESHEET.resolve().as_uri())


def _load_weasyprint() -> tuple[Any, Any]:
    try:
        from weasyprint import HTML, default_url_fetcher
    except (ImportError, OSError) as exc:
        raise RuntimeError(
            "WeasyPrint is required to render report PDFs; install WeasyPrint for production output."
        ) from exc
    return HTML, default_url_fetcher


def _render_pdf(html: str, pdf_path: Path, base_url: str) -> None:
    HTML, _ = _load_weasyprint()

    try:
        HTML(string=html, base_url=base_url, url_fetcher=_safe_url_fetcher).write_pdf(
            pdf_path,
            pdf_variant="pdf/a-2b",
            pdf_tags=True,
        )
    except OSError as exc:
        raise RuntimeError(
            "WeasyPrint is required to render report PDFs; native dependencies are unavailable."
        ) from exc


def render_report(report: ReportModel, output_dir: Path) -> ReportArtifacts:
    output_dir.mkdir(parents=True, exist_ok=True)
    payload = _report_payload(report)
    view = _build_report_view(payload)
    json_path = output_dir / "report.json"
    html_path = output_dir / "report.html"
    pdf_path = output_dir / "report.pdf"
    checksums_path = output_dir / "checksums.json"

    json_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=_json_default),
        encoding="utf-8",
    )
    chart_files = _render_charts(view["questions"], output_dir)
    html = _render_html(view)
    html_path.write_text(html, encoding="utf-8")
    _render_pdf(html, pdf_path, output_dir.resolve().as_uri())

    files = [json_path, html_path, pdf_path, *chart_files]
    checksums = {path.name: _checksum(path) for path in files}
    checksums_path.write_text(json.dumps(checksums, indent=2, sort_keys=True), encoding="utf-8")
    return ReportArtifacts(
        json_path=json_path,
        html_path=html_path,
        pdf_path=pdf_path,
        checksums_path=checksums_path,
        chart_paths=chart_files,
    )
