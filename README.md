# RF CNPJ

Pipeline local e open source para baixar, cruzar e exportar bases públicas de CNPJ da Receita Federal sem editar código.

O projeto usa um núcleo Python para download/processamento, uma API local FastAPI e uma interface Next.js com shadcn/ui. A interface chama a API local, que baixa automaticamente os arquivos da RF, cruza as tabelas selecionadas e gera saídas em CSV e Parquet.

## Status

MVP em Pandas com chunks. A arquitetura separa núcleo, API e interface para permitir uma evolução futura para DuckDB ou outra UI sem reescrever o processamento.

## Funcionalidades

- Interface local em Next.js + shadcn/ui.
- API local com FastAPI.
- Comando `rf-cnpj api` para abrir a API.
- Comando `rf-cnpj web` para abrir o frontend Next.js a partir da raiz do repo.
- Download automático dos ZIPs da Receita Federal.
- Processamento por UF inteira ou município específico.
- Tabelas auxiliares selecionáveis:
  - CNAEs
  - Simples/MEI
  - Motivos de situação cadastral
  - Naturezas jurídicas
  - Qualificações
  - Países
  - Sócios/QSA
- Sócios agregados em uma linha por CNPJ.
- Exportação simultânea para CSV e Parquet.
- Opções de limpeza dos arquivos brutos após exportar.

> **Tempo de execução estimado:** 1h30 a 2h para uma UF inteira (download + processamento + exportação), dependendo da conexão e do hardware.

## Limites do MVP

- Brasil inteiro não é foco do MVP.
- Geocodificação não faz parte do núcleo inicial.
- A base pública da RF não fornece e-mail pessoal de sócios. O campo `EMAIL` vem do estabelecimento.

## Instalação

Instale o backend Python:

```bash
pip install -r requirements.txt
pip install .
```

Instale o frontend:

```bash
cd web
npm install
```

## Uso

Abra dois terminais na raiz do repositório.

Terminal 1, API local:

```bash
rf-cnpj api
```

Terminal 2, interface web:

```bash
rf-cnpj web
```

Se o Windows não encontrar `rf-cnpj`, rode pelos módulos Python sem depender do PATH:

```bash
python -m rf_cnpj api
python -m rf_cnpj web
```

Alternativa sem instalar o pacote Python:

```bash
python -m uvicorn rf_cnpj.api.app:app --reload
cd web
npm run dev
```

Depois abra `http://localhost:3000`.

Na interface, selecione:

1. Mês da base RF.
2. Escopo: UF inteira ou município.
3. Tabelas auxiliares.
4. Diretório de dados e saída.
5. Política de limpeza.

Ao finalizar, o app gera dois arquivos:

- `<nome>.csv`
- `<nome>.parquet`

## Estrutura

```text
rf_cnpj/
  api/                  # FastAPI local
  core/                 # Download, extração, schemas, normalização, exportação
  engines/              # Engine Pandas atual
web/                    # Next.js + shadcn/ui
tests/                  # Testes com fixtures pequenas
pyproject.toml          # Package metadata e entrypoint rf-cnpj
requirements.txt        # Dependências Python runtime/teste
```

## Desenvolvimento

Backend:

```bash
python -m pytest -q
```

Frontend:

```bash
cd web
npm run lint
npm run build
```

O núcleo foi desenhado para que a API apenas monte um `RunConfig` e chame `PipelineRunner`. Isso facilita substituir a engine Pandas por DuckDB depois, ou expor o mesmo núcleo para outra interface.
