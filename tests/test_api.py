from pathlib import Path
import json

from fastapi.testclient import TestClient

from rf_cnpj.api.app import create_app
from rf_cnpj.core.models import ExportResult


class FakeRunner:
    def __init__(self):
        self.configs = []

    def run(self, config, emit=None):
        self.configs.append(config)
        if emit:
            emit({"type": "process_start", "level": "info", "message": "Processando CSVs", "data": {}})
        return ExportResult(
            csv_path=Path("saida/rf_cnpj_pe.csv"),
            parquet_path=Path("saida/rf_cnpj_pe.parquet"),
            rows=123,
        )


class FakeMonthDiscovery:
    def fetch_available_months(self):
        return ["2026-01", "2026-02"]


def test_health_endpoint_reports_service_status():
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["service"] == "rf-cnpj-api"


def test_options_endpoint_exposes_ui_choices():
    client = TestClient(create_app(month_discovery=FakeMonthDiscovery()))

    response = client.get("/options")

    payload = response.json()

    assert response.status_code == 200
    assert "CNAEs" in payload["tables"]
    assert "Socios/QSA" in payload["tables"]
    assert "extracted" in payload["cleanup_modes"]
    assert payload["scope_types"] == ["uf", "municipio"]
    assert payload["months"] == ["2026-01", "2026-02"]
    assert {"value": "PE", "label": "PE - Pernambuco"} in payload["states"]


def fake_municipios_loader(
    uf: str, data_dir: str = "dados"
) -> list[dict[str, str]]:
    db = {
        "PE": [
            {"codigo": "1", "descricao": "OLINDA"},
            {"codigo": "2", "descricao": "RECIFE"},
        ],
        "SP": [
            {"codigo": "3", "descricao": "SAO PAULO"},
        ],
    }
    return db.get(uf.upper().strip(), [])


def test_municipios_endpoint_returns_filtered_by_uf():
    client = TestClient(create_app(municipios_loader=fake_municipios_loader))

    response = client.get("/municipios?uf=PE")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 2
    assert payload[0]["value"] == "OLINDA"
    assert "TOM 1" in payload[0]["label"]


def test_municipios_endpoint_returns_empty_for_nonexistent_uf():
    client = TestClient(create_app(municipios_loader=fake_municipios_loader))

    response = client.get("/municipios?uf=ZZ")

    assert response.status_code == 200
    assert response.json() == []


def test_directory_picker_endpoint_returns_selected_path():
    calls = []

    def fake_pick_directory(initial_dir=None):
        calls.append(initial_dir)
        return "C:/bases/rf-cnpj"

    client = TestClient(create_app(directory_picker=fake_pick_directory))

    response = client.post("/directories/pick", json={"initial_dir": "dados"})

    assert response.status_code == 200
    assert response.json() == {"path": "C:/bases/rf-cnpj"}
    assert calls == ["dados"]


def test_run_endpoint_builds_config_and_returns_export_result():
    runner = FakeRunner()
    client = TestClient(create_app(runner=runner))

    response = client.post(
        "/runs",
        json={
            "month": "2026-02",
            "data_dir": "dados",
            "output_dir": "saida",
            "scope_type": "municipio",
            "uf": "PE",
            "municipio": "Recife",
            "tables": ["CNAEs", "Socios/QSA"],
            "cleanup_mode": "extracted",
            "output_name": "rf_cnpj_recife",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "csv_path": "saida/rf_cnpj_pe.csv",
        "parquet_path": "saida/rf_cnpj_pe.parquet",
        "rows": 123,
    }
    config = runner.configs[0]
    assert config.month == "2026-02"
    assert config.scope.type == "municipio"
    assert config.scope.uf == "PE"
    assert config.scope.municipio == "RECIFE"
    assert config.options.include_cnaes is True
    assert config.options.include_socios is True
    assert config.options.include_simples is False


def test_run_job_endpoint_streams_events_until_done():
    runner = FakeRunner()
    client = TestClient(create_app(runner=runner))

    response = client.post(
        "/runs/jobs",
        json={
            "month": "2026-02",
            "data_dir": "dados",
            "output_dir": "saida",
            "scope_type": "uf",
            "uf": "PE",
            "municipio": None,
            "tables": ["CNAEs"],
            "cleanup_mode": "extracted",
            "output_name": "rf_cnpj_pe",
        },
    )
    assert response.status_code == 200
    run_id = response.json()["run_id"]

    with client.stream("GET", f"/runs/{run_id}/events") as stream:
        body = "".join(stream.iter_text())

    payloads = [
        json.loads(line.removeprefix("data: "))
        for line in body.splitlines()
        if line.startswith("data: ")
    ]
    assert [event["type"] for event in payloads] == ["process_start", "done"]
    assert payloads[-1]["data"] == {
        "csv_path": "saida/rf_cnpj_pe.csv",
        "parquet_path": "saida/rf_cnpj_pe.parquet",
        "rows": 123,
    }
