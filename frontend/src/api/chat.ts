import { API_BASE, apiFetch } from './http'
import type {
  ChatMessageRequest,
  ChatMessageResponse,
  ChatSessionCreate,
  ChatSessionRead,
  ChatStreamStatus,
} from './types'

export type ChatStreamHandlers = {
  onStatus?: (status: ChatStreamStatus) => void
  onDelta?: (delta: string) => void
  onFinal?: (response: ChatMessageResponse) => void
}

export function createChatSession(payload: ChatSessionCreate) {
  return apiFetch<ChatSessionRead>('/chat/sessions', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function sendChatMessage(sessionId: string, payload: ChatMessageRequest) {
  return apiFetch<ChatMessageResponse>(`/chat/sessions/${sessionId}/messages`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function sendChatMessageStream(
  sessionId: string,
  payload: ChatMessageRequest,
  handlers: ChatStreamHandlers,
  signal?: AbortSignal,
) {
  const response = await fetch(`${API_BASE}/chat/sessions/${sessionId}/messages/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
    body: JSON.stringify(payload),
    signal,
  })

  if (!response.ok) {
    const detail = await response.text()
    throw new Error(detail || `Request failed: ${response.status}`)
  }
  if (!response.body) {
    throw new Error('Streaming response body is not available.')
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    buffer = consumeSseBuffer(buffer, handlers)
  }

  buffer += decoder.decode()
  consumeSseBuffer(buffer, handlers, true)
}

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
  let event = 'message'
  const dataLines: string[] = []

  for (const line of block.split('\n')) {
    if (line.startsWith('event:')) {
      event = line.slice('event:'.length).trim()
    } else if (line.startsWith('data:')) {
      dataLines.push(line.slice('data:'.length).trimStart())
    }
  }

  if (!dataLines.length) return

  const payload = JSON.parse(dataLines.join('\n')) as unknown
  if (event === 'status') {
    handlers.onStatus?.(payload as ChatStreamStatus)
    return
  }
  if (event === 'delta') {
    const delta = typeof payload === 'object' && payload && 'delta' in payload
      ? String((payload as { delta?: unknown }).delta ?? '')
      : ''
    if (delta) handlers.onDelta?.(delta)
    return
  }
  if (event === 'final') {
    handlers.onFinal?.(payload as ChatMessageResponse)
    return
  }
  if (event === 'error') {
    const message = typeof payload === 'object' && payload && 'message' in payload
      ? String((payload as { message?: unknown }).message ?? 'Streaming request failed.')
      : 'Streaming request failed.'
    throw new Error(message)
  }
}
