"""FastAPI app for controlling the local RF CNPJ pipeline."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Callable, Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from rf_cnpj import __version__
from rf_cnpj.api.jobs import TERMINAL_EVENTS, RunJobManager
from rf_cnpj.core.file_dialog import pick_directory
from rf_cnpj.core.month_discovery import MonthDiscovery
from rf_cnpj.core.municipios_rf import municipios_por_uf
from rf_cnpj.core.models import RunConfig, Scope
from rf_cnpj.core.processor import PipelineRunner
from rf_cnpj.core.ui_options import BRAZIL_STATES, TABLE_LABELS, options_from_labels


class RunRequest(BaseModel):
    month: str = Field(pattern=r"^\d{4}-\d{2}$")
    data_dir: str = "dados"
    output_dir: str = "saida"
    scope_type: Literal["uf", "municipio"]
    uf: str = Field(min_length=2, max_length=2)
    municipio: str | None = None
    tables: list[str] = Field(default_factory=list)
    cleanup_mode: Literal["none", "extracted", "all_raw"] = "extracted"
    output_name: str = "rf_cnpj"


class RunResponse(BaseModel):
    csv_path: str
    parquet_path: str
    rows: int


class RunJobResponse(BaseModel):
    run_id: str


class StateOption(BaseModel):
    value: str
    label: str


class OptionsResponse(BaseModel):
    tables: list[str]
    cleanup_modes: list[str]
    scope_types: list[Literal["uf", "municipio"]]
    months: list[str]
    states: list[StateOption]


class PickDirectoryRequest(BaseModel):
    initial_dir: str | None = None


class PickDirectoryResponse(BaseModel):
    path: str | None


class MunicipioOption(BaseModel):
    value: str
    label: str


def create_app(
    runner: PipelineRunner | None = None,
    month_discovery: MonthDiscovery | None = None,
    directory_picker: Callable[[str | None], str | None] | None = None,
    municipios_loader: Callable[[str, str], list[dict[str, str]]] | None = None,
) -> FastAPI:
    app = FastAPI(title="RF CNPJ API", version=__version__)
    pipeline_runner = runner or PipelineRunner()
    job_manager = RunJobManager(pipeline_runner)
    month_source = month_discovery or MonthDiscovery()
    choose_directory = directory_picker or pick_directory
    load_municipios = municipios_loader or municipios_por_uf

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "rf-cnpj-api", "version": __version__}

    @app.get("/options", response_model=OptionsResponse)
    def options() -> OptionsResponse:
        try:
            months = month_source.fetch_available_months()
        except Exception:
            months = []

        return OptionsResponse(
            tables=list(TABLE_LABELS.keys()),
            cleanup_modes=["extracted", "none", "all_raw"],
            scope_types=["uf", "municipio"],
            months=months,
            states=[StateOption(**state) for state in BRAZIL_STATES],
        )

    @app.post("/directories/pick", response_model=PickDirectoryResponse)
    def pick_directory_endpoint(request: PickDirectoryRequest) -> PickDirectoryResponse:
        return PickDirectoryResponse(path=choose_directory(request.initial_dir))

    @app.get("/municipios", response_model=list[MunicipioOption])
    def list_municipios(
        uf: str, data_dir: str = "dados"
    ) -> list[MunicipioOption]:
        matched = load_municipios(uf, data_dir)
        return [
            MunicipioOption(value=m["descricao"], label=f"{m['descricao']} (TOM {m['codigo']})")
            for m in matched
        ]

    @app.post("/runs", response_model=RunResponse)
    def run_pipeline(request: RunRequest) -> RunResponse:
        config = _run_config(request)
        result = pipeline_runner.run(config)
        return RunResponse(csv_path=result.csv_path.as_posix(), parquet_path=result.parquet_path.as_posix(), rows=result.rows)

    @app.post("/runs/jobs", response_model=RunJobResponse)
    def start_run_job(request: RunRequest) -> RunJobResponse:
        return RunJobResponse(run_id=job_manager.start(_run_config(request)))

    @app.get("/runs/{run_id}/events")
    async def run_events(run_id: str) -> StreamingResponse:
        job = job_manager.get(run_id)
        if job is None:
            raise HTTPException(status_code=404, detail="run not found")

        async def stream():
            while True:
                event = await asyncio.to_thread(job.events.get)
                if event is None:
                    break
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                if event["type"] in TERMINAL_EVENTS:
                    break

        return StreamingResponse(stream(), media_type="text/event-stream")

    return app


def _run_config(request: RunRequest) -> RunConfig:
    return RunConfig(
        month=request.month,
        data_dir=Path(request.data_dir),
        output_dir=Path(request.output_dir),
        scope=Scope(type=request.scope_type, uf=request.uf, municipio=request.municipio),
        options=options_from_labels(request.tables),
        output_name=request.output_name,
        cleanup_mode=request.cleanup_mode,
    )


app = create_app()
