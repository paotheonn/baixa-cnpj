"""Schemas and output column definitions for Receita Federal CNPJ files."""

from __future__ import annotations

RF_ENCODING = "latin-1"
RF_SEPARATOR = ";"

REQUIRED_DOWNLOAD_GROUPS = ["estabelecimentos", "empresas", "municipios"]
SELECTABLE_DOWNLOAD_GROUPS = [
    "cnaes",
    "simples",
    "motivos",
    "naturezas",
    "qualificacoes",
    "paises",
    "socios",
]

DOWNLOAD_GROUP_FILES = {
    "estabelecimentos": [f"Estabelecimentos{i}.zip" for i in range(10)],
    "empresas": [f"Empresas{i}.zip" for i in range(10)],
    "socios": [f"Socios{i}.zip" for i in range(10)],
    "cnaes": ["Cnaes.zip"],
    "simples": ["Simples.zip"],
    "motivos": ["Motivos.zip"],
    "municipios": ["Municipios.zip"],
    "naturezas": ["Naturezas.zip"],
    "qualificacoes": ["Qualificacoes.zip"],
    "paises": ["Paises.zip"],
}

COLUNAS_ESTABELECIMENTOS = [
    "CNPJ_BASE",
    "CNPJ_ORDEM",
    "CNPJ_DV",
    "MATRIZ_FILIAL_CODIGO",
    "NOME_FANTASIA",
    "SITUACAO_CADASTRAL_CODIGO",
    "DATA_SITUACAO_CADASTRAL",
    "MOTIVO_SITUACAO_CADASTRAL_CODIGO",
    "NOME_CIDADE_EXTERIOR",
    "PAIS_CODIGO",
    "DATA_INICIO_ATIVIDADE",
    "CNAE_PRINCIPAL_CODIGO",
    "CNAES_SECUNDARIOS_CODIGOS",
    "TIPO_LOGRADOURO",
    "LOGRADOURO",
    "NUMERO",
    "COMPLEMENTO",
    "BAIRRO",
    "CEP",
    "UF",
    "MUNICIPIO_CODIGO",
    "DDD_1",
    "TELEFONE_1_RAW",
    "DDD_2",
    "TELEFONE_2_RAW",
    "DDD_FAX",
    "FAX_RAW",
    "EMAIL",
    "SITUACAO_ESPECIAL",
    "DATA_SITUACAO_ESPECIAL",
]

COLUNAS_EMPRESAS = [
    "CNPJ_BASE",
    "RAZAO_SOCIAL",
    "NATUREZA_JURIDICA_CODIGO",
    "QUALIFICACAO_RESPONSAVEL_CODIGO",
    "CAPITAL_SOCIAL",
    "PORTE_EMPRESA_CODIGO",
    "ENTE_FEDERATIVO_RESPONSAVEL",
]

COLUNAS_SIMPLES = [
    "CNPJ_BASE",
    "OPCAO_SIMPLES",
    "DATA_EXCLUSAO_SIMPLES",
    "DATA_OPCAO_SIMPLES",
    "OPCAO_MEI",
    "DATA_EXCLUSAO_MEI",
    "DATA_OPCAO_MEI",
]

COLUNAS_SOCIOS = [
    "CNPJ_BASE",
    "IDENTIFICADOR_SOCIO",
    "NOME_SOCIO_RAZAO_SOCIAL",
    "CNPJ_CPF_SOCIO",
    "QUALIFICACAO_SOCIO_CODIGO",
    "DATA_ENTRADA_SOCIEDADE",
    "PAIS_CODIGO",
    "CPF_REPRESENTANTE_LEGAL",
    "NOME_REPRESENTANTE_LEGAL",
    "QUALIFICACAO_REPRESENTANTE_LEGAL_CODIGO",
    "FAIXA_ETARIA_CODIGO",
]

COLUNAS_CODIGO_DESCRICAO = ["CODIGO", "DESCRICAO"]

FINAL_COLUMNS = [
    "CNPJ",
    "CNPJ_BASE",
    "MATRIZ_FILIAL",
    "RAZAO_SOCIAL",
    "NOME_FANTASIA",
    "SITUACAO_CADASTRAL",
    "DATA_SITUACAO_CADASTRAL",
    "MOTIVO_SITUACAO_CADASTRAL",
    "DATA_INICIO_ATIVIDADE",
    "CNAE_PRINCIPAL_CODIGO",
    "CNAE_PRINCIPAL_DESCRICAO",
    "CNAES_SECUNDARIOS",
    "TIPO_LOGRADOURO",
    "LOGRADOURO",
    "NUMERO",
    "COMPLEMENTO",
    "BAIRRO",
    "CEP",
    "UF",
    "MUNICIPIO",
    "MUNICIPIO_CODIGO",
    "ENDERECO_COMPLETO",
    "DDD_1",
    "TELEFONE_1",
    "DDD_2",
    "TELEFONE_2",
    "EMAIL",
    "CAPITAL_SOCIAL",
    "PORTE_EMPRESA",
    "NATUREZA_JURIDICA_CODIGO",
    "NATUREZA_JURIDICA",
    "QUALIFICACAO_RESPONSAVEL",
    "SIMPLES",
    "MEI",
    "QTD_SOCIOS",
    "SOCIOS_NOMES",
    "SOCIOS_QUALIFICACOES",
    "SOCIOS_DATA_ENTRADA",
    "SOCIOS_FAIXA_ETARIA",
    "SOCIOS_PAIS",
    "SOCIOS_REPRESENTANTES_LEGAIS",
]

SITUACAO_CADASTRAL = {
    "01": "NULA",
    "1": "NULA",
    "02": "ATIVA",
    "2": "ATIVA",
    "03": "SUSPENSA",
    "3": "SUSPENSA",
    "04": "INAPTA",
    "4": "INAPTA",
    "08": "BAIXADA",
    "8": "BAIXADA",
}

MATRIZ_FILIAL = {"1": "Matriz", "2": "Filial"}

PORTE_EMPRESA = {
    "00": "NAO INFORMADO",
    "0": "NAO INFORMADO",
    "01": "MICRO EMPRESA",
    "1": "MICRO EMPRESA",
    "03": "EMPRESA DE PEQUENO PORTE",
    "3": "EMPRESA DE PEQUENO PORTE",
    "05": "DEMAIS",
    "5": "DEMAIS",
}

FAIXA_ETARIA_SOCIO = {
    "0": "NAO INFORMADA",
    "1": "0 A 12 ANOS",
    "2": "13 A 20 ANOS",
    "3": "21 A 30 ANOS",
    "4": "31 A 40 ANOS",
    "5": "41 A 50 ANOS",
    "6": "51 A 60 ANOS",
    "7": "61 A 70 ANOS",
    "8": "71 A 80 ANOS",
    "9": "MAIS DE 80 ANOS",
}
