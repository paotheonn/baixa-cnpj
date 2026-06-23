import pandas as pd

from rf_cnpj.core.output import export_csv_and_parquet


def test_exports_csv_and_parquet(tmp_path):
    df = pd.DataFrame([{"CNPJ": "11.111.111/0001-91", "RAZAO_SOCIAL": "EMPRESA"}])

    result = export_csv_and_parquet(df, tmp_path, "empresas_pe")

    assert result.csv_path.exists()
    assert result.parquet_path.exists()
    assert result.rows == 1
    assert pd.read_parquet(result.parquet_path).iloc[0]["CNPJ"] == "11.111.111/0001-91"
