"""Output writers for processed CNPJ data."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .models import ExportResult
from .normalization import safe_filename


def export_csv_and_parquet(df: pd.DataFrame, output_dir: Path, base_name: str) -> ExportResult:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    safe_base = safe_filename(base_name)
    csv_path = output_dir / f"{safe_base}.csv"
    parquet_path = output_dir / f"{safe_base}.parquet"

    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    df.to_parquet(parquet_path, index=False)

    return ExportResult(csv_path=csv_path, parquet_path=parquet_path, rows=len(df))
