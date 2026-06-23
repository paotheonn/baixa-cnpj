from rf_cnpj.core.schemas import FINAL_COLUMNS, REQUIRED_DOWNLOAD_GROUPS, SELECTABLE_DOWNLOAD_GROUPS


def test_required_groups_do_not_include_local_customization():
    all_group_names = " ".join(REQUIRED_DOWNLOAD_GROUPS + SELECTABLE_DOWNLOAD_GROUPS).lower()
    all_column_names = " ".join(FINAL_COLUMNS).lower()

    assert "caruaru" not in all_group_names
    assert "via_parque" not in all_column_names
    assert "latitude" not in all_column_names
    assert "longitude" not in all_column_names


def test_final_columns_include_company_contact_address_and_aggregated_partners():
    expected = {
        "CNPJ",
        "RAZAO_SOCIAL",
        "NOME_FANTASIA",
        "EMAIL",
        "TELEFONE_1",
        "ENDERECO_COMPLETO",
        "MUNICIPIO",
        "UF",
        "QTD_SOCIOS",
        "SOCIOS_NOMES",
        "SOCIOS_QUALIFICACOES",
    }

    assert expected.issubset(set(FINAL_COLUMNS))
