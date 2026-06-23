from pathlib import Path

import pandas as pd

from rf_cnpj.core.models import ProcessingOptions, RunConfig, Scope
from rf_cnpj.core.processor import PipelineRunner


class FakeDownloader:
    def __init__(self):
        self.downloaded = []

    def download_month(self, month, options):
        self.downloaded.append((month, options))
        return [Path("Empresas0.zip")]


class FakeExtractor:
    def __init__(self):
        self.extracted = False

    def extract_month(self, month_dir, zip_files=None):
        self.extracted = True
        self.zip_files = zip_files
        return []


class FakeEngine:
    def __init__(self):
        self.calls = []

    def process(self, raw_dir, scope, options):
        self.calls.append((raw_dir, scope, options))
        return pd.DataFrame([{"CNPJ": "11.111.111/0001-91", "RAZAO_SOCIAL": "EMPRESA"}])


def test_pipeline_runner_downloads_extracts_processes_exports_and_cleans(tmp_path):
    downloader = FakeDownloader()
    extractor = FakeExtractor()
    engine = FakeEngine()
    raw_month = tmp_path / "dados" / "receita_federal" / "2026-02"
    raw_month.mkdir(parents=True)
    (raw_month / "empresas0.csv").write_text("csv")
    (raw_month / "empresas0.zip").write_text("zip")

    config = RunConfig(
        month="2026-02",
        data_dir=tmp_path / "dados",
        output_dir=tmp_path / "saida",
        scope=Scope(type="uf", uf="PE"),
        options=ProcessingOptions(include_socios=False),
        output_name="empresas_pe",
        cleanup_mode="extracted",
    )
    runner = PipelineRunner(downloader=downloader, extractor=extractor, engine=engine)

    result = runner.run(config)

    assert downloader.downloaded[0][0] == "2026-02"
    assert extractor.extracted is True
    assert extractor.zip_files == [Path("Empresas0.zip")]
    assert engine.calls[0][0] == raw_month
    assert result.rows == 1
    assert result.csv_path.exists()
    assert result.parquet_path.exists()
    assert (raw_month / "empresas0.zip").exists()
    assert not (raw_month / "empresas0.csv").exists()


def test_pipeline_runner_emits_lifecycle_events(tmp_path):
    downloader = FakeDownloader()
    extractor = FakeExtractor()
    engine = FakeEngine()
    raw_month = tmp_path / "dados" / "receita_federal" / "2026-02"
    raw_month.mkdir(parents=True)
    (raw_month / "empresas0.csv").write_text("csv")
    (raw_month / "empresas0.zip").write_text("zip")
    events = []
    config = RunConfig(
        month="2026-02",
        data_dir=tmp_path / "dados",
        output_dir=tmp_path / "saida",
        scope=Scope(type="uf", uf="PE"),
        options=ProcessingOptions(include_socios=False),
        output_name="empresas_pe",
        cleanup_mode="extracted",
    )
    runner = PipelineRunner(downloader=downloader, extractor=extractor, engine=engine)

    runner.run(config, emit=events.append)

    assert [event["type"] for event in events] == [
        "pipeline_start",
        "download_phase_start",
        "download_phase_done",
        "extract_phase_start",
        "extract_phase_done",
        "process_start",
        "process_done",
        "export_start",
        "export_done",
        "cleanup_start",
        "cleanup_done",
        "done",
    ]
    assert events[0]["message"] == "Iniciando pipeline RF CNPJ para 2026-02"
    assert events[-1]["data"]["rows"] == 1
