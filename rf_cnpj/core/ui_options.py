"""Shared UI labels and helpers for local frontends."""

from __future__ import annotations

from rf_cnpj.core.models import ProcessingOptions
from rf_cnpj.core.normalization import safe_filename

TABLE_LABELS = {
    "CNAEs": "include_cnaes",
    "Simples/MEI": "include_simples",
    "Motivos": "include_motivos",
    "Naturezas Juridicas": "include_naturezas",
    "Qualificacoes": "include_qualificacoes",
    "Paises": "include_paises",
    "Socios/QSA": "include_socios",
}

DEFAULT_TABLE_LABELS = list(TABLE_LABELS.keys())

BRAZIL_STATES = [
    {"value": "AC", "label": "AC - Acre"},
    {"value": "AL", "label": "AL - Alagoas"},
    {"value": "AP", "label": "AP - Amapa"},
    {"value": "AM", "label": "AM - Amazonas"},
    {"value": "BA", "label": "BA - Bahia"},
    {"value": "CE", "label": "CE - Ceara"},
    {"value": "DF", "label": "DF - Distrito Federal"},
    {"value": "ES", "label": "ES - Espirito Santo"},
    {"value": "GO", "label": "GO - Goias"},
    {"value": "MA", "label": "MA - Maranhao"},
    {"value": "MT", "label": "MT - Mato Grosso"},
    {"value": "MS", "label": "MS - Mato Grosso do Sul"},
    {"value": "MG", "label": "MG - Minas Gerais"},
    {"value": "PA", "label": "PA - Para"},
    {"value": "PB", "label": "PB - Paraiba"},
    {"value": "PR", "label": "PR - Parana"},
    {"value": "PE", "label": "PE - Pernambuco"},
    {"value": "PI", "label": "PI - Piaui"},
    {"value": "RJ", "label": "RJ - Rio de Janeiro"},
    {"value": "RN", "label": "RN - Rio Grande do Norte"},
    {"value": "RS", "label": "RS - Rio Grande do Sul"},
    {"value": "RO", "label": "RO - Rondonia"},
    {"value": "RR", "label": "RR - Roraima"},
    {"value": "SC", "label": "SC - Santa Catarina"},
    {"value": "SP", "label": "SP - Sao Paulo"},
    {"value": "SE", "label": "SE - Sergipe"},
    {"value": "TO", "label": "TO - Tocantins"},
]


def options_from_labels(labels: list[str]) -> ProcessingOptions:
    values = {field: False for field in TABLE_LABELS.values()}
    for label in labels:
        field = TABLE_LABELS[label]
        values[field] = True
    return ProcessingOptions(**values)


def build_output_name(month: str, uf: str, municipio: str | None = None) -> str:
    parts = ["rf_cnpj", month.replace("-", "_"), uf]
    if municipio:
        parts.append(municipio)
    return safe_filename("_".join(parts))
