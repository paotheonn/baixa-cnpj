"""Typed configuration models used by the pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal


@dataclass(frozen=True)
class Scope:
    """Processing scope: one UF or one municipality inside a UF."""

    type: Literal["uf", "municipio"]
    uf: str
    municipio: str | None = None

    def __post_init__(self) -> None:
        scope_type = self.type.lower().strip()
        uf = self.uf.upper().strip()
        municipio = self.municipio.strip().upper() if self.municipio else None

        if scope_type not in {"uf", "municipio"}:
            raise ValueError("Scope.type deve ser 'uf' ou 'municipio'.")
        if len(uf) != 2:
            raise ValueError("UF deve ter duas letras.")
        if scope_type == "municipio" and not municipio:
            raise ValueError("Municipio é obrigatório quando scope.type='municipio'.")

        object.__setattr__(self, "type", scope_type)
        object.__setattr__(self, "uf", uf)
        object.__setattr__(self, "municipio", municipio)


@dataclass(frozen=True)
class ProcessingOptions:
    """Optional RF tables to join into the final output."""

    include_cnaes: bool = True
    include_simples: bool = True
    include_motivos: bool = True
    include_naturezas: bool = True
    include_qualificacoes: bool = True
    include_paises: bool = True
    include_socios: bool = True


@dataclass(frozen=True)
class RunConfig:
    """Full run configuration used by CLI/UI orchestration."""

    month: str
    data_dir: Path
    output_dir: Path
    scope: Scope
    options: ProcessingOptions
    output_name: str = "rf_cnpj"
    cleanup_mode: Literal["none", "extracted", "all_raw"] = "extracted"


@dataclass(frozen=True)
class ExportResult:
    csv_path: Path
    parquet_path: Path
    rows: int
