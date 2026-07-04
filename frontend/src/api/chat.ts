import { apiFetch } from './http'
import type {
  ChatMessageRequest,
  ChatMessageResponse,
  ChatSessionCreate,
  ChatSessionRead,
} from './types'

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
