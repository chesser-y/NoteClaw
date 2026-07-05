import { apiFetch } from './http'
import type { GenerationPreviewResponse, GenerationRequest, GenerationTaskResponse } from './types'

export function previewGeneration(payload: GenerationRequest) {
  return apiFetch<GenerationPreviewResponse>('/generate/preview', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function createGenerationTask(payload: GenerationRequest) {
  return apiFetch<GenerationTaskResponse>('/generate', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}
