"""Pandas-based processing engine for RF CNPJ data."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd

from rf_cnpj.core.models import ProcessingOptions, Scope
from rf_cnpj.core.normalization import (
    build_full_address,
    clean_text,
    format_cnpj,
    format_date,
    format_phone,
    normalize_capital,
    normalize_key,
    yes_no,
)
from rf_cnpj.core.schemas import (
    COLUNAS_CODIGO_DESCRICAO,
    COLUNAS_EMPRESAS,
    COLUNAS_ESTABELECIMENTOS,
    COLUNAS_SIMPLES,
    COLUNAS_SOCIOS,
    FAIXA_ETARIA_SOCIO,
    FINAL_COLUMNS,
    MATRIZ_FILIAL,
    PORTE_EMPRESA,
    RF_ENCODING,
    RF_SEPARATOR,
    SITUACAO_CADASTRAL,
)


class PandasCNPJEngine:
    """Processes extracted RF CSV files with Pandas chunks."""

    def __init__(self, chunk_size: int = 500_000):
        self.chunk_size = chunk_size

    def process(self, raw_dir: Path, scope: Scope, options: ProcessingOptions) -> pd.DataFrame:
        raw_dir = Path(raw_dir)
        municipios = self._load_code_description(raw_dir / "municipios.csv")
        municipio_codes = self._municipio_codes(municipios, scope)
        estabelecimentos = self._load_estabelecimentos(raw_dir, scope, municipio_codes)

        if estabelecimentos.empty:
            return pd.DataFrame(columns=FINAL_COLUMNS)

        cnpj_bases = set(estabelecimentos["CNPJ_BASE"].dropna().astype(str))
        empresas = self._load_empresas(raw_dir, cnpj_bases)
        df = estabelecimentos.merge(empresas, on="CNPJ_BASE", how="left")

        self._current_raw_dir = raw_dir
        aux = self._load_auxiliary_tables(raw_dir, options)
        aux["simples"] = self._load_simples(raw_dir, cnpj_bases) if options.include_simples else pd.DataFrame(columns=COLUNAS_SIMPLES)
        final = self._build_final_dataframe(df, municipios, aux, options)
        final = final.drop_duplicates(subset=["CNPJ"], keep="first")
        return final[FINAL_COLUMNS]

    def _csv_files(self, raw_dir: Path, prefix: str) -> list[Path]:
        return sorted(raw_dir.glob(f"{prefix}*.csv"))

    def _read_chunks(self, path: Path, columns: list[str]) -> Iterable[pd.DataFrame]:
        return pd.read_csv(
            path,
            sep=RF_SEPARATOR,
            encoding=RF_ENCODING,
            header=None,
            names=columns,
            dtype=str,
            chunksize=self.chunk_size,
            keep_default_na=False,
        )

    def _read_full(self, path: Path, columns: list[str]) -> pd.DataFrame:
        if not path.exists():
            return pd.DataFrame(columns=columns)
        return pd.read_csv(
            path,
            sep=RF_SEPARATOR,
            encoding=RF_ENCODING,
            header=None,
            names=columns,
            dtype=str,
            keep_default_na=False,
        )

    def _load_code_description(self, path: Path) -> pd.DataFrame:
        return self._read_full(path, COLUNAS_CODIGO_DESCRICAO)

    def _load_selected_code_description(self, path: Path) -> pd.DataFrame:
        if not path.exists():
            raise FileNotFoundError(f"Tabela selecionada não encontrada: {path}")
        return self._load_code_description(path)

    def _code_map(self, df: pd.DataFrame) -> dict[str, str]:
        if df.empty:
            return {}
        return dict(zip(df["CODIGO"].astype(str), df["DESCRICAO"].astype(str)))

    def _municipio_codes(self, municipios: pd.DataFrame, scope: Scope) -> set[str] | None:
        if scope.type == "uf":
            return None
        if municipios.empty:
            return set()
        wanted = normalize_key(scope.municipio)
        mask = municipios["DESCRICAO"].apply(normalize_key) == wanted
        return set(municipios.loc[mask, "CODIGO"].astype(str))

    def _load_estabelecimentos(self, raw_dir: Path, scope: Scope, municipio_codes: set[str] | None) -> pd.DataFrame:
        frames: list[pd.DataFrame] = []
        for path in self._csv_files(raw_dir, "estabelecimentos"):
            for chunk in self._read_chunks(path, COLUNAS_ESTABELECIMENTOS):
                filtered = chunk[chunk["UF"].str.upper() == scope.uf]
                if municipio_codes is not None:
                    filtered = filtered[filtered["MUNICIPIO_CODIGO"].isin(municipio_codes)]
                if not filtered.empty:
                    frames.append(filtered.copy())
        if not frames:
            return pd.DataFrame(columns=COLUNAS_ESTABELECIMENTOS)
        return pd.concat(frames, ignore_index=True)

    def _load_empresas(self, raw_dir: Path, cnpj_bases: set[str]) -> pd.DataFrame:
        frames: list[pd.DataFrame] = []
        for path in self._csv_files(raw_dir, "empresas"):
            for chunk in self._read_chunks(path, COLUNAS_EMPRESAS):
                filtered = chunk[chunk["CNPJ_BASE"].isin(cnpj_bases)]
                if not filtered.empty:
                    frames.append(filtered.copy())
        if not frames:
            return pd.DataFrame(columns=COLUNAS_EMPRESAS)
        return pd.concat(frames, ignore_index=True).drop_duplicates(subset=["CNPJ_BASE"], keep="first")

    def _load_auxiliary_tables(self, raw_dir: Path, options: ProcessingOptions) -> dict[str, pd.DataFrame]:
        return {
            "cnaes": self._load_selected_code_description(raw_dir / "cnaes.csv") if options.include_cnaes else pd.DataFrame(columns=COLUNAS_CODIGO_DESCRICAO),
            "motivos": self._load_selected_code_description(raw_dir / "motivos.csv") if options.include_motivos else pd.DataFrame(columns=COLUNAS_CODIGO_DESCRICAO),
            "naturezas": self._load_selected_code_description(raw_dir / "naturezas.csv") if options.include_naturezas else pd.DataFrame(columns=COLUNAS_CODIGO_DESCRICAO),
            "qualificacoes": self._load_selected_code_description(raw_dir / "qualificacoes.csv") if options.include_qualificacoes else pd.DataFrame(columns=COLUNAS_CODIGO_DESCRICAO),
            "paises": self._load_selected_code_description(raw_dir / "paises.csv") if options.include_paises else pd.DataFrame(columns=COLUNAS_CODIGO_DESCRICAO),
        }

    def _load_simples(self, raw_dir: Path, cnpj_bases: set[str]) -> pd.DataFrame:
        path = raw_dir / "simples.csv"
        if not path.exists():
            raise FileNotFoundError(f"Tabela selecionada não encontrada: {path}")
        frames: list[pd.DataFrame] = []
        for chunk in self._read_chunks(path, COLUNAS_SIMPLES):
            filtered = chunk[chunk["CNPJ_BASE"].isin(cnpj_bases)]
            if not filtered.empty:
                frames.append(filtered.copy())
        if not frames:
            return pd.DataFrame(columns=COLUNAS_SIMPLES)
        return pd.concat(frames, ignore_index=True)

    def _build_final_dataframe(
        self,
        df: pd.DataFrame,
        municipios: pd.DataFrame,
        aux: dict[str, pd.DataFrame],
        options: ProcessingOptions,
    ) -> pd.DataFrame:
        cnae_map = self._code_map(aux["cnaes"])
        motivo_map = {k.zfill(2): v for k, v in self._code_map(aux["motivos"]).items()}
        municipio_map = self._code_map(municipios)
        natureza_map = self._code_map(aux["naturezas"])
        qualificacao_map = self._code_map(aux["qualificacoes"])

        out = pd.DataFrame()
        out["CNPJ"] = df.apply(lambda row: format_cnpj(row["CNPJ_BASE"], row["CNPJ_ORDEM"], row["CNPJ_DV"]), axis=1)
        out["CNPJ_BASE"] = df["CNPJ_BASE"]
        out["MATRIZ_FILIAL"] = df["MATRIZ_FILIAL_CODIGO"].map(MATRIZ_FILIAL).fillna(df["MATRIZ_FILIAL_CODIGO"])
        out["RAZAO_SOCIAL"] = df.get("RAZAO_SOCIAL", "").apply(clean_text)
        out["NOME_FANTASIA"] = df["NOME_FANTASIA"].apply(clean_text)
        out["SITUACAO_CADASTRAL"] = df["SITUACAO_CADASTRAL_CODIGO"].map(SITUACAO_CADASTRAL).fillna(df["SITUACAO_CADASTRAL_CODIGO"])
        out["DATA_SITUACAO_CADASTRAL"] = df["DATA_SITUACAO_CADASTRAL"].apply(format_date)

        motivo_codigo = df["MOTIVO_SITUACAO_CADASTRAL_CODIGO"].astype(str).str.zfill(2)
        out["MOTIVO_SITUACAO_CADASTRAL"] = motivo_codigo.map(motivo_map).fillna(motivo_codigo)
        out["DATA_INICIO_ATIVIDADE"] = df["DATA_INICIO_ATIVIDADE"].apply(format_date)
        out["CNAE_PRINCIPAL_CODIGO"] = df["CNAE_PRINCIPAL_CODIGO"]
        out["CNAE_PRINCIPAL_DESCRICAO"] = df["CNAE_PRINCIPAL_CODIGO"].map(cnae_map).fillna(df["CNAE_PRINCIPAL_CODIGO"])
        out["CNAES_SECUNDARIOS"] = df["CNAES_SECUNDARIOS_CODIGOS"].apply(lambda value: self._translate_multi_codes(value, cnae_map))
        out["TIPO_LOGRADOURO"] = df["TIPO_LOGRADOURO"].apply(clean_text)
        out["LOGRADOURO"] = df["LOGRADOURO"].apply(clean_text)
        out["NUMERO"] = df["NUMERO"].apply(clean_text)
        out["COMPLEMENTO"] = df["COMPLEMENTO"].apply(clean_text)
        out["BAIRRO"] = df["BAIRRO"].apply(clean_text)
        out["CEP"] = df["CEP"].apply(clean_text)
        out["UF"] = df["UF"].str.upper()
        out["MUNICIPIO"] = df["MUNICIPIO_CODIGO"].map(municipio_map).fillna(df["MUNICIPIO_CODIGO"])
        out["MUNICIPIO_CODIGO"] = df["MUNICIPIO_CODIGO"]
        out["ENDERECO_COMPLETO"] = df.apply(
            lambda row: build_full_address(row["TIPO_LOGRADOURO"], row["LOGRADOURO"], row["NUMERO"], row["COMPLEMENTO"]),
            axis=1,
        )
        out["DDD_1"] = df["DDD_1"].apply(clean_text)
        out["TELEFONE_1"] = df.apply(lambda row: format_phone(row["DDD_1"], row["TELEFONE_1_RAW"]), axis=1)
        out["DDD_2"] = df["DDD_2"].apply(clean_text)
        out["TELEFONE_2"] = df.apply(lambda row: format_phone(row["DDD_2"], row["TELEFONE_2_RAW"]), axis=1)
        out["EMAIL"] = df["EMAIL"].apply(lambda value: clean_text(value).lower())
        out["CAPITAL_SOCIAL"] = df.get("CAPITAL_SOCIAL", "").apply(normalize_capital)
        out["PORTE_EMPRESA"] = df.get("PORTE_EMPRESA_CODIGO", "").map(PORTE_EMPRESA).fillna(df.get("PORTE_EMPRESA_CODIGO", ""))
        out["NATUREZA_JURIDICA_CODIGO"] = df.get("NATUREZA_JURIDICA_CODIGO", "")
        out["NATUREZA_JURIDICA"] = df.get("NATUREZA_JURIDICA_CODIGO", "").map(natureza_map).fillna(df.get("NATUREZA_JURIDICA_CODIGO", ""))
        out["QUALIFICACAO_RESPONSAVEL"] = df.get("QUALIFICACAO_RESPONSAVEL_CODIGO", "").map(qualificacao_map).fillna(df.get("QUALIFICACAO_RESPONSAVEL_CODIGO", ""))

        if options.include_simples:
            simples = self._simples_map(aux["simples"])
            out["SIMPLES"] = df["CNPJ_BASE"].map(simples["simples"]).fillna("Não")
            out["MEI"] = df["CNPJ_BASE"].map(simples["mei"]).fillna("Não")
        else:
            out["SIMPLES"] = ""
            out["MEI"] = ""

        socios = self._socios_aggregated(df["CNPJ_BASE"], aux, options)
        out = out.merge(socios, on="CNPJ_BASE", how="left")
        socio_columns = [
            "QTD_SOCIOS",
            "SOCIOS_NOMES",
            "SOCIOS_QUALIFICACOES",
            "SOCIOS_DATA_ENTRADA",
            "SOCIOS_FAIXA_ETARIA",
            "SOCIOS_PAIS",
            "SOCIOS_REPRESENTANTES_LEGAIS",
        ]
        if options.include_socios:
            out["QTD_SOCIOS"] = out["QTD_SOCIOS"].fillna(0).astype(int)
        else:
            out["QTD_SOCIOS"] = out["QTD_SOCIOS"].fillna("")
        for column in socio_columns[1:]:
            out[column] = out[column].fillna("")
        return out

    def _translate_multi_codes(self, value: str, code_map: dict[str, str]) -> str:
        codes = [clean_text(code) for code in str(value).split(",") if clean_text(code)]
        return " | ".join(code_map.get(code, code) for code in codes)

    def _simples_map(self, simples: pd.DataFrame) -> dict[str, dict[str, str]]:
        if simples.empty:
            return {"simples": {}, "mei": {}}
        dedup = simples.drop_duplicates(subset=["CNPJ_BASE"], keep="last")
        return {
            "simples": dict(zip(dedup["CNPJ_BASE"], dedup["OPCAO_SIMPLES"].apply(yes_no))),
            "mei": dict(zip(dedup["CNPJ_BASE"], dedup["OPCAO_MEI"].apply(yes_no))),
        }

    def _socios_aggregated(self, cnpj_bases: pd.Series, aux: dict[str, pd.DataFrame], options: ProcessingOptions) -> pd.DataFrame:
        base_df = pd.DataFrame({"CNPJ_BASE": sorted(set(cnpj_bases.astype(str)))})
        empty_unknown = base_df.assign(
            QTD_SOCIOS="",
            SOCIOS_NOMES="",
            SOCIOS_QUALIFICACOES="",
            SOCIOS_DATA_ENTRADA="",
            SOCIOS_FAIXA_ETARIA="",
            SOCIOS_PAIS="",
            SOCIOS_REPRESENTANTES_LEGAIS="",
        )
        empty_loaded = base_df.assign(
            QTD_SOCIOS=0,
            SOCIOS_NOMES="",
            SOCIOS_QUALIFICACOES="",
            SOCIOS_DATA_ENTRADA="",
            SOCIOS_FAIXA_ETARIA="",
            SOCIOS_PAIS="",
            SOCIOS_REPRESENTANTES_LEGAIS="",
        )
        if not options.include_socios:
            return empty_unknown

        raw_dir = getattr(self, "_current_raw_dir", None)
        if raw_dir is None:
            return empty_loaded

        cnpj_set = set(base_df["CNPJ_BASE"])
        frames: list[pd.DataFrame] = []
        socios_files = self._csv_files(raw_dir, "socios")
        if not socios_files:
            raise FileNotFoundError(f"Tabela selecionada não encontrada: {raw_dir / 'socios*.csv'}")
        for path in socios_files:
            for chunk in self._read_chunks(path, COLUNAS_SOCIOS):
                filtered = chunk[chunk["CNPJ_BASE"].isin(cnpj_set)]
                if not filtered.empty:
                    frames.append(filtered.copy())
        if not frames:
            return empty_loaded

        socios = pd.concat(frames, ignore_index=True)
        qualificacao_map = self._code_map(aux["qualificacoes"])
        pais_map = self._code_map(aux["paises"])
        socios["NOME_SOCIO_RAZAO_SOCIAL"] = socios["NOME_SOCIO_RAZAO_SOCIAL"].apply(clean_text)
        socios["QUALIFICACAO"] = socios["QUALIFICACAO_SOCIO_CODIGO"].map(qualificacao_map).fillna(socios["QUALIFICACAO_SOCIO_CODIGO"])
        socios["DATA_ENTRADA"] = socios["DATA_ENTRADA_SOCIEDADE"].apply(format_date)
        socios["FAIXA_ETARIA"] = socios["FAIXA_ETARIA_CODIGO"].map(FAIXA_ETARIA_SOCIO).fillna(socios["FAIXA_ETARIA_CODIGO"])
        socios["PAIS"] = socios["PAIS_CODIGO"].map(pais_map).fillna(socios["PAIS_CODIGO"])
        socios["REPRESENTANTE"] = socios["NOME_REPRESENTANTE_LEGAL"].apply(clean_text)

        grouped = socios.groupby("CNPJ_BASE", sort=False).agg(
            QTD_SOCIOS=("NOME_SOCIO_RAZAO_SOCIAL", "size"),
            SOCIOS_NOMES=("NOME_SOCIO_RAZAO_SOCIAL", self._join_non_empty),
            SOCIOS_QUALIFICACOES=("QUALIFICACAO", self._join_non_empty),
            SOCIOS_DATA_ENTRADA=("DATA_ENTRADA", self._join_non_empty),
            SOCIOS_FAIXA_ETARIA=("FAIXA_ETARIA", self._join_non_empty),
            SOCIOS_PAIS=("PAIS", self._join_non_empty),
            SOCIOS_REPRESENTANTES_LEGAIS=("REPRESENTANTE", self._join_non_empty),
        ).reset_index()
        return empty_loaded.drop(columns=[
            "QTD_SOCIOS",
            "SOCIOS_NOMES",
            "SOCIOS_QUALIFICACOES",
            "SOCIOS_DATA_ENTRADA",
            "SOCIOS_FAIXA_ETARIA",
            "SOCIOS_PAIS",
            "SOCIOS_REPRESENTANTES_LEGAIS",
        ]).merge(grouped, on="CNPJ_BASE", how="left")

    def _join_non_empty(self, values: pd.Series) -> str:
        cleaned = [clean_text(value) for value in values if clean_text(value)]
        return " | ".join(cleaned)
