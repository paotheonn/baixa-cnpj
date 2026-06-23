"use client"

import { FormEvent, useEffect, useRef, useState } from "react"
import { DatabaseIcon, FolderIcon, PlayIcon } from "lucide-react"

import {
  createRunEventSource,
  fetchMunicipios,
  fetchPipelineOptions,
  pickDirectory,
  startRunJob,
  type MunicipioOption,
  type PipelineOptions,
  type RunEvent,
  type RunPipelineResponse,
} from "@/lib/api"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Checkbox } from "@/components/ui/checkbox"
import {
  Field,
  FieldContent,
  FieldDescription,
  FieldGroup,
  FieldLabel,
  FieldLegend,
  FieldSet,
} from "@/components/ui/field"
import { Separator } from "@/components/ui/separator"
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Spinner } from "@/components/ui/spinner"
import { cn } from "@/lib/utils"

const FALLBACK_OPTIONS: PipelineOptions = {
  tables: [
    "CNAEs",
    "Simples/MEI",
    "Motivos",
    "Naturezas Juridicas",
    "Qualificacoes",
    "Paises",
    "Socios/QSA",
  ],
  cleanup_modes: ["extracted", "none", "all_raw"],
  scope_types: ["uf", "municipio"],
  months: [],
  states: [],
}

const cleanupLabels: Record<string, string> = {
  extracted: "Apagar CSVs extraidos e manter ZIPs",
  none: "Manter todos os brutos",
  all_raw: "Apagar ZIPs e CSVs brutos",
}

function resultFromEvent(event: RunEvent): RunPipelineResponse | null {
  const csvPath = event.data.csv_path
  const parquetPath = event.data.parquet_path
  const rows = event.data.rows
  if (typeof csvPath !== "string" || typeof parquetPath !== "string" || typeof rows !== "number") {
    return null
  }
  return { csv_path: csvPath, parquet_path: parquetPath, rows }
}

function formatLogTime(timestamp: string) {
  return new Date(timestamp).toLocaleTimeString("pt-BR", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  })
}

function logVariant(level: RunEvent["level"]): "outline" | "secondary" | "destructive" {
  if (level === "error") return "destructive"
  if (level === "success") return "secondary"
  return "outline"
}

function logLineClass(level: RunEvent["level"]) {
  return cn(
    "grid grid-cols-[4.75rem_4.5rem_minmax(0,1fr)] items-start gap-2 rounded-md px-2 py-1.5",
    level === "error" && "bg-destructive/10",
    level === "success" && "bg-primary/5"
  )
}

