import { apiFetch } from './http'
import type { HarnessJobRequest, HarnessJobResponse } from './types'

export function createHarnessJob(payload: HarnessJobRequest) {
  return apiFetch<HarnessJobResponse>('/harness/jobs', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}
