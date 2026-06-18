from __future__ import annotations

import asyncio
import json
from pathlib import Path

import typer

from synthetix.application import RunService
from synthetix.benchmarking.frozen import EvaluationSplit, FrozenEvaluation
from synthetix.benchmarking.loop import BenchmarkLoop
from synthetix.benchmarking.predictions import DevelopmentPredictionEmitter
from synthetix.benchmarking.runtime import BenchmarkComparator
from synthetix.guardrails.preflight import estimate_run
from synthetix.ingestion.structured import load_blueprint
from synthetix.model_gateway.profiles import DEFAULT_PROFILES
from synthetix.orchestration.loop import OrchestratorLoop, VerificationResult
from synthetix.orchestration.quality_loop import QualityLoop, QualityTarget
from synthetix.reporting.models import ReportModel
from synthetix.reporting.renderer import render_report
from synthetix.settings import Settings


app = typer.Typer(
    name="synthetix",
    help="Synthetic scenario exploration with explicit scientific and cost guardrails.",
    no_args_is_help=True,
)


@app.command()
def validate(path: Path) -> None:
    """Validate a JSON or YAML SimulationBlueprint without model calls."""
    blueprint = load_blueprint(path)
    typer.echo(
        f"Valid blueprint: {blueprint.title} "
        f"({blueprint.population.size} personas, {len(blueprint.questions)} questions)"
    )
    typer.echo(f"SHA-256: {blueprint.content_hash()}")


@app.command()
def preflight(path: Path) -> None:
    """Estimate worst-case calls, tokens, and cost."""
    blueprint = load_blueprint(path)
    settings = Settings()
    profile = DEFAULT_PROFILES.get(blueprint.model.profile)
    estimate = estimate_run(blueprint, profile, settings.guardrail_limits())
    typer.echo(estimate.model_dump_json(indent=2))


@app.command("run")
def run_blueprint(
    path: Path,
    yes: bool = typer.Option(False, "--yes", "-y", help="Approve external transmission."),
) -> None:
    """Execute a validated blueprint through OpenRouter and render report artifacts."""
    blueprint = load_blueprint(path)
    settings = Settings()
    if not settings.openrouter_api_key:
        raise typer.BadParameter("Set SYNTHETIX_OPENROUTER_API_KEY before execution")
    profile = DEFAULT_PROFILES.get(blueprint.model.profile)
    estimate = estimate_run(blueprint, profile, settings.guardrail_limits())
    typer.echo(estimate.model_dump_json(indent=2))
    if not yes and not typer.confirm("Transmit prompts to the configured OpenRouter provider?"):
        raise typer.Abort()

    async def execute() -> str:
        service = RunService(settings)
        await service.startup()
        try:
            import hashlib

            source_hash = hashlib.sha256(path.read_bytes()).hexdigest()
            run_id = await service.create_draft(
                blueprint, source_hashes={path.name: source_hash}
            )
            await service.approve(run_id)
            artifacts = await service.execute(run_id)
            return str(artifacts.pdf_path)
        finally:
            await service.shutdown()

    pdf_path = asyncio.run(execute())
    typer.echo(f"Report: {pdf_path}")


@app.command()
def demo_report(
    output: Path = typer.Argument(Path("data/demo-report")),
) -> None:
    """Generate deterministic report artifacts without calling a model."""
    artifacts = render_report(ReportModel.example(), output)
    typer.echo(f"Report: {artifacts.pdf_path}")


@app.command()
def serve(
    host: str = "127.0.0.1",
    port: int = 8000,
) -> None:
    """Start the minimal local web interface."""
    import uvicorn

    uvicorn.run("synthetix.web.app:app", host=host, port=port, reload=False)


@app.command("benchmark-loop-init")
def benchmark_loop_init(
    state: Path = typer.Option(
        Path("data/benchmark-loop-state.json"),
        help="Path to the persisted benchmark loop state file.",
    ),
) -> None:
    """Initialize the persistent benchmark loop state from repo manifests."""
    loop = BenchmarkLoop.for_workspace(Path.cwd(), state_path=state)
    typer.echo(loop.state.model_dump_json(indent=2))


@app.command("benchmark-loop-next")
def benchmark_loop_next(
    state: Path = typer.Option(
        Path("data/benchmark-loop-state.json"),
        help="Path to the persisted benchmark loop state file.",
    ),
) -> None:
    """Show the next benchmark-loop task packet."""
    loop = BenchmarkLoop.for_workspace(Path.cwd(), state_path=state)
    typer.echo(loop.next_packet().model_dump_json(indent=2))


