from pathlib import Path

import pandas as pd

from rf_cnpj.core.models import ProcessingOptions, Scope
from rf_cnpj.engines.pandas_engine import PandasCNPJEngine


def write_rf(path: Path, rows: list[list[str]]) -> None:
    path.write_text("\n".join(";".join(row) for row in rows), encoding="latin-1")


def create_fixture(raw_dir: Path) -> None:
    raw_dir.mkdir(exist_ok=True)
    write_rf(
        raw_dir / "municipios.csv",
        [
            ["2605", "OLINDA"],
            ["2531", "RECIFE"],
        ],
    )
    write_rf(raw_dir / "cnaes.csv", [["4711302", "Comercio varejista"], ["6201501", "Software"]])
    write_rf(raw_dir / "motivos.csv", [["00", "Sem motivo"]])
    write_rf(raw_dir / "naturezas.csv", [["2135", "Empresario Individual"]])
    write_rf(raw_dir / "qualificacoes.csv", [["49", "Socio-Administrador"], ["05", "Administrador"]])
    write_rf(raw_dir / "paises.csv", [["105", "Brasil"]])
    write_rf(
        raw_dir / "simples.csv",
        [
            ["11111111", "S", "", "20200101", "N", "", ""],
            ["22222222", "N", "", "", "S", "", "20210101"],
        ],
    )
    write_rf(
        raw_dir / "empresas0.csv",
        [
            ["11111111", "EMPRESA RECIFE LTDA", "2135", "49", "1234,50", "01", ""],
            ["22222222", "EMPRESA OLINDA LTDA", "2135", "49", "999,99", "03", ""],
        ],
    )
    write_rf(
        raw_dir / "socios0.csv",
        [
            ["11111111", "2", "MARIA SOCIA", "***", "49", "20200110", "105", "00000000000", "", "05", "5"],
            ["11111111", "2", "JOAO SOCIO", "***", "49", "20200210", "105", "00000000000", "", "05", "6"],
            ["22222222", "2", "ANA SOCIA", "***", "49", "20200310", "105", "00000000000", "", "05", "4"],
        ],
    )
    write_rf(
        raw_dir / "estabelecimentos0.csv",
        [
            [
                "11111111", "0001", "91", "1", "LOJA RECIFE", "02", "20240101", "00", "", "", "20200101",
                "4711302", "6201501", "AVENIDA", "BOA VIAGEM", "10", "SALA 1", "BOA VIAGEM", "51000000",
                "PE", "2531", "81", "33334444", "81", "99998888", "", "", "CONTATO@RECIFE.COM", "", "",
            ],
            [
                "22222222", "0001", "92", "1", "LOJA OLINDA", "02", "20240101", "00", "", "", "20210101",
                "4711302", "", "RUA", "CENTRO", "20", "", "CENTRO", "55000000",
                "PE", "2605", "81", "22223333", "", "", "", "", "CONTATO@OLINDA.COM", "", "",
            ],
            [
                "33333333", "0001", "93", "1", "LOJA SP", "02", "20240101", "00", "", "", "20210101",
                "4711302", "", "RUA", "PAULISTA", "30", "", "BELA VISTA", "01000000",
                "SP", "7107", "11", "11112222", "", "", "", "", "CONTATO@SP.COM", "", "",
            ],
        ],
    )


def test_processes_single_municipality_with_selected_tables(tmp_path):
    create_fixture(tmp_path)
    engine = PandasCNPJEngine(chunk_size=2)

    result = engine.process(
        tmp_path,
        scope=Scope(type="municipio", uf="PE", municipio="RECIFE"),
        options=ProcessingOptions(include_socios=True),
    )

    assert list(result["CNPJ"]) == ["11.111.111/0001-91"]
    row = result.iloc[0]
    assert row["MUNICIPIO"] == "RECIFE"
    assert row["UF"] == "PE"
    assert row["RAZAO_SOCIAL"] == "EMPRESA RECIFE LTDA"
    assert row["CNAE_PRINCIPAL_DESCRICAO"] == "Comercio varejista"
    assert row["SIMPLES"] == "Sim"
    assert row["MEI"] == "Não"
    assert row["QTD_SOCIOS"] == 2
    assert row["SOCIOS_NOMES"] == "MARIA SOCIA | JOAO SOCIO"


def test_processes_entire_uf_without_city_filter(tmp_path):
    create_fixture(tmp_path)
    engine = PandasCNPJEngine(chunk_size=2)

    result = engine.process(
        tmp_path,
        scope=Scope(type="uf", uf="PE"),
        options=ProcessingOptions(include_socios=False),
    )

    assert list(result["CNPJ"]) == ["11.111.111/0001-91", "22.222.222/0001-92"]
    assert set(result["MUNICIPIO"]) == {"RECIFE", "OLINDA"}
    assert result["QTD_SOCIOS"].tolist() == ["", ""]


def test_disabled_simples_fields_are_blank_not_false(tmp_path):
    create_fixture(tmp_path)
    engine = PandasCNPJEngine(chunk_size=2)

    result = engine.process(
        tmp_path,
        scope=Scope(type="municipio", uf="PE", municipio="RECIFE"),
        options=ProcessingOptions(include_simples=False, include_socios=False),
    )

    row = result.iloc[0]
    assert row["SIMPLES"] == ""
    assert row["MEI"] == ""
    assert row["QTD_SOCIOS"] == ""


def test_simples_is_filtered_in_chunks_instead_of_loaded_full(tmp_path, monkeypatch):
    create_fixture(tmp_path)
    engine = PandasCNPJEngine(chunk_size=2)
    original_read_full = engine._read_full

    def fail_if_full_simples(path, columns):
        if Path(path).name == "simples.csv":
            raise AssertionError("simples.csv must be chunk-filtered")
        return original_read_full(path, columns)

    monkeypatch.setattr(engine, "_read_full", fail_if_full_simples)

    result = engine.process(
        tmp_path,
        scope=Scope(type="municipio", uf="PE", municipio="RECIFE"),
        options=ProcessingOptions(include_simples=True, include_socios=False),
    )

    assert result.iloc[0]["SIMPLES"] == "Sim"


def test_selected_missing_optional_table_fails_fast(tmp_path):
    create_fixture(tmp_path)
    (tmp_path / "simples.csv").unlink()
    engine = PandasCNPJEngine(chunk_size=2)

    try:
        engine.process(
            tmp_path,
            scope=Scope(type="municipio", uf="PE", municipio="RECIFE"),
            options=ProcessingOptions(include_simples=True, include_socios=False),
        )
    except FileNotFoundError as exc:
        assert "simples.csv" in str(exc)
    else:
        raise AssertionError("missing selected optional table should fail fast")


def test_selected_missing_socios_table_fails_fast(tmp_path):
    create_fixture(tmp_path)
    (tmp_path / "socios0.csv").unlink()
    engine = PandasCNPJEngine(chunk_size=2)

    try:
        engine.process(
            tmp_path,
            scope=Scope(type="municipio", uf="PE", municipio="RECIFE"),
            options=ProcessingOptions(include_simples=False, include_socios=True),
        )
    except FileNotFoundError as exc:
        assert "socios" in str(exc).lower()
    else:
        raise AssertionError("missing selected socios table should fail fast")
