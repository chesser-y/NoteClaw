import { API_BASE, apiFetch } from './http'
import type {
  ChatMessageRead,
  ChatMessageRequest,
  ChatMessageResponse,
  ChatSessionCreate,
  ChatSessionDetail,
  ChatSessionRead,
  ChatStreamStatus,
} from './types'

export function createChatSession(payload: ChatSessionCreate) {
  return apiFetch<ChatSessionRead>('/chat/sessions', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function listChatSessions(limit = 50, opts?: { favorites?: boolean }) {
  const params = new URLSearchParams({ limit: String(limit) })
  if (opts?.favorites) params.set('favorites_only', 'true')
  return apiFetch<ChatSessionRead[]>(`/chat/sessions?${params.toString()}`)
}

export function getChatSession(id: string) {
  return apiFetch<ChatSessionDetail>(`/chat/sessions/${id}`)
}

export function renameChatSession(id: string, title: string) {
  return apiFetch<ChatSessionRead>(`/chat/sessions/${id}`, {
    method: 'PATCH',
    body: JSON.stringify({ title }),
  })
}

export function deleteChatSession(id: string) {
  return apiFetch<{ deleted: boolean }>(`/chat/sessions/${id}`, {
    method: 'DELETE',
  })
}

export function setSessionFavorite(id: string, isFavorite: boolean) {
  return apiFetch<ChatSessionRead>(`/chat/sessions/${id}/favorite`, {
    method: 'PATCH',
    body: JSON.stringify({ is_favorite: isFavorite }),
  })
}

export function sendChatMessage(sessionId: string, payload: ChatMessageRequest) {
  return apiFetch<ChatMessageResponse>(`/chat/sessions/${sessionId}/messages`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export type StreamStepData = {
  role: string
  phase: 'running' | 'done'
  plan?: string[]
  output?: string
  citations?: Array<{ note_id: string; title?: string; snippet?: string; score?: number }>
  review?: { verdict?: string; confidence?: number; risks?: string[]; suggestions?: string[] }
  message?: string
  progress?: number
}

export type ChatStreamHandlers = {
  onStart?: (data: { reasoning_mode: string; retrieval_mode: string; session_id: string }) => void
  onStep?: (data: StreamStepData) => void
  onDone?: (response: ChatMessageResponse) => void
  onStatus?: (status: ChatStreamStatus) => void
  onDelta?: (delta: string) => void
  onFinal?: (response: ChatMessageResponse) => void
  onError?: (err: string) => void
}

export type StreamHandlers = ChatStreamHandlers

export async function sendChatMessageStream(
  sessionId: string,
  payload: ChatMessageRequest,
  handlers: ChatStreamHandlers,
  signal?: AbortSignal,
): Promise<void> {
  const response = await fetch(`${API_BASE}/chat/sessions/${sessionId}/messages/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
    body: JSON.stringify(payload),
    signal,
  })

  if (!response.ok) {
    const detail = await response.text().catch(() => '')
    throw new Error(detail || `Stream request failed: ${response.status}`)
  }
  if (!response.body) throw new Error('No response body for stream')

  const reader = response.body.getReader()
  const decoder = new TextDecoder('utf-8')
  let buffer = ''

  try {
    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      buffer = consumeSseBuffer(buffer, handlers)
    }
    buffer += decoder.decode()
    consumeSseBuffer(buffer, handlers, true)
  } finally {
    try {
      reader.releaseLock()
    } catch {
      // ignore
    }
  }
}

export const streamChatMessage = sendChatMessageStream

function consumeSseBuffer(
  input: string,
  handlers: ChatStreamHandlers,
  flush = false,
) {
  const normalized = input.replace(/\r\n/g, '\n')
  const blocks = normalized.split('\n\n')
  const tail = flush ? '' : blocks.pop() ?? ''

  for (const block of blocks) {
    if (block.trim()) {
      dispatchSseBlock(block, handlers)
    }
  }

  return tail
}

function dispatchSseBlock(block: string, handlers: ChatStreamHandlers) {
  const evt = parseSse(block)
  if (!evt) return

  if (evt.event === 'start') {
    handlers.onStart?.(evt.data as { reasoning_mode: string; retrieval_mode: string; session_id: string })
    handlers.onStatus?.(evt.data as ChatStreamStatus)
    return
  }
  if (evt.event === 'status') {
    handlers.onStatus?.(evt.data as ChatStreamStatus)
    return
  }
  if (evt.event === 'step') {
    handlers.onStep?.(evt.data as StreamStepData)
    return
  }
  if (evt.event === 'delta') {
    const delta = typeof evt.data === 'object' && evt.data && 'delta' in evt.data
      ? String((evt.data as { delta?: unknown }).delta ?? '')
      : ''
    if (delta) handlers.onDelta?.(delta)
    return
  }
  if (evt.event === 'final' || evt.event === 'done') {
    handlers.onFinal?.(evt.data as ChatMessageResponse)
    handlers.onDone?.(evt.data as ChatMessageResponse)
    return
  }
  if (evt.event === 'error') {
    const message = typeof evt.data === 'object' && evt.data
      ? String((evt.data as { message?: unknown; detail?: unknown }).message ?? (evt.data as { detail?: unknown }).detail ?? 'stream failed')
      : 'stream failed'
    handlers.onError?.(message)
    throw new Error(message)
  }
}

function parseSse(raw: string): { event: string; data: unknown } | null {
  let event = 'message'
  const dataLines: string[] = []
  for (const line of raw.split('\n')) {
    if (line.startsWith('event:')) event = line.slice('event:'.length).trim()
    else if (line.startsWith('data:')) dataLines.push(line.slice('data:'.length).trimStart())
  }
  if (!dataLines.length) return null
  try {
    const data = JSON.parse(dataLines.join('\n')) as unknown
    return { event, data }
  } catch {
    return null
  }
}

export type ChatMessageSimple = {
  id: string
  role: string
  content: string
  created_at: string
}

export function mapMessageToTurn(m: ChatMessageRead) {
  return {
    role: (m.role === 'user' ? 'user' : 'assistant') as 'user' | 'assistant',
    content: m.content,
    citations: m.citations ?? [],
    trace: m.trace as any,
  }
}
