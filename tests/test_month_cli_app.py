import sys
from pathlib import Path

from rf_cnpj.cli import main
from rf_cnpj.core.month_discovery import parse_months_from_webdav
from rf_cnpj.core.ui_options import build_output_name, options_from_labels


def test_parse_months_from_webdav_sorts_valid_months():
    xml = b"""
    <d:multistatus xmlns:d="DAV:">
      <d:response><d:href>/public.php/webdav/2026-02/</d:href></d:response>
      <d:response><d:href>/public.php/webdav/not-a-month/</d:href></d:response>
      <d:response><d:href>/public.php/webdav/2025-12/</d:href></d:response>
      <d:response><d:href>/public.php/webdav/2026-13/</d:href></d:response>
    </d:multistatus>
    """

    assert parse_months_from_webdav(xml) == ["2025-12", "2026-02"]


def test_cli_web_invokes_next_dev(monkeypatch):
    calls = []

    def fake_run(cmd, check=False):
        calls.append((cmd, check))
        class Result:
            returncode = 0
        return Result()

    monkeypatch.setattr("subprocess.run", fake_run)

    assert main(["web"]) == 0
    cmd, check = calls[0]
    assert cmd[1:3] == ["--prefix", str(Path.cwd() / "web")]
    assert cmd[3:] == ["run", "dev"]
    assert check is False


def test_cli_web_uses_cmd_shim_on_windows(monkeypatch):
    calls = []

    def fake_run(cmd, check=False):
        calls.append((cmd, check))

        class Result:
            returncode = 0

        return Result()

    monkeypatch.setattr("rf_cnpj.cli.sys.platform", "win32")
    monkeypatch.setattr("subprocess.run", fake_run)

    assert main(["web"]) == 0
    cmd, _ = calls[0]
    assert cmd[0] == "npm.cmd"


def test_cli_api_runs_uvicorn_without_reload_by_default(monkeypatch):
    calls = []

    def fake_run(cmd, check=False):
        calls.append((cmd, check))

        class Result:
            returncode = 0

        return Result()

    monkeypatch.setattr("subprocess.run", fake_run)

    assert main(["api"]) == 0
    cmd, check = calls[0]
    assert cmd == [sys.executable, "-m", "uvicorn", "rf_cnpj.api.app:app"]
    assert "--reload" not in cmd
    assert check is False


def test_cli_run_brasil_builds_config_and_returns_zero(monkeypatch):
    captured = {}

    class FakeRunner:
        def run(self, config, emit=None):
            captured["config"] = config
            if emit:
                emit({"type": "done", "level": "success", "message": "ok", "timestamp": "2026-02-01T10:00:00+00:00"})
            return None

    monkeypatch.setattr("rf_cnpj.core.processor.PipelineRunner", FakeRunner)

    exit_code = main(["run", "--scope", "brasil", "--month", "2026-05"])

    assert exit_code == 0
    config = captured["config"]
    assert config.scope.type == "brasil"
    assert config.scope.uf == ""
    assert config.month == "2026-05"
    assert config.output_name == "rf_cnpj_2026_05_br"
    # Default cleanup and all tables selected.
    assert config.cleanup_mode == "extracted"
    assert config.options.include_socios is True


def test_cli_run_uf_uses_uf_and_selected_tables(monkeypatch):
    captured = {}

    class FakeRunner:
        def run(self, config, emit=None):
            captured["config"] = config
            return None

    monkeypatch.setattr("rf_cnpj.core.processor.PipelineRunner", FakeRunner)

    exit_code = main([
        "run", "--scope", "uf", "--month", "2026-05", "--uf", "PE",
        "--tables", "CNAEs", "Paises", "--cleanup", "none",
    ])

    assert exit_code == 0
    config = captured["config"]
    assert config.scope.type == "uf"
    assert config.scope.uf == "PE"
    assert config.output_name == "rf_cnpj_2026_05_pe"
    assert config.cleanup_mode == "none"
    assert config.options.include_cnaes is True
    assert config.options.include_paises is True
    assert config.options.include_socios is False


def test_cli_run_returns_one_when_pipeline_raises(monkeypatch):
    class FakeRunner:
        def run(self, config, emit=None):
            raise RuntimeError("boom")

    monkeypatch.setattr("rf_cnpj.core.processor.PipelineRunner", FakeRunner)

    exit_code = main(["run", "--scope", "brasil", "--month", "2026-05"])

    assert exit_code == 1


def test_streamlit_helpers_build_output_name_and_options():
    assert build_output_name(month="2026-02", uf="PE", municipio="Recife") == "rf_cnpj_2026_02_pe_recife"

    options = options_from_labels(["CNAEs", "Socios/QSA", "Paises"])
    assert options.include_cnaes is True
    assert options.include_socios is True
    assert options.include_paises is True
    assert options.include_simples is False