export function PipelineConsole() {
  const [options, setOptions] = useState<PipelineOptions>(FALLBACK_OPTIONS)
  const [month, setMonth] = useState("")
  const [dataDir, setDataDir] = useState("dados")
  const [outputDir, setOutputDir] = useState("saida")
  const [uf, setUf] = useState("")
  const [scopeType, setScopeType] = useState<"uf" | "municipio">("uf")
  const [municipio, setMunicipio] = useState("")
  const [municipios, setMunicipios] = useState<MunicipioOption[]>([])
  const municipiosLoading = month !== "" && uf !== "" && scopeType === "municipio" && municipios.length === 0
  const [selectedTables, setSelectedTables] = useState<string[]>(
    FALLBACK_OPTIONS.tables
  )
  const [cleanupMode, setCleanupMode] = useState<"none" | "extracted" | "all_raw">(
    "extracted"
  )
  const outputName = (() => {
    if (month && uf) {
      const suffix = scopeType === "municipio" && municipio
        ? municipio.toLowerCase().replace(/\s+/g, "_")
        : uf.toLowerCase()
      return `rf_cnpj_${month.replace("-", "_")}_${suffix}`
    }
    return ""
  })()
  const [isPending, setIsPending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<RunPipelineResponse | null>(null)
  const [logs, setLogs] = useState<RunEvent[]>([])
  const eventSourceRef = useRef<EventSource | null>(null)

  useEffect(() => {
    fetchPipelineOptions()
      .then((nextOptions) => {
        setOptions(nextOptions)
        setSelectedTables(nextOptions.tables)
        if (nextOptions.months.length > 0) {
          const first = nextOptions.months[0]
          setMonth(first)
          setUf("PE")
        }
      })
      .catch(() => {
        setOptions(FALLBACK_OPTIONS)
      })
  }, [])

  useEffect(() => {
    return () => eventSourceRef.current?.close()
  }, [])

  useEffect(() => {
    if (!(uf && scopeType === "municipio")) return
    let cancelled = false
    fetchMunicipios(uf, dataDir)
      .then((data) => { if (!cancelled) setMunicipios(data) })
      .catch(() => { if (!cancelled) setMunicipios([]) })
    return () => { cancelled = true }
  }, [uf, scopeType, dataDir])

  function toggleTable(table: string, checked: boolean) {
    setSelectedTables((current) =>
      checked ? [...new Set([...current, table])] : current.filter((item) => item !== table)
    )
  }

  async function pickFolder(
    target: "dataDir" | "outputDir"
  ) {
    try {
      const result = await pickDirectory(target === "dataDir" ? dataDir : outputDir)
      if (result.path) {
        if (target === "dataDir") setDataDir(result.path)
        else setOutputDir(result.path)
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Falha ao selecionar pasta")
    }
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    eventSourceRef.current?.close()
    setIsPending(true)
    setError(null)
    setResult(null)
    setLogs([])

    startRunJob({
        month,
        data_dir: dataDir,
        output_dir: outputDir,
        scope_type: scopeType,
        uf,
        municipio: scopeType === "municipio" ? municipio : null,
        tables: selectedTables,
        cleanup_mode: cleanupMode,
        output_name: outputName,
      })
      .then(({ run_id }) => {
        const source = createRunEventSource(run_id)
        eventSourceRef.current = source
        source.onmessage = (message) => {
          const runEvent = JSON.parse(message.data) as RunEvent
          setLogs((current) => [...current.slice(-199), runEvent])
          if (runEvent.type === "done") {
            const finished = resultFromEvent(runEvent)
            if (finished) setResult(finished)
            setIsPending(false)
            source.close()
          }
          if (runEvent.type === "error") {
            setError(runEvent.message)
            setIsPending(false)
            source.close()
          }
        }
        source.onerror = () => {
          setError("Conexao com logs da execucao foi encerrada inesperadamente")
          setIsPending(false)
          source.close()
        }
      })
      .catch((runError: Error) => {
        setError(runError.message)
        setIsPending(false)
      })
  }

  return (
    <main className="rf-grid-bg min-h-screen bg-background text-foreground">
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-5 px-4 py-5 md:px-7 lg:py-7">
        <header className="rf-panel-shadow rounded-2xl border bg-card/90 px-5 py-5 backdrop-blur md:px-6">
          <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
            <div className="flex max-w-3xl flex-col gap-3">
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="default">RF CNPJ Local</Badge>
                <Badge variant="secondary">Processamento local</Badge>
                <Badge variant="outline">FastAPI</Badge>
                <Badge variant="outline">CSV + Parquet</Badge>
              </div>
              <div className="flex flex-col gap-2">
                <h1 className="max-w-3xl text-3xl font-semibold tracking-tight text-balance md:text-4xl lg:text-5xl">
                  Workbench tecnico para montar bases CNPJ da Receita Federal.
                </h1>
                <p className="max-w-2xl text-sm leading-6 text-muted-foreground md:text-base">
                  Selecione o mes e a UF, marque as tabelas auxiliares desejadas. A API Python
                  baixa, cruza e exporta uma base pronta para analise.
                </p>
              </div>
            </div>
            <div className="grid gap-2 text-sm lg:min-w-72">
              <div className="rounded-xl border bg-background/70 p-3">
                <p className="text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground">
                  Status esperado
                </p>
                <p className="mt-1 font-medium">API ativa antes da execucao</p>
              </div>
              <code className="rf-code-chip rounded-lg px-3 py-2 font-mono text-xs">
                python -m rf_cnpj api
              </code>
            </div>
          </div>
        </header>

        <form onSubmit={submit} className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_25rem]">
          <section className="flex flex-col gap-5">
            <Card className="rf-panel-shadow border bg-card/95">
              <CardHeader>
                <CardTitle>Mes e UF</CardTitle>
                <CardDescription>
                  Selecione o mes disponivel na Receita Federal e a UF de interesse.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <FieldGroup className="gap-4">
                  <div className="grid gap-4 md:grid-cols-2">
                    <Field>
                      <FieldLabel htmlFor="month">Mes RF</FieldLabel>
                      <Select value={month} onValueChange={(value) => { if (value) setMonth(value) }}>
                        <SelectTrigger id="month" aria-label="Mes RF" className="w-full">
                          <SelectValue placeholder="Selecione o mes" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectGroup>
                            {options.months.map((m) => (
                              <SelectItem key={m} value={m}>{m}</SelectItem>
                            ))}
                          </SelectGroup>
                        </SelectContent>
                      </Select>
                    </Field>
                    <Field>
                      <FieldLabel htmlFor="uf">UF</FieldLabel>
                      <Select value={uf} onValueChange={(value) => { if (value) setUf(value) }}>
                        <SelectTrigger id="uf" aria-label="UF" className="w-full">
                          <SelectValue placeholder="Selecione a UF" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectGroup>
                            {options.states.map((s) => (
                              <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>
                            ))}
                          </SelectGroup>
                        </SelectContent>
                      </Select>
                    </Field>
                  </div>
                  <FieldSet className="mt-4">
                    <FieldLegend>Escopo geografico</FieldLegend>
                    <FieldGroup className="flex gap-4">
                      <Field orientation="horizontal">
                        <input
                          type="radio"
                          id="scope-uf"
                          name="scope_type"
                          value="uf"
                          checked={scopeType === "uf"}
                          onChange={() => setScopeType("uf")}
                          className="mt-1"
                        />
                        <FieldLabel htmlFor="scope-uf">UF inteira</FieldLabel>
                      </Field>
                      <Field orientation="horizontal">
                        <input
                          type="radio"
                          id="scope-municipio"
                          name="scope_type"
                          value="municipio"
                          checked={scopeType === "municipio"}
                          onChange={() => setScopeType("municipio")}
                          className="mt-1"
                        />
                        <FieldLabel htmlFor="scope-municipio">Municipio</FieldLabel>
                      </Field>
                    </FieldGroup>
                    {scopeType === "municipio" && (
                      <Field className="mt-3">
                        <FieldLabel htmlFor="municipio">Municipio</FieldLabel>
                        <Select
                          value={municipio}
                          onValueChange={(value) => { if (value) setMunicipio(value) }}
                        >
                          <SelectTrigger id="municipio" aria-label="Municipio" className="w-full">
                            <SelectValue placeholder={municipiosLoading ? "Carregando..." : "Selecione o municipio"} />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectGroup>
                              {municipios.map((m) => (
                                <SelectItem key={m.value} value={m.value}>{m.label}</SelectItem>
                              ))}
                            </SelectGroup>
                          </SelectContent>
                        </Select>
                      </Field>
                    )}
                  </FieldSet>
                </FieldGroup>
              </CardContent>
            </Card>

            <Card className="rf-panel-shadow border bg-card/95">
              <CardHeader>
                <div className="flex flex-col gap-1 md:flex-row md:items-start md:justify-between">
                  <div>
                    <CardTitle>Tabelas auxiliares</CardTitle>
                    <CardDescription>
                      Selecione somente os cruzamentos necessarios para o arquivo final.
                    </CardDescription>
                  </div>
                  <Badge variant="outline" className="w-fit">
                    {selectedTables.length}/{options.tables.length} ativas
                  </Badge>
                </div>
              </CardHeader>
              <CardContent>
                <FieldSet>
                  <FieldLegend>Crosswalk da Receita Federal</FieldLegend>
                  <FieldDescription>
                    As tabelas marcadas precisam existir depois do download e extracao.
                  </FieldDescription>
                  <FieldGroup data-slot="checkbox-group" className="grid gap-3 md:grid-cols-2">
                    {options.tables.map((table) => {
                      const checked = selectedTables.includes(table)
                      const tableId = `table-${table.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`
                      const descriptionId = `${tableId}-description`
                      return (
                        <Field
                          key={table}
                          orientation="horizontal"
                          className="rounded-lg border bg-background/60 p-3"
                        >
                          <Checkbox
                            id={tableId}
                            aria-describedby={descriptionId}
                            checked={checked}
                            onCheckedChange={(value) => toggleTable(table, Boolean(value))}
                          />
                          <FieldContent>
                            <FieldLabel htmlFor={tableId}>{table}</FieldLabel>
                            <FieldDescription id={descriptionId}>
                              {table === "Socios/QSA"
                                ? "Agrega socios na mesma linha do CNPJ."
                                : "Inclui descricao amigavel no arquivo final."}
                            </FieldDescription>
                          </FieldContent>
                        </Field>
                      )
                    })}
                  </FieldGroup>
                </FieldSet>
              </CardContent>
            </Card>
          </section>

          <aside className="flex flex-col gap-5 lg:sticky lg:top-6 lg:self-start">
            <Card className="rf-panel-shadow border bg-card/95">
              <CardHeader>
                <CardTitle>Execucao</CardTitle>
                <CardDescription>Saida, limpeza e disparo da pipeline.</CardDescription>
              </CardHeader>
              <CardContent>
                <FieldGroup className="gap-4">
                  <Field>
                    <div className="flex w-full items-end gap-2">
                      <div className="flex flex-1 flex-col gap-0.5">
                        <FieldLabel htmlFor="data-dir">Diretorio de dados</FieldLabel>
                        <div className="rf-code-chip flex h-8 items-center rounded-lg px-3 font-mono text-xs" id="data-dir" aria-label="Diretorio de dados">
                          {dataDir}
                        </div>
                      </div>
                      <Button type="button" variant="outline" size="sm" onClick={() => pickFolder("dataDir")} className="shrink-0">
                        <FolderIcon data-icon="inline-start" />
                        Pasta
                      </Button>
                    </div>
                  </Field>
                  <Field>
                    <div className="flex w-full items-end gap-2">
                      <div className="flex flex-1 flex-col gap-0.5">
                        <FieldLabel htmlFor="output-dir">Diretorio de saida</FieldLabel>
                        <div className="rf-code-chip flex h-8 items-center rounded-lg px-3 font-mono text-xs" id="output-dir" aria-label="Diretorio de saida">
                          {outputDir}
                        </div>
                      </div>
                      <Button type="button" variant="outline" size="sm" onClick={() => pickFolder("outputDir")} className="shrink-0">
                        <FolderIcon data-icon="inline-start" />
                        Pasta
                      </Button>
                    </div>
                  </Field>
                  <Field>
                    <FieldLabel htmlFor="output-name">Nome base</FieldLabel>
                    <div className="rf-code-chip flex h-8 items-center rounded-lg px-3 font-mono text-xs" id="output-name">
                      {outputName || "rf_cnpj"}
                    </div>
                  </Field>
                  <Field>
                    <FieldLabel htmlFor="cleanup-mode">Limpeza</FieldLabel>
                    <Select
                      value={cleanupMode}
                      onValueChange={(value) =>
                        setCleanupMode(value as "none" | "extracted" | "all_raw")
                      }
                    >
                      <SelectTrigger id="cleanup-mode" aria-label="Limpeza" className="w-full">
                        <SelectValue>
                          {cleanupLabels[cleanupMode] ?? cleanupMode}
                        </SelectValue>
                      </SelectTrigger>
                      <SelectContent>
                        <SelectGroup>
                          {options.cleanup_modes.map((mode) => (
                            <SelectItem key={mode} value={mode}>
                              {cleanupLabels[mode] ?? mode}
                            </SelectItem>
                          ))}
                        </SelectGroup>
                      </SelectContent>
                    </Select>
                  </Field>
                </FieldGroup>
              </CardContent>
              <CardFooter className="flex flex-col items-stretch gap-3">
                <Button type="submit" disabled={isPending} className="w-full" size="lg">
                  {isPending ? (
                    <Spinner data-icon="inline-start" />
                  ) : (
                    <PlayIcon data-icon="inline-start" />
                  )}
                  {isPending ? "Processando" : "Executar pipeline"}
                </Button>
                {isPending ? (
                  <div className="flex items-center justify-center gap-2 rounded-lg border bg-background/60 p-2">
                    <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
                      <div className="h-full w-1/3 animate-indeterminate rounded-full bg-primary" />
                    </div>
                  </div>
                ) : null}
              </CardFooter>
            </Card>

            {logs.length > 0 ? (
              <Card size="sm" className="border bg-card/90">
                <CardHeader>
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex flex-col gap-1">
                      <CardTitle>Logs da execucao</CardTitle>
                      <CardDescription>Download, extracao, processamento e erros em tempo real.</CardDescription>
                    </div>
                    <Badge variant="outline">{logs.length}</Badge>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="max-h-80 overflow-y-auto rounded-lg border bg-background/80 p-2 font-mono text-xs">
                    {logs.map((log, index) => (
                      <div key={`${log.timestamp}-${index}`} className={logLineClass(log.level)}>
                        <span className="text-muted-foreground">{formatLogTime(log.timestamp)}</span>
                        <Badge variant={logVariant(log.level)} className="font-sans">
                          {log.level}
                        </Badge>
                        <span className="min-w-0 break-words leading-5">{log.message}</span>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            ) : null}

            {error ? (
              <Alert variant="destructive">
                <AlertTitle>Falha na execucao</AlertTitle>
                <AlertDescription className="break-words">{error}</AlertDescription>
              </Alert>
            ) : null}

            {result ? (
              <Alert>
                <DatabaseIcon data-icon="inline-start" />
                <AlertTitle>Exportacao concluida</AlertTitle>
                <AlertDescription className="flex flex-col gap-1 break-words">
                  <span>{result.rows.toLocaleString("pt-BR")} registros.</span>
                  <span>CSV: {result.csv_path}</span>
                  <span>Parquet: {result.parquet_path}</span>
                </AlertDescription>
              </Alert>
            ) : null}

            <Card size="sm" className="border bg-card/90">
              <CardHeader>
                <CardTitle>Operacao local</CardTitle>
                <CardDescription>Use dois terminais nesta pasta.</CardDescription>
              </CardHeader>
              <CardContent className="flex flex-col gap-2">
                <code className="rf-code-chip rounded-lg px-3 py-2 font-mono text-xs">
                  python -m rf_cnpj api
                </code>
                <code className="rf-code-chip rounded-lg px-3 py-2 font-mono text-xs">
                  python -m rf_cnpj web
                </code>
              </CardContent>
            </Card>

            <Separator />

            <div className="grid grid-cols-3 gap-2 text-center text-xs text-muted-foreground">
              <div className="rounded-lg border bg-background/60 p-2">
                <p className="font-medium text-foreground">CSV</p>
                <p>export</p>
              </div>
              <div className="rounded-lg border bg-background/60 p-2">
                <p className="font-medium text-foreground">Parquet</p>
                <p>analytics</p>
              </div>
              <div className="rounded-lg border bg-background/60 p-2">
                <p className="font-medium text-foreground">QSA</p>
                <p>agregado</p>
              </div>
            </div>
          </aside>
        </form>
      </div>
    </main>
  )
}
