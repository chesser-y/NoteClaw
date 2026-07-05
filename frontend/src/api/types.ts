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

export type NoteDetail = NoteListItem & {
  content: string
  metadata?: Record<string, unknown> | null
  chunks?: { id: string; note_id: string; text: string; chunk_index: number; score?: number | null }[]
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
    source?: string | null
    source_contains?: string | null
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
  summary?: string | null
  source?: string | null
  source_url?: string | null
  created_at?: string | null
  updated_at?: string | null
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

export type ChatReasoningMode = 'normal' | 'deep' | 'web' | 'agent'

export type AgentRole = 'coordinator' | 'researcher' | 'reasoner' | 'reviewer'

export type AgentStep = {
  role: AgentRole
  title: string
  output?: string | null
  duration_ms?: number | null
  citations?: Citation[]
}

export type AgentReview = {
  verdict?: string | null
  confidence?: number | null
  risks?: string[]
  needs_user_confirmation?: boolean
}

export type ChatMessageRequest = {
  message: string
  retrieval_mode: SearchMode
  use_nanobot_reasoning?: boolean
  use_web_research?: boolean
  reasoning_mode?: ChatReasoningMode
  top_k?: number
  max_reasoning_steps?: number
  web_results?: number
  fetch_web_pages?: boolean
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
    steps?: AgentStep[]
    plan?: string[]
    review?: AgentReview | null
    workflow_id?: string | null
  }
}

export type ChatStreamStatus = {
  stage?: string
  message?: string
  progress?: number
  reasoning_mode?: ChatReasoningMode
  citation_count?: number
  plan?: string[]
  workflow_id?: string | null
  task_id?: string | null
  review?: AgentReview | Record<string, unknown> | null
  [key: string]: unknown
}

export type WebSource = {
  title: string
  url: string
  snippet?: string
  content?: string | null
  score?: number | null
  provider?: string | null
  metadata?: Record<string, unknown>
}

export type EvidenceAnchor = {
  id: string
  source_type: string
  title: string
  snippet: string
  url?: string | null
  note_id?: string | null
  chunk_id?: string | null
  score?: number | null
  metadata?: Record<string, unknown>
}

export type NanobotResearchRequest = {
  question: string
  retrieval_mode?: SearchMode
  scope?: Scope
  top_k?: number
  max_steps?: number
  max_sub_questions?: number
  use_web?: boolean
  web_results?: number
  fetch_web_pages?: boolean
  save_web_evidence?: boolean
}

export type NanobotResearchStep = {
  step_index: number
  objective: string
  action: string
  local_citations: Citation[]
  web_sources: WebSource[]
  evidence_anchors: EvidenceAnchor[]
  observation: string
}

export type NanobotResearchResponse = {
  question: string
  answer: string
  plan: string[]
  steps: NanobotResearchStep[]
  citations: Citation[]
  web_sources: WebSource[]
  evidence_anchors: EvidenceAnchor[]
  trace: Record<string, unknown>
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
  html_slides?: string[]
  note_id?: string | null
  artifact_url?: string | null
  download_url?: string | null
  document_extension?: string | null
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

export type KGNodeType = 'tag' | 'note' | 'category' | 'content_type'
export type KGEdgeType = 'has_tag' | 'tag_cooccurs' | 'category_tag' | 'content_type_tag'

export type KGNode = {
  id: string
  label: string
  type: KGNodeType
  weight?: number
  metadata?: Record<string, unknown>
}

export type KGEdge = {
  id: string
  source: string
  target: string
  type: KGEdgeType
  weight?: number
  note_ids?: string[]
}

export type KGStats = {
  note_count: number
  tag_count: number
  category_count?: number
  content_type_count?: number
  edge_count: number
  max_tag_weight?: number
  max_edge_weight?: number
}

export type KGResponse = {
  nodes: KGNode[]
  edges: KGEdge[]
  stats: KGStats
}
