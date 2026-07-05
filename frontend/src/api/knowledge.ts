import { apiFetch } from './http'
import type { ContentType, KGResponse, KnowledgeListResponse, NoteDetail } from './types'

export function listKnowledge(params: {
  q?: string
  content_type?: ContentType | ''
  tag?: string[]
  category?: string
  source?: string
  date_from?: string
  date_to?: string
  limit?: number
  offset?: number
}) {
  const query = new URLSearchParams()
  if (params.q) query.set('q', params.q)
  if (params.content_type) query.set('content_type', params.content_type)
  params.tag?.forEach((tag) => query.append('tag', tag))
  if (params.category) query.set('category', params.category)
  if (params.source) query.set('source', params.source)
  if (params.date_from) query.set('date_from', params.date_from)
  if (params.date_to) query.set('date_to', params.date_to)
  query.set('limit', String(params.limit ?? 20))
  query.set('offset', String(params.offset ?? 0))

  return apiFetch<KnowledgeListResponse>(`/knowledge?${query.toString()}`)
}

export function getKnowledge(noteId: string) {
  return apiFetch<NoteDetail>(`/knowledge/${noteId}`)
}

export type Facets = {
  tags: [string, number][]
  sources: string[]
  categories: string[]
  content_types: string[]
}

export function getKnowledgeFacets() {
  return apiFetch<Facets>('/knowledge/_facets')
}

export function getKnowledgeGraph(params: {
  include_notes?: boolean
  include_categories?: boolean
  include_content_types?: boolean
  min_tag_count?: number
  min_edge_weight?: number
  limit_tags?: number
  limit_notes?: number
  focus_tag?: string
} = {}) {
  const query = new URLSearchParams()
  if (params.include_notes) query.set('include_notes', 'true')
  if (params.include_categories) query.set('include_categories', 'true')
  if (params.include_content_types) query.set('include_content_types', 'true')
  if (params.min_tag_count != null) query.set('min_tag_count', String(params.min_tag_count))
  if (params.min_edge_weight != null) query.set('min_edge_weight', String(params.min_edge_weight))
  if (params.limit_tags != null) query.set('limit_tags', String(params.limit_tags))
  if (params.limit_notes != null) query.set('limit_notes', String(params.limit_notes))
  if (params.focus_tag) query.set('focus_tag', params.focus_tag)
  return apiFetch<KGResponse>(`/knowledge/graph?${query.toString()}`)
}
