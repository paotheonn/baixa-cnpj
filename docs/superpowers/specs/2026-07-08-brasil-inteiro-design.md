# Design: Escopo "Brasil inteiro"

## Contexto

O pipeline RF CNPJ hoje suporta dois escopos de processamento: uma UF inteira
(`Scope.type == "uf"`) ou um município específico (`Scope.type == "municipio"`).
O README lista "Brasil inteiro" como fora do escopo do MVP.

O motivo técnico é a engine Pandas (`rf_cnpj/engines/pandas_engine.py`), que
carrega todos os estabelecimentos filtrados em memória (`pd.concat` de chunks),
depois cruza empresas/sócios/simples pelo conjunto de `CNPJ_BASE`. Isso funciona
para uma UF ou município, mas o Brasil inteiro (~60M estabelecimentos, ~50M
empresas, dezenas de milhões de sócios) não cabe em RAM com essa abordagem.

Este design adiciona o escopo "Brasil inteiro" reaproveitando a engine atual,
sem reescrevê-la, através de um loop por UF com escrita incremental e retomada.

## Objetivo

Permitir que o usuário selecione "Brasil inteiro" na interface e obtenha os dois
arquivos de saída únicos (`.csv` e `.parquet`) contendo todos os estabelecimentos
das 27 UFs, de forma segura em memória e resiliente a falhas em execuções longas.

## Estratégia

Loop por UF reaproveitando a engine Pandas atual. Para cada UF, chamamos a engine
com `Scope(type="uf", uf=<sigla>)`, escrevemos o resultado dessa UF num par de
arquivos temporários, registramos a UF num manifesto de checkpoint e, ao concluir
as 27, fazemos o merge de todas as partes nos arquivos únicos finais.

Download e extração dos ZIPs acontecem **uma única vez** — os arquivos brutos da RF
já são do Brasil inteiro e não dependem de UF. O loop ocorre apenas na fase de
processamento.

### Por que partes temporárias + merge (e não append direto)

Um `ParquetWriter` append-only não permite "desfazer" uma UF parcialmente escrita
após um crash. Gravando cada UF concluída em arquivos temporários separados
(`.parts/<UF>.csv` e `.parts/<UF>.parquet`) e só então registrando no manifesto,
uma UF interrompida no meio é simplesmente refeita (a parte parcial é descartada).
O custo é espaço de disco temporário e um passo de merge no final.

## Componentes

### 1. `core/models.py` — Scope

- `Scope.type` passa a aceitar `"brasil"` além de `"uf"` e `"municipio"`.
- Validação condicional: quando `type == "brasil"`, não exige `uf` nem `municipio`.
  As validações atuais de `uf` (2 letras) e `municipio` (obrigatório para
  `municipio`) permanecem intactas para os outros tipos.
- Para `"brasil"`, `uf`/`municipio` são normalizados como estão (podem ficar vazios).

### 2. `core/output.py` — escrita incremental, checkpoint e merge

Novo `IncrementalUFExporter` (ou conjunto de funções) responsável por:

- **Layout de saída temporária**: pasta `<output_dir>/<base_name>.parts/` contendo
  um par `<UF>.csv` + `<UF>.parquet` por UF concluída.
- **Manifesto**: `<output_dir>/<base_name>.manifest.json` registrando:
  - `month`, `base_name`, `columns` (FINAL_COLUMNS), lista de UFs concluídas com
    contagem de linhas, e `status` (`"in_progress"` / `"done"`).
- **`write_uf(uf, df)`**: grava a parte da UF (CSV + Parquet) e atualiza o manifesto
  só após ambos os arquivos ficarem completos.
- **`completed_ufs()`**: lê o manifesto e retorna as UFs já concluídas (para retomada).
- **`merge()`**: concatena todas as partes (ordem de `FINAL_COLUMNS`, concat vertical)
  em `<base_name>.csv` (por append de blocos) e `<base_name>.parquet`
  (via `ParquetWriter` acumulando row-groups), retornando `ExportResult`.
- **`cleanup()`**: após merge bem-sucedido, remove `.parts/` e o manifesto.

A função `export_csv_and_parquet` existente permanece inalterada (usada pelos
escopos UF/município).

### 3. `core/processor.py` — orquestração

- `PipelineRunner.run` detecta `scope.type == "brasil"` e chama um novo método
  `_run_brasil(config, emit, downloader, extractor, raw_month_dir)`.
