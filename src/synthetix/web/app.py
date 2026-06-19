from __future__ import annotations

import asyncio
import json
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from synthetix.application import RunService
from synthetix.ingestion.documents import DocumentLimits, UnsafeDocument, extract_document
from synthetix.ingestion.questionnaire import parse_questionnaire
from synthetix.ingestion.structured import parse_blueprint_text
from synthetix.guardrails.preflight import GuardrailViolation
from synthetix.model_gateway.openrouter import OpenRouterGateway
from synthetix.model_gateway.profiles import DEFAULT_PROFILES
from synthetix.reporting.models import ReportModel
from synthetix.settings import Settings


PACKAGE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=PACKAGE_DIR / "templates")


def create_app(*, data_dir: Path | None = None) -> FastAPI:
    settings = Settings()
    if data_dir is not None:
        settings.data_dir = data_dir
        settings.database_url = f"sqlite+aiosqlite:///{data_dir / 'synthetix.db'}"
    service = RunService(settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        await service.startup()
        yield
        await service.shutdown()

    app = FastAPI(title="Synthetix", version="0.1.0", lifespan=lifespan)
    app.state.service = service
    app.mount("/static", StaticFiles(directory=PACKAGE_DIR / "static"), name="static")

    @app.get("/", response_class=HTMLResponse)
    async def new_run(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            request=request,
            name="new_run.html",
            context={"profiles": DEFAULT_PROFILES.list()},
        )

    @app.post("/ingest")
    async def ingest(
        request: Request,
        file: UploadFile = File(...),
        confirm_transmission: bool = Form(False),
    ) -> HTMLResponse:
        filename = Path(file.filename or "upload").name
        suffix = Path(filename).suffix.lower()
        content = await file.read(settings.max_upload_bytes + 1)
        if len(content) > settings.max_upload_bytes:
            raise HTTPException(413, "Upload exceeds configured size limit")
        source_hashes: dict[str, str] = {}
        try:
            if suffix in {".json", ".yaml", ".yml"}:
                blueprint = parse_blueprint_text(content.decode("utf-8"), suffix)
                import hashlib

                source_hashes[filename] = hashlib.sha256(content).hexdigest()
            elif suffix in {".txt", ".md", ".pdf"}:
                if not confirm_transmission:
                    raise HTTPException(
                        400,
                        "Confirm external transmission before model-assisted document parsing",
                    )
                if not settings.openrouter_api_key:
                    raise HTTPException(
                        503,
                        "Configure SYNTHETIX_OPENROUTER_API_KEY for document parsing",
                    )
                with tempfile.TemporaryDirectory() as directory:
                    path = Path(directory) / filename
                    path.write_bytes(content)
                    extracted = extract_document(
                        path,
                        DocumentLimits(settings.max_upload_bytes, settings.max_pdf_pages),
                    )
                profile = DEFAULT_PROFILES.get("openrouter-default")
                gateway = OpenRouterGateway(settings.openrouter_api_key)
                try:
                    blueprint = await parse_questionnaire(extracted.text, gateway, profile)
                finally:
                    await gateway.close()
                source_hashes[filename] = extracted.sha256
            else:
                raise HTTPException(415, "Supported files: JSON, YAML, PDF, Markdown, text")
        except UnicodeDecodeError as exc:
            raise HTTPException(400, "Structured files must use UTF-8") from exc
        except UnsafeDocument as exc:
            raise HTTPException(400, str(exc)) from exc
        except (ValueError, GuardrailViolation) as exc:
            raise HTTPException(400, str(exc)) from exc
        try:
            run_id = await service.create_draft(blueprint, source_hashes=source_hashes)
        except (ValueError, GuardrailViolation) as exc:
            raise HTTPException(400, str(exc)) from exc
        return templates.TemplateResponse(
            request=request,
            name="review.html",
            context={"run_id": run_id, "blueprint": blueprint},
        )

    @app.get("/runs/{run_id}/preflight", response_class=HTMLResponse)
    async def preflight(request: Request, run_id: str) -> HTMLResponse:
        if run_id == "demo":
            return templates.TemplateResponse(
                request=request,
                name="preflight.html",
                context={
                    "run_id": run_id,
                    "estimate": {
                        "projected_calls": 10,
                        "max_tokens": 8_000,
                        "max_cost_usd": 0.05,
                        "warnings": ["Demo estimate only."],
                    },
                },
            )
        try:
            estimate = await service.preflight(run_id)
        except Exception as exc:
            raise HTTPException(400, str(exc)) from exc
        return templates.TemplateResponse(
            request=request,
            name="preflight.html",
            context={"run_id": run_id, "estimate": estimate},
        )

    @app.post("/runs/{run_id}/approve")
    async def approve(run_id: str) -> RedirectResponse:
        if not settings.openrouter_api_key:
            raise HTTPException(
                503,
                "Configure SYNTHETIX_OPENROUTER_API_KEY before approving execution",
            )
        await service.approve(run_id)
        task = asyncio.create_task(service.execute(run_id))
        service.tasks[run_id] = task
        task.add_done_callback(lambda completed: service.tasks.pop(run_id, None))
        return RedirectResponse(f"/runs/{run_id}/status", status_code=303)

    @app.get("/runs/{run_id}/status", response_class=HTMLResponse)
    async def status(request: Request, run_id: str) -> HTMLResponse:
        progress = (
            {"status": "completed", "completed": 10, "total": 10, "cost_usd": 0.05}
            if run_id == "demo"
            else service.progress.get(run_id, {"status": "unknown"})
        )
        return templates.TemplateResponse(
            request=request,
            name="status.html",
            context={"run_id": run_id, "progress": progress},
        )

    @app.get("/runs/{run_id}/events")
    async def events(run_id: str) -> StreamingResponse:
        async def stream() -> AsyncIterator[str]:
            previous = ""
            while True:
                progress = service.progress.get(run_id, {"status": "unknown"})
                payload = json.dumps(progress, sort_keys=True)
                if payload != previous:
                    yield f"data: {payload}\n\n"
                    previous = payload
                if progress.get("status") in {"completed", "cancelled", "failed"}:
                    break
                await asyncio.sleep(1)

        return StreamingResponse(stream(), media_type="text/event-stream")

    @app.post("/runs/{run_id}/cancel")
    async def cancel(run_id: str) -> RedirectResponse:
        service.cancel(run_id)
        return RedirectResponse(f"/runs/{run_id}/status", status_code=303)

    @app.get("/runs/{run_id}/results", response_class=HTMLResponse)
    async def results(request: Request, run_id: str) -> HTMLResponse:
        report_path = service.report_path(run_id, "report.json")
        if run_id == "demo":
            report = ReportModel.example()
        elif report_path.exists():
            report = ReportModel.model_validate_json(report_path.read_text(encoding="utf-8"))
        else:
            raise HTTPException(404, "Report is not ready")
        return templates.TemplateResponse(
            request=request,
            name="results.html",
            context={"run_id": run_id, "report": report},
        )

    @app.get("/runs/{run_id}/report.pdf")
    async def download_pdf(run_id: str) -> FileResponse:
        path = service.report_path(run_id, "report.pdf")
        if not path.exists():
            raise HTTPException(404, "Report is not ready")
        return FileResponse(path, media_type="application/pdf", filename=f"{run_id}-report.pdf")

    return app


app = create_app()
