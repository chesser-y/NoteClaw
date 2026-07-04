import { apiFetch } from './http'
import type { ContentType, KnowledgeListResponse, NoteListItem } from './types'

export function listKnowledge(params: {
  q?: string
  content_type?: ContentType | ''
  tag?: string[]
  category?: string
  limit?: number
  offset?: number
}) {
  const query = new URLSearchParams()
  if (params.q) query.set('q', params.q)
  if (params.content_type) query.set('content_type', params.content_type)
  params.tag?.forEach((tag) => query.append('tag', tag))
  if (params.category) query.set('category', params.category)
  query.set('limit', String(params.limit ?? 20))
  query.set('offset', String(params.offset ?? 0))

  return apiFetch<KnowledgeListResponse>(`/knowledge?${query.toString()}`)
}

export function getKnowledge(noteId: string) {
  return apiFetch<NoteListItem>(`/knowledge/${noteId}`)
}
