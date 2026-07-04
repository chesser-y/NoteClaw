import { apiFetch } from './http'
import type { SearchRequest, SearchResponse } from './types'

export function searchKnowledge(payload: SearchRequest) {
  return apiFetch<SearchResponse>('/search', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}
