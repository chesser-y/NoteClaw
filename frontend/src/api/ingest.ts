import { apiFetch, API_BASE } from './http'
import type { ContentType, IngestRequest, IngestResponse } from './types'

export function ingestContent(payload: IngestRequest) {
  return apiFetch<IngestResponse>('/ingest', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function ingestFile(file: File, contentType?: ContentType, source?: string) {
  const form = new FormData()
  form.append('file', file)
  if (contentType) form.append('content_type', contentType)
  if (source) form.append('source', source)

  const response = await fetch(`${API_BASE}/ingest/files`, {
    method: 'POST',
    body: form,
  })

  if (!response.ok) {
    throw new Error(await response.text())
  }

  return response.json() as Promise<IngestResponse>
}
