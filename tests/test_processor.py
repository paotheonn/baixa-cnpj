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


class PerUFEngine:
    """Returns one row per UF, tagged with the UF, so we can assert aggregation."""

    def __init__(self):
        self.calls = []

    def process(self, raw_dir, scope, options):
        self.calls.append(scope.uf)
        return pd.DataFrame([{"CNPJ": f"{scope.uf}-CNPJ", "UF": scope.uf}])


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


def _brasil_config(tmp_path):
    raw_month = tmp_path / "dados" / "receita_federal" / "2026-02"
    raw_month.mkdir(parents=True)
    return RunConfig(
        month="2026-02",
        data_dir=tmp_path / "dados",
        output_dir=tmp_path / "saida",
        scope=Scope(type="brasil"),
        options=ProcessingOptions(include_socios=False),
        output_name="rf_cnpj_2026_02_BR",
        cleanup_mode="none",
    )


def test_pipeline_runner_processes_all_ufs_for_brasil_scope(tmp_path):
    engine = PerUFEngine()
    config = _brasil_config(tmp_path)
    runner = PipelineRunner(downloader=FakeDownloader(), extractor=FakeExtractor(), engine=engine)

    result = runner.run(config)

    # All 27 UFs processed and aggregated into a single output.
    assert len(engine.calls) == 27
    assert result.rows == 27
    merged = pd.read_parquet(result.parquet_path)
    assert set(merged["UF"]) == set(engine.calls)
    # Temp parts and manifest cleaned up after merge.
    assert not (config.output_dir / "rf_cnpj_2026_02_BR.parts").exists()
    assert not (config.output_dir / "rf_cnpj_2026_02_BR.manifest.json").exists()


def test_pipeline_runner_resumes_brasil_scope_skipping_completed_ufs(tmp_path):
    from rf_cnpj.core.output import IncrementalUFExporter

    config = _brasil_config(tmp_path)
    # Pre-populate a checkpoint with one finished UF.
    exporter = IncrementalUFExporter(config.output_dir, config.output_name)
    exporter.write_uf("SP", pd.DataFrame([{"CNPJ": "SP-CNPJ", "UF": "SP"}]))

    engine = PerUFEngine()
    runner = PipelineRunner(downloader=FakeDownloader(), extractor=FakeExtractor(), engine=engine)

    result = runner.run(config)

    # SP is skipped; the other 26 UFs are processed.
    assert "SP" not in engine.calls
    assert len(engine.calls) == 26
    assert result.rows == 27
    assert set(pd.read_parquet(result.parquet_path)["UF"]) >= {"SP"}


def test_pipeline_runner_emits_uf_events_for_brasil_scope(tmp_path):
    engine = PerUFEngine()
    config = _brasil_config(tmp_path)
    events = []
    runner = PipelineRunner(downloader=FakeDownloader(), extractor=FakeExtractor(), engine=engine)

    runner.run(config, emit=events.append)

    types = [event["type"] for event in events]
    assert types.count("uf_start") == 27
    assert types.count("uf_done") == 27
    assert "done" in types
