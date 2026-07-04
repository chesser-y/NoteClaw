export type ContentType =
  | 'text'
  | 'code'
  | 'table'
  | 'image'
  | 'document'
  | 'webpage'
  | 'repository'

export type TaskStatus = 'queued' | 'running' | 'succeeded' | 'failed' | 'cancelled'
export type SearchMode = 'keyword' | 'semantic' | 'hybrid'

export type GenerationType =
  | 'learning_note'
  | 'technical_summary'
  | 'report_draft'
  | 'ppt_outline'
  | 'pptx'
  | 'mind_map'
  | 'table'
  | 'image'
  | 'diagram'
  | 'video_script'

export type Scope = {
  note_ids?: string[]
  tags?: string[]
  content_types?: ContentType[]
}

export type Citation = {
  note_id: string
  chunk_id?: string | null
  title: string
  snippet: string
  score?: number | null
}

export type IngestRequest = {
  content_type: ContentType
  content: string
  title?: string | null
  source?: string | null
  source_url?: string | null
  metadata?: Record<string, unknown>
}

export type IngestResponse = {
  note_id: string
  task_id?: string | null
  status: TaskStatus
  message: string
}

export type NoteListItem = {
  id: string
  title: string
  content_type: ContentType
  summary?: string | null
  tags: string[]
  category?: string | null
  source?: string | null
  source_url?: string | null
  status: string
  created_at: string
  updated_at: string
}

export type KnowledgeListResponse = {
  items: NoteListItem[]
  total: number
  limit: number
  offset: number
}

export type SearchRequest = {
  query: string
  mode: SearchMode
  filters: {
    content_types: ContentType[]
    tags: string[]
    category: string | null
    date_from: string | null
    date_to: string | null
  }
  limit: number
}

export type SearchResult = {
  note_id: string
  chunk_id?: string | null
  title: string
  snippet: string
  score?: number | null
  content_type: ContentType
  tags: string[]
  source?: string | null
}

export type SearchResponse = {
  query: string
  mode: SearchMode
  results: SearchResult[]
}

export type ChatSessionCreate = {
  title?: string | null
  scope?: Scope
}

export type ChatSessionRead = {
  id: string
  title: string
  created_at: string
}

export type ChatMessageRequest = {
  message: string
  retrieval_mode: SearchMode
  use_nanobot_reasoning: boolean
  top_k: number
}

export type ChatMessageResponse = {
  message_id: string
  answer: string
  citations: Citation[]
  trace: {
    retrieval_mode: SearchMode
    used_nanobot: boolean
    model?: string | null
    metadata?: Record<string, unknown>
  }
}

export type GenerationRequest = {
  generation_type: GenerationType
  prompt: string
  scope?: Scope
  options?: {
    slide_count?: number | null
    theme?: string | null
    include_generated_images?: boolean
    output_format?: string | null
    extra?: Record<string, unknown>
  }
}

export type GenerationTaskResponse = {
  task_id: string
  status: TaskStatus
  message: string
}

export type GenerationPreviewResponse = {
  generation_type: GenerationType
  content: Record<string, unknown> | string
  citations: Citation[]
}

export type TaskRead = {
  id: string
  type: string
  status: TaskStatus
  progress: number
  message?: string | null
  result?: Record<string, unknown> | null
  error?: string | null
  created_at: string
  updated_at: string
}

export type TaskListResponse = {
  items: TaskRead[]
  total: number
  limit: number
  offset: number
}

export type HarnessJobRequest = {
  job_type: string
  instruction: string
  inputs?: Record<string, unknown>
}

export type HarnessJobResponse = {
  task_id: string
  status: TaskStatus
  message: string
}
