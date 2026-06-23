"""High-level pipeline runner."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from rf_cnpj.engines.pandas_engine import PandasCNPJEngine

from .cleanup import cleanup_raw_files
from .downloader import DownloaderRF
from .events import EventEmitter, emit_event
from .extractor import MonthExtractor
from .models import ExportResult, ProcessingOptions, RunConfig, Scope
from .output import export_csv_and_parquet


class Downloader(Protocol):
    def download_month(self, month: str, options: ProcessingOptions) -> list[Path]: ...


class Extractor(Protocol):
    def extract_month(self, month_dir: Path, zip_files: list[Path] | None = None) -> list[Path]: ...


class Engine(Protocol):
    def process(self, raw_dir: Path, scope: Scope, options: ProcessingOptions): ...


class PipelineRunner:
    """Coordinates download, extraction, processing, export, and cleanup."""

    def __init__(self, downloader: Downloader | None = None, extractor: Extractor | None = None, engine: Engine | None = None):
        self.downloader = downloader
        self.extractor = extractor
        self.engine = engine or PandasCNPJEngine()

    def run(self, config: RunConfig, emit: EventEmitter | None = None) -> ExportResult:
        downloader = self.downloader or DownloaderRF(config.data_dir, emit=emit)
        extractor = self.extractor or MonthExtractor(emit=emit)
        raw_month_dir = Path(config.data_dir) / "receita_federal" / config.month

        try:
            emit_event(emit, "pipeline_start", f"Iniciando pipeline RF CNPJ para {config.month}")
            emit_event(emit, "download_phase_start", "Iniciando downloads da Receita Federal")
            downloaded = downloader.download_month(config.month, config.options)
            emit_event(emit, "download_phase_done", f"Downloads concluidos: {len(downloaded)} arquivos", level="success")
            emit_event(emit, "extract_phase_start", "Iniciando extracao dos arquivos ZIP")
            extractor.extract_month(raw_month_dir, zip_files=downloaded)
            emit_event(emit, "extract_phase_done", "Extracao concluida", level="success")
            emit_event(emit, "process_start", "Processando CSVs e cruzamentos")
            df = self.engine.process(raw_month_dir, config.scope, config.options)
            emit_event(emit, "process_done", f"Processamento concluido: {len(df)} registros", level="success", data={"rows": len(df)})
            emit_event(emit, "export_start", "Exportando CSV e Parquet")
            result = export_csv_and_parquet(df, config.output_dir, config.output_name)
            emit_event(
                emit,
                "export_done",
                "Exportacao concluida",
                level="success",
                data={"csv_path": result.csv_path.as_posix(), "parquet_path": result.parquet_path.as_posix(), "rows": result.rows},
            )
            emit_event(emit, "cleanup_start", f"Aplicando limpeza: {config.cleanup_mode}")
            cleanup_raw_files(raw_month_dir, config.cleanup_mode)
            emit_event(emit, "cleanup_done", "Limpeza concluida", level="success")
            emit_event(
                emit,
                "done",
                "Pipeline concluida",
                level="success",
                data={"csv_path": result.csv_path.as_posix(), "parquet_path": result.parquet_path.as_posix(), "rows": result.rows},
            )
            return result
        except Exception as exc:
            emit_event(emit, "error", f"Erro na pipeline: {exc}", level="error", data={"error": str(exc)})
            raise
