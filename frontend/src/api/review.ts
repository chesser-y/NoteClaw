import { apiFetch } from './http'

export type DraftItem = {
  id: string
  title: string
  summary: string
  generation_type?: string
  prompt?: string
  created_at?: string
  download_url?: string | null
  note_id: string
}

export type LowConfidenceItem = {
  id: string
  title: string
  answer: string
  question: string
  confidence?: number | null
  verdict?: string | null
  risks: string[]
  session_id?: string | null
  created_at?: string
  note_id: string
}

export type DuplicateItem = {
  id: string
  type: string
  payload: {
    note_a: string
    note_b: string
    title_a: string
    title_b: string
    score: number
  }
  status: string
  created_at: string
}

export type ReviewItemsResponse = {
  drafts: { total: number; items: DraftItem[] }
  low_confidence: { total: number; items: LowConfidenceItem[] }
  duplicates: { total: number; items: DuplicateItem[] }
}

export function listReviewItems() {
  return apiFetch<ReviewItemsResponse>('/review/items')
}

export function actOnReviewItem(itemId: string, action: 'approve' | 'reject' | 'defer') {
  return apiFetch<{ status: string; id: string }>(`/review/items/${itemId}/action`, {
    method: 'POST',
    body: JSON.stringify({ action }),
  })
}

export function runDuplicateDetection() {
  return apiFetch<{ inserted: number; total_found: number }>('/review/duplicates/run', {
    method: 'POST',
  })
}
