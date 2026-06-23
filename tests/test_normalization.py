import pandas as pd

from rf_cnpj.core.normalization import (
    build_full_address,
    format_cnpj,
    format_date,
    format_phone,
    normalize_capital,
)


def test_formats_cnpj_from_rf_parts():
    assert format_cnpj("12345678", "1", "9") == "12.345.678/0001-09"


def test_formats_rf_dates_and_empty_values():
    assert format_date("20240229") == "29/02/2024"
    assert format_date(pd.NA) == ""
    assert format_date("") == ""


def test_formats_phone_without_leaking_nan():
    assert format_phone("81", "99998888") == "(81) 99998888"
    assert format_phone("", "99998888") == "99998888"
    assert format_phone("81", pd.NA) == ""


def test_builds_full_address_without_nan_fragments():
    assert build_full_address("AVENIDA", "BRASIL", "100", pd.NA) == "AVENIDA BRASIL, 100"


def test_normalizes_capital_to_brazilian_currency_text():
    assert normalize_capital("1234,5") == "1.234,50"
    assert normalize_capital("0") == "0,00"
