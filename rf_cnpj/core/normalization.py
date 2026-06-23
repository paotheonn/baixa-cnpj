"""Normalization helpers for RF CNPJ values."""

from __future__ import annotations

import math
import re
import unicodedata
from typing import Any

import pandas as pd


def is_blank(value: Any) -> bool:
    if value is None:
        return True
    try:
        if pd.isna(value):
            return True
    except TypeError:
        pass
    text = str(value).strip()
    return text == "" or text.lower() == "nan"


def clean_text(value: Any) -> str:
    if is_blank(value):
        return ""
    return " ".join(str(value).strip().split())


def normalize_key(value: Any) -> str:
    text = clean_text(value).upper()
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(c for c in normalized if not unicodedata.combining(c))


def digits_only(value: Any) -> str:
    if is_blank(value):
        return ""
    return "".join(ch for ch in str(value) if ch.isdigit())


def format_cnpj(cnpj_base: Any, ordem: Any, dv: Any) -> str:
    base = digits_only(cnpj_base).zfill(8)[-8:]
    ordem_text = digits_only(ordem).zfill(4)[-4:]
    dv_text = digits_only(dv).zfill(2)[-2:]
    return f"{base[:2]}.{base[2:5]}.{base[5:]}/{ordem_text}-{dv_text}"


def format_date(value: Any) -> str:
    if is_blank(value):
        return ""
    try:
        text = str(int(float(str(value).replace(",", "."))))
    except (TypeError, ValueError):
        text = digits_only(value)
    if len(text) != 8:
        return clean_text(value)
    return f"{text[6:8]}/{text[4:6]}/{text[:4]}"


def format_phone(ddd: Any, phone: Any) -> str:
    phone_digits = digits_only(phone)
    if not phone_digits:
        return ""
    ddd_digits = digits_only(ddd)
    return f"({ddd_digits}) {phone_digits}" if ddd_digits else phone_digits


def build_full_address(tipo_logradouro: Any, logradouro: Any, numero: Any, complemento: Any) -> str:
    street_parts = [clean_text(tipo_logradouro), clean_text(logradouro)]
    street = " ".join(part for part in street_parts if part)
    parts = [street, clean_text(numero), clean_text(complemento)]
    return ", ".join(part for part in parts if part)


def normalize_capital(value: Any) -> str:
    if is_blank(value):
        return "0,00"
    raw = clean_text(value).replace(".", "").replace(",", ".")
    try:
        number = float(raw)
    except ValueError:
        return "0,00"
    if math.isnan(number):
        return "0,00"
    return f"{number:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def yes_no(value: Any) -> str:
    return "Sim" if clean_text(value).upper() == "S" else "Não"


def safe_filename(value: str) -> str:
    text = normalize_key(value).lower()
    text = re.sub(r"[^a-z0-9_-]+", "_", text)
    return text.strip("_") or "rf_cnpj"
