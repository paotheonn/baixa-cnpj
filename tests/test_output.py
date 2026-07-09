import pandas as pd

from rf_cnpj.core.output import IncrementalUFExporter, export_csv_and_parquet


def test_exports_csv_and_parquet(tmp_path):
    df = pd.DataFrame([{"CNPJ": "11.111.111/0001-91", "RAZAO_SOCIAL": "EMPRESA"}])

    result = export_csv_and_parquet(df, tmp_path, "empresas_pe")

    assert result.csv_path.exists()
    assert result.parquet_path.exists()
    assert result.rows == 1
    assert pd.read_parquet(result.parquet_path).iloc[0]["CNPJ"] == "11.111.111/0001-91"


def _uf_df(uf: str, cnpj: str) -> pd.DataFrame:
    return pd.DataFrame([{"CNPJ": cnpj, "UF": uf}])


def test_incremental_exporter_merges_parts_in_uf_order(tmp_path):
    exporter = IncrementalUFExporter(tmp_path, "rf_cnpj_2026_02_BR")

    exporter.write_uf("SP", _uf_df("SP", "11.111.111/0001-91"))
    exporter.write_uf("PE", _uf_df("PE", "22.222.222/0001-92"))

    assert exporter.completed_ufs() == {"SP", "PE"}

    result = exporter.merge()

    assert result.rows == 2
    merged = pd.read_parquet(result.parquet_path)
    # Sorted UF order: PE before SP.
    assert list(merged["UF"]) == ["PE", "SP"]
    csv = pd.read_csv(result.csv_path, dtype=str)
    assert list(csv["UF"]) == ["PE", "SP"]


def test_incremental_exporter_cleanup_removes_parts_and_manifest(tmp_path):
    exporter = IncrementalUFExporter(tmp_path, "rf_cnpj_2026_02_BR")
    exporter.write_uf("SP", _uf_df("SP", "11.111.111/0001-91"))
    exporter.merge()

    assert exporter.manifest_path.exists()
    assert exporter.parts_dir.exists()

    exporter.cleanup()

    assert not exporter.manifest_path.exists()
    assert not exporter.parts_dir.exists()
    assert exporter.csv_path.exists()
    assert exporter.parquet_path.exists()


def test_incremental_exporter_resumes_from_manifest(tmp_path):
    first = IncrementalUFExporter(tmp_path, "rf_cnpj_2026_02_BR")
    first.write_uf("PE", _uf_df("PE", "22.222.222/0001-92"))

    # New exporter instance sees the persisted checkpoint.
    resumed = IncrementalUFExporter(tmp_path, "rf_cnpj_2026_02_BR")
    assert resumed.completed_ufs() == {"PE"}

    resumed.write_uf("SP", _uf_df("SP", "11.111.111/0001-91"))
    result = resumed.merge()

    assert result.rows == 2
    assert set(pd.read_parquet(result.parquet_path)["UF"]) == {"PE", "SP"}
