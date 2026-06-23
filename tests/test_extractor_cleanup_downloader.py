import zipfile
from io import BytesIO
from pathlib import Path

import pytest

from rf_cnpj.core.cleanup import cleanup_raw_files
from rf_cnpj.core.downloader import DownloaderRF, planned_download_files
from rf_cnpj.core.extractor import MonthExtractor, extract_zip_safely
from rf_cnpj.core.models import ProcessingOptions


def test_extract_zip_safely_normalizes_output_name(tmp_path):
    zip_path = tmp_path / "Empresas0.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("K3241.K03200Y0.D40113.EMPRECSV", "11111111;EMPRESA")

    extracted = extract_zip_safely(zip_path, tmp_path)

    assert extracted == [tmp_path / "empresas0.csv"]
    assert (tmp_path / "empresas0.csv").read_text(encoding="latin-1") == "11111111;EMPRESA"


def test_extract_zip_safely_streams_member_copy(tmp_path, monkeypatch):
    zip_path = tmp_path / "Empresas0.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("K3241.K03200Y0.D40113.EMPRECSV", "11111111;EMPRESA")
    calls = []

    def fake_copyfileobj(source, target, length=0):
        calls.append(length)
        target.write(source.read(4))
        target.write(source.read())

    monkeypatch.setattr("shutil.copyfileobj", fake_copyfileobj)

    extract_zip_safely(zip_path, tmp_path)

    assert calls


def test_extract_zip_safely_rejects_path_traversal(tmp_path):
    zip_path = tmp_path / "Empresas0.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("../evil.csv", "bad")

    with pytest.raises(ValueError, match="unsafe"):
        extract_zip_safely(zip_path, tmp_path)


def test_planned_download_files_includes_required_and_selected_tables():
    files = planned_download_files(ProcessingOptions(include_socios=True, include_simples=False))

    assert "Estabelecimentos0.zip" in files
    assert "Empresas0.zip" in files
    assert "Municipios.zip" in files
    assert "Socios0.zip" in files
    assert "Simples.zip" not in files


def test_cleanup_extracted_keeps_zip_files(tmp_path):
    raw_dir = tmp_path / "2026-02"
    raw_dir.mkdir()
    (raw_dir / "empresas0.zip").write_text("zip")
    (raw_dir / "empresas0.csv").write_text("csv")

    cleanup_raw_files(raw_dir, mode="extracted")

    assert (raw_dir / "empresas0.zip").exists()
    assert not (raw_dir / "empresas0.csv").exists()


def test_cleanup_all_raw_removes_directory(tmp_path):
    raw_dir = tmp_path / "2026-02"
    raw_dir.mkdir()
    (raw_dir / "empresas0.zip").write_text("zip")

    cleanup_raw_files(raw_dir, mode="all_raw")

    assert not raw_dir.exists()


class FailingResponse:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def raise_for_status(self):
        return None

    def iter_content(self, chunk_size):
        yield b"partial"
        raise RuntimeError("connection lost")


class FailingSession:
    headers = {}

    def get(self, *args, **kwargs):
        return FailingResponse()


def test_downloader_removes_partial_file_after_failure(tmp_path):
    downloader = DownloaderRF(tmp_path, session=FailingSession())

    with pytest.raises(RuntimeError, match="connection lost"):
        downloader.download_file("2026-02", "Empresas0.zip")

    month_dir = tmp_path / "receita_federal" / "2026-02"
    assert not (month_dir / "Empresas0.zip").exists()
    assert not (month_dir / "Empresas0.zip.part").exists()


class SuccessfulResponse:
    def __init__(self, payload: bytes):
        self.payload = payload
        self.headers = {"content-length": str(len(payload))}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def raise_for_status(self):
        return None

    def iter_content(self, chunk_size):
        yield self.payload


class SuccessfulSession:
    headers = {}

    def __init__(self, payload: bytes):
        self.payload = payload
        self.calls = 0

    def get(self, *args, **kwargs):
        self.calls += 1
        return SuccessfulResponse(self.payload)


def valid_zip_payload() -> bytes:
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr("data.csv", "ok")
    return buffer.getvalue()


def test_downloader_redownloads_existing_invalid_zip(tmp_path):
    month_dir = tmp_path / "receita_federal" / "2026-02"
    month_dir.mkdir(parents=True)
    target = month_dir / "Empresas0.zip"
    target.write_text("partial")
    session = SuccessfulSession(valid_zip_payload())
    downloader = DownloaderRF(tmp_path, session=session)

    downloader.download_file("2026-02", "Empresas0.zip")

    assert session.calls == 1
    assert zipfile.is_zipfile(target)


def test_downloader_rejects_new_invalid_zip_payload(tmp_path):
    session = SuccessfulSession(b"not a zip")
    downloader = DownloaderRF(tmp_path, session=session)

    with pytest.raises(zipfile.BadZipFile):
        downloader.download_file("2026-02", "Empresas0.zip")

    month_dir = tmp_path / "receita_federal" / "2026-02"
    assert not (month_dir / "Empresas0.zip").exists()
    assert not (month_dir / "Empresas0.zip.part").exists()


def test_downloader_emits_download_progress_events(tmp_path):
    payload = valid_zip_payload()
    session = SuccessfulSession(payload)
    events = []
    downloader = DownloaderRF(tmp_path, session=session, emit=events.append)

    downloader.download_file("2026-02", "Empresas0.zip")

    event_types = [event["type"] for event in events]
    assert event_types[0] == "download_start"
    assert "download_progress" in event_types
    assert event_types[-1] == "download_done"
    progress = next(event for event in events if event["type"] == "download_progress")
    assert progress["data"]["filename"] == "Empresas0.zip"
    assert progress["data"]["downloaded_bytes"] == len(payload)
    assert progress["data"]["total_bytes"] == len(payload)
    assert "Empresas0.zip" in progress["message"]


def test_month_extractor_extracts_only_selected_zip_files(tmp_path):
    empresas_zip = tmp_path / "Empresas0.zip"
    socios_zip = tmp_path / "Socios0.zip"
    with zipfile.ZipFile(empresas_zip, "w") as zf:
        zf.writestr("empresas", "empresa")
    with zipfile.ZipFile(socios_zip, "w") as zf:
        zf.writestr("socios", "socio")

    extracted = MonthExtractor().extract_month(tmp_path, zip_files=[empresas_zip])

    assert extracted == [tmp_path / "empresas0.csv"]
    assert (tmp_path / "empresas0.csv").exists()
    assert not (tmp_path / "socios0.csv").exists()


def test_month_extractor_emits_extract_events(tmp_path):
    empresas_zip = tmp_path / "Empresas0.zip"
    with zipfile.ZipFile(empresas_zip, "w") as zf:
        zf.writestr("empresas", "empresa")
    events = []

    MonthExtractor(emit=events.append).extract_month(tmp_path, zip_files=[empresas_zip])

    assert [event["type"] for event in events] == ["extract_start", "extract_done"]
    assert events[0]["data"]["filename"] == "Empresas0.zip"
    assert events[1]["data"]["extracted_files"] == ["empresas0.csv"]