- Fase de download + extração: idêntica ao fluxo atual, executada uma vez.
- Fase de processamento (loop):
  - Instancia o `IncrementalUFExporter` com base em `config.output_dir` e
    `config.output_name`.
  - Lê `completed_ufs()` para retomar (pula UFs já feitas).
  - Para cada UF em `BRAZIL_STATES` (ordem estável) ainda não concluída:
    - Emite `uf_start` com `{"uf": <sigla>, "index": i, "total": 27}`.
    - Chama `self.engine.process(raw_month_dir, Scope("uf", uf), options)`.
    - `exporter.write_uf(uf, df)`.
    - Emite `uf_done` com `{"uf": <sigla>, "index": i, "total": 27, "rows": n}`.
  - Após todas as UFs: `result = exporter.merge()`, emite `export_done`.
  - `exporter.cleanup()`.
  - Aplica cleanup dos brutos (`cleanup_raw_files`) como hoje.
  - Emite `done`.
- Eventos existentes (`pipeline_start`, `download_*`, `extract_*`, `error`, etc.)
  são reutilizados. O console SSE do frontend já renderiza eventos genéricos.

### 4. `core/ui_options.py` — nome de saída

- `build_output_name(month, uf, municipio=None, scope_type="uf")` ganha suporte a
  Brasil: quando escopo é brasil, retorna `rf_cnpj_<month>_BR`.

### 5. `api/app.py` — API

- `RunRequest`:
  - `scope_type` aceita `"brasil"`.
  - `uf` passa a ser opcional (default vazio) e `municipio` opcional; validação de
    UF de 2 letras só se aplica quando `scope_type != "brasil"` (validação no
    `_run_config`/`Scope`).
- `/options`: `scope_types` inclui `"brasil"`.
- `_run_config`: monta `Scope(type="brasil", uf=request.uf or "", municipio=None)`
  quando brasil.

### 6. Frontend (`web/src/lib/api.ts` + `components/pipeline-console.tsx`)

- Tipos `scope_type` incluem `"brasil"`.
- Terceira opção de rádio no "Escopo geográfico": "Brasil inteiro".
- Quando `brasil` selecionado: escondem-se os seletores de UF e Município; o payload
  envia `uf: ""`, `municipio: null`.
- `outputName` para brasil: `rf_cnpj_<month>_BR`.
- Aviso na UI de que Brasil inteiro é uma execução longa (várias horas).
- Nota: seguir `web/AGENTS.md` — ler `node_modules/next/dist/docs/` antes de
  escrever código de frontend (Next.js 16 com breaking changes).

## Fluxo de dados

```
download (1x) -> extract (1x) -> [loop UF: engine.process -> exporter.write_uf]
                                  -> exporter.merge -> exporter.cleanup -> cleanup brutos
```

## Correção / edge cases

- **Deduplicação**: cada estabelecimento pertence a uma única UF, então não há CNPJ
  repetido entre UFs. A dedup por-UF existente é suficiente; não há dedup global.
- **Colunas idênticas**: todas as UFs produzem `FINAL_COLUMNS` na mesma ordem, então
  o merge é um concat vertical trivial.
- **UF vazia**: se uma UF não tem estabelecimentos, a engine retorna DataFrame vazio
  com `FINAL_COLUMNS`; a parte é gravada vazia (0 linhas) e registrada como concluída.
- **Retomada**: reexecutar com mesmo `month` + `output_dir` + `output_name` detecta o
  manifesto e pula UFs concluídas. Uma UF parcial (crash no meio) não está no manifesto
  e é reprocessada.
- **Performance**: os arquivos grandes (Empresas0-9, Socios0-9, Simples) são relidos
  do disco a cada UF. Aceito como limitação de performance do MVP e documentado.

## Testes

- **Engine/processor brasil**: fixtures com 2-3 UFs → todas as linhas aparecem na
  saída única, ordenadas por UF.
- **IncrementalUFExporter**: `write_uf` de vários lotes + `merge` gera CSV/Parquet
  corretos; `cleanup` remove `.parts` e manifesto.
- **Retomada**: manifesto pré-populado com UFs concluídas → `_run_brasil` pula-as e
  completa o restante; resultado final contém todas as UFs.
- **API**: `scope_type="brasil"` sem `uf` passa validação e chama o runner com
  `Scope.type == "brasil"`; `/options` expõe `"brasil"`.

## Fora de escopo

- Geocodificação (permanece fora do MVP).
- Otimização de performance para não reler arquivos grandes por UF (futuro: engine
  DuckDB).
- Paralelismo entre UFs.
