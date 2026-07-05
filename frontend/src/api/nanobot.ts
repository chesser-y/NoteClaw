import { apiFetch } from './http'
import type { NanobotResearchRequest, NanobotResearchResponse } from './types'

export function runNanobotResearch(payload: NanobotResearchRequest) {
  return apiFetch<NanobotResearchResponse>('/nanobot/research', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}
