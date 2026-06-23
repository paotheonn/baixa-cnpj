from __future__ import annotations

from pathlib import Path

import pandas as pd
import requests

_MAPPING_URL = "https://www.gov.br/receitafederal/dados/municipios.csv"
_RF_ENCODING = "latin-1"
_COLUMNS = ["CODIGO_TOM", "CODIGO_IBGE", "MUNICIPIO_TOM", "MUNICIPIO_IBGE", "UF"]


def _mapping_path(data_dir: str) -> Path:
    return Path(data_dir) / "municipios_mapping.csv"


def _download_mapping(data_dir: str) -> Path:
    path = _mapping_path(data_dir)
    if path.exists() and path.stat().st_size > 0:
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    resp = requests.get(_MAPPING_URL, timeout=60)
    resp.raise_for_status()
    path.write_bytes(resp.content)
    return path


def municipios_por_uf(uf: str, data_dir: str = "dados") -> list[dict[str, str]]:
    try:
        path = _download_mapping(data_dir)
    except Exception:
        return []

    try:
        df = pd.read_csv(
            path,
            sep=";",
            encoding=_RF_ENCODING,
            dtype=str,
            on_bad_lines="skip",
        )
    except Exception:
        return []

    if df.shape[1] < 5:
        return []
    df.columns = _COLUMNS[: df.shape[1]]

    uf_upper = uf.upper().strip()
    matched = df[df["UF"] == uf_upper].copy()
    matched.sort_values("MUNICIPIO_TOM", inplace=True)

    return [
        {"codigo": row["CODIGO_TOM"], "descricao": row["MUNICIPIO_TOM"]}
        for _, row in matched.iterrows()
    ]
