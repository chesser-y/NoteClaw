import { apiFetch } from './http'
import { API_BASE } from './http'
import type {
  ChatMessageRead,
  ChatMessageRequest,
  ChatMessageResponse,
  ChatSessionCreate,
  ChatSessionDetail,
  ChatSessionRead,
} from './types'

export function createChatSession(payload: ChatSessionCreate) {
  return apiFetch<ChatSessionRead>('/chat/sessions', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function listChatSessions(limit = 50) {
  return apiFetch<ChatSessionRead[]>(`/chat/sessions?limit=${limit}`)
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
}

export type StreamHandlers = {
  onStart?: (data: { reasoning_mode: string; retrieval_mode: string; session_id: string }) => void
  onStep?: (data: StreamStepData) => void
  onDone?: (response: ChatMessageResponse) => void
  onError?: (err: string) => void
}

export async function streamChatMessage(
  sessionId: string,
  payload: ChatMessageRequest,
  handlers: StreamHandlers,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(`${API_BASE}/chat/sessions/${sessionId}/messages/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
    body: JSON.stringify(payload),
    signal,
  })

  if (!res.ok) {
    const detail = await res.text().catch(() => '')
    throw new Error(detail || `Stream request failed: ${res.status}`)
  }
  if (!res.body) throw new Error('No response body for stream')

  const reader = res.body.getReader()
  const decoder = new TextDecoder('utf-8')
  let buffer = ''

  try {
    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      let idx: number
      while ((idx = buffer.indexOf('\n\n')) >= 0) {
        const raw = buffer.slice(0, idx)
        buffer = buffer.slice(idx + 2)
        const evt = parseSse(raw)
        if (!evt) continue
        switch (evt.event) {
          case 'start':
            handlers.onStart?.(evt.data as any)
            break
          case 'step':
            handlers.onStep?.(evt.data as StreamStepData)
            break
          case 'done':
            handlers.onDone?.(evt.data as ChatMessageResponse)
            return
          case 'error':
            handlers.onError?.((evt.data?.detail as string) || 'stream failed')
            return
        }
      }
    }
  } finally {
    try {
      reader.releaseLock()
    } catch {
      // ignore
    }
  }
}

function parseSse(raw: string): { event: string; data: any } | null {
  let event = 'message'
  const dataLines: string[] = []
  for (const line of raw.split('\n')) {
    if (line.startsWith('event:')) event = line.slice(6).trim()
    else if (line.startsWith('data:')) dataLines.push(line.slice(5).trim())
  }
  if (!dataLines.length) return null
  try {
    const data = JSON.parse(dataLines.join('\n'))
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