@app.command("benchmark-loop-complete")
def benchmark_loop_complete(
    task_id: str = typer.Argument(..., help="Completed benchmark-loop task identifier."),
    state: Path = typer.Option(
        Path("data/benchmark-loop-state.json"),
        help="Path to the persisted benchmark loop state file.",
    ),
) -> None:
    """Advance the benchmark loop after completing the current task."""
    loop = BenchmarkLoop.for_workspace(Path.cwd(), state_path=state)
    updated = loop.complete(task_id)
    typer.echo(updated.model_dump_json(indent=2))


@app.command("benchmark-compare")
def benchmark_compare(
    fixture: Path = typer.Argument(..., help="Path to the benchmark fixture with locked actual targets."),
    predicted: Path = typer.Argument(..., help="Path to the predicted metric payload."),
    output: Path = typer.Option(
        Path("data/benchmark-results/development/comparison.json"),
        "--output",
        help="Path to write the actual-vs-predicted comparison report.",
    ),
) -> None:
    """Compare predicted benchmark outputs against locked actual targets."""
    report = BenchmarkComparator.compare_files(
        fixture_path=fixture,
        predicted_path=predicted,
        output_path=output,
    )
    typer.echo(report.model_dump_json(indent=2))


@app.command("benchmark-compare-development")
def benchmark_compare_development(
    fixtures: Path = typer.Option(
        Path("research/benchmark_program/development"),
        "--fixtures",
        help="Directory containing development benchmark fixtures.",
    ),
    predicted_dir: Path = typer.Option(
        Path("data/benchmark-predictions/development"),
        "--predicted-dir",
        help="Directory containing predicted metric payloads keyed by fixture filename.",
    ),
    output_dir: Path = typer.Option(
        Path("data/benchmark-results/development"),
        "--output-dir",
        help="Directory where comparison reports and summary.json are written.",
    ),
) -> None:
    """Batch-compare development fixtures against predicted metric outputs."""
    summary = BenchmarkComparator.compare_directory(
        fixture_dir=fixtures,
        predicted_dir=predicted_dir,
        output_dir=output_dir,
    )
    typer.echo(json.dumps(summary, indent=2))


@app.command("benchmark-predict-development")
def benchmark_predict_development(
    fixtures: Path = typer.Option(
        Path("research/benchmark_program/development"),
        "--fixtures",
        help="Directory containing development benchmark fixtures.",
    ),
    output_dir: Path = typer.Option(
        Path("data/benchmark-predictions/development"),
        "--output-dir",
        help="Directory where predicted metric payloads are written.",
    ),
) -> None:
    """Emit conservative development benchmark prediction payloads."""
    summary = DevelopmentPredictionEmitter.emit_directory(
        fixture_dir=fixtures,
        output_dir=output_dir,
    )
    typer.echo(json.dumps(summary, indent=2))


@app.command("benchmark-freeze")
def benchmark_freeze(
    split: EvaluationSplit = typer.Argument(..., help="Evaluation split to freeze: validation or holdout."),
    output: Path | None = typer.Option(
        None,
        "--output",
        help="Path to write the immutable freeze manifest.",
    ),
) -> None:
    """Freeze validation or holdout artifacts before one-shot evaluation."""
    evaluator = FrozenEvaluation.for_workspace(Path.cwd())
    output_path = output or Path(f"data/frozen-evaluations/{split}/freeze-manifest.json")
    manifest = evaluator.freeze(split=split, output_path=output_path)
    typer.echo(manifest.model_dump_json(indent=2))


@app.command("benchmark-predict-frozen")
def benchmark_predict_frozen(
    split: EvaluationSplit = typer.Argument(..., help="Frozen split to predict: validation or holdout."),
    output_dir: Path | None = typer.Option(
        None,
        "--output-dir",
        help="Directory where predicted metric payloads are written.",
    ),
) -> None:
    """Emit predictions for a frozen validation or holdout split."""
    evaluator = FrozenEvaluation.for_workspace(Path.cwd())
    prediction_dir = output_dir or Path(f"data/benchmark-predictions/{split}")
    summary = evaluator.emit_predictions(split=split, output_dir=prediction_dir)
    typer.echo(json.dumps(summary, indent=2))


