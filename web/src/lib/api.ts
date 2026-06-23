export type StateOption = {
  value: string
  label: string
}

export type PipelineOptions = {
  tables: string[]
  cleanup_modes: string[]
  scope_types: Array<"uf" | "municipio">
  months: string[]
  states: StateOption[]
}

export type PickDirectoryResponse = {
  path: string | null
}

export type MunicipioOption = {
  value: string
  label: string
}

export type RunPipelinePayload = {
  month: string
  data_dir: string
  output_dir: string
  scope_type: "uf" | "municipio"
  uf: string
  municipio?: string | null
  tables: string[]
  cleanup_mode: "none" | "extracted" | "all_raw"
  output_name: string
}

export type RunPipelineResponse = {
  csv_path: string
  parquet_path: string
  rows: number
}

export type StartRunJobResponse = {
  run_id: string
}

export type RunEvent = {
  type: string
  level: "info" | "success" | "error"
  message: string
  timestamp: string
  data: Record<string, unknown>
}

const API_BASE_URL =
  process.env.NEXT_PUBLIC_RF_CNPJ_API_URL ?? "http://127.0.0.1:8000"

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  })

  if (!response.ok) {
    const detail = await response.text()
    throw new Error(detail || `Request failed with status ${response.status}`)
  }

  return response.json() as Promise<T>
}

export function fetchPipelineOptions(): Promise<PipelineOptions> {
  return request<PipelineOptions>("/options")
}

export function runPipeline(
  payload: RunPipelinePayload
): Promise<RunPipelineResponse> {
  return request<RunPipelineResponse>("/runs", {
    method: "POST",
    body: JSON.stringify(payload),
  })
}

export function startRunJob(
  payload: RunPipelinePayload
): Promise<StartRunJobResponse> {
  return request<StartRunJobResponse>("/runs/jobs", {
    method: "POST",
    body: JSON.stringify(payload),
  })
}

export function createRunEventSource(runId: string): EventSource {
  return new EventSource(`${API_BASE_URL}/runs/${encodeURIComponent(runId)}/events`)
}

export function pickDirectory(
  initial_dir?: string
): Promise<PickDirectoryResponse> {
  return request<PickDirectoryResponse>("/directories/pick", {
    method: "POST",
    body: JSON.stringify({ initial_dir }),
  })
}

export function fetchMunicipios(uf: string, dataDir?: string): Promise<MunicipioOption[]> {
  const params = new URLSearchParams({ uf })
  if (dataDir) params.set("data_dir", dataDir)
  return request<MunicipioOption[]>(`/municipios?${params.toString()}`)
}