@app.command("benchmark-evaluate-frozen")
def benchmark_evaluate_frozen(
    split: EvaluationSplit = typer.Argument(..., help="Frozen split to evaluate: validation or holdout."),
    predicted_dir: Path | None = typer.Option(
        None,
        "--predicted-dir",
        help="Directory containing predicted metric payloads.",
    ),
    output_dir: Path | None = typer.Option(
        None,
        "--output-dir",
        help="Directory where comparison reports and summary.json are written.",
    ),
    quality_output: Path | None = typer.Option(
        None,
        "--quality-output",
        help="Path to write the frozen quality summary.",
    ),
    min_average_score: float = typer.Option(0.8, "--min-average-score"),
    min_fixture_score: float = typer.Option(0.7, "--min-fixture-score"),
) -> None:
    """Compare frozen predictions and write an honest quality-gate summary."""
    evaluator = FrozenEvaluation.for_workspace(Path.cwd())
    prediction_dir = predicted_dir or Path(f"data/benchmark-predictions/{split}")
    comparison_dir = output_dir or Path(f"data/benchmark-results/{split}")
    quality_path = quality_output or Path(f"data/frozen-evaluations/{split}/quality-summary.json")
    quality = evaluator.evaluate(
        split=split,
        predicted_dir=prediction_dir,
        output_dir=comparison_dir,
        quality_output=quality_path,
        min_average_score=min_average_score,
        min_fixture_score=min_fixture_score,
    )
    typer.echo(quality.model_dump_json(indent=2))


@app.command("orchestrator-next")
def orchestrator_next(
    state: Path = typer.Option(
        Path("data/orchestrator-loop-state.json"),
        help="Path to the persisted orchestrator state file.",
    ),
) -> None:
    """Show the next gated agent task."""
    loop = OrchestratorLoop.for_workspace(Path.cwd(), state_path=state)
    typer.echo(loop.next_task().model_dump_json(indent=2))


@app.command("orchestrator-record")
def orchestrator_record(
    task_id: str = typer.Argument(..., help="Task identifier to record verification for."),
    state: Path = typer.Option(
        Path("data/orchestrator-loop-state.json"),
        help="Path to the persisted orchestrator state file.",
    ),
    failed: bool = typer.Option(False, "--failed", help="Record the verification as failed."),
    note: list[str] = typer.Option([], "--note", help="Review note to persist."),
    artifact: list[str] = typer.Option([], "--artifact", help="Accepted artifact path."),
) -> None:
    """Record verification for the active orchestrator task."""
    loop = OrchestratorLoop.for_workspace(Path.cwd(), state_path=state)
    task = loop.next_task()
    if task.task_id != task_id:
        raise typer.BadParameter(f"Expected active task '{task.task_id}'")
    checks = {check: not failed for check in task.acceptance_checks}
    updated = loop.record_verification(
        task_id,
        VerificationResult(
            passed=not failed,
            checks=checks,
            review_notes=note,
            artifact_paths=artifact,
        ),
    )
    typer.echo(updated.model_dump_json(indent=2))


@app.command("orchestrator-run")
def orchestrator_run(
    state: Path = typer.Option(
        Path("data/orchestrator-loop-state.json"),
        help="Path to the persisted orchestrator state file.",
    ),
    progress: Path = typer.Option(
        Path("docs/progress/orchestrator-progress.md"),
        help="Path to append orchestrator progress notes.",
    ),
    max_steps: int = typer.Option(20, "--max-steps", help="Maximum tasks to process."),
) -> None:
    """Run the local orchestrator until a gate blocks or all possible tasks are accepted."""
    loop = OrchestratorLoop.for_workspace(
        Path.cwd(),
        state_path=state,
        progress_path=progress,
    )
    result = loop.run_until_blocked(max_steps=max_steps)
    typer.echo(result.model_dump_json(indent=2))


@app.command("quality-loop-run")
def quality_loop_run(
    workspace: Path = typer.Option(Path.cwd(), "--workspace", help="Workspace root to evaluate."),
    state: Path = typer.Option(
        Path("data/quality-loop-state.json"),
        help="Path to the persisted quality loop state file.",
    ),
    progress: Path = typer.Option(
        Path("docs/progress/quality-loop-progress.md"),
        help="Path to append quality loop progress notes.",
    ),
    min_average_score: float = typer.Option(
        0.8,
        "--min-average-score",
        help="Minimum average development benchmark score.",
    ),
    min_fixture_score: float = typer.Option(
        0.7,
        "--min-fixture-score",
        help="Minimum score for every development benchmark fixture.",
    ),
    require_report_artifacts: bool = typer.Option(
        True,
        "--require-report-artifacts/--no-require-report-artifacts",
        help="Require professional report artifacts before passing the quality loop.",
    ),
) -> None:
    """Evaluate product quality and emit the next task until desired results are met."""
    loop = QualityLoop.for_workspace(
        workspace,
        state_path=state,
        progress_path=progress,
        target=QualityTarget(
            min_average_score=min_average_score,
            min_fixture_score=min_fixture_score,
            require_report_artifacts=require_report_artifacts,
        ),
    )
    typer.echo(loop.run_once().model_dump_json(indent=2))


if __name__ == "__main__":
    app()
