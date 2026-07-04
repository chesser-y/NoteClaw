import { defineStore } from 'pinia'
import { ref } from 'vue'
import { createChatSession, sendChatMessage } from '../api/chat'
import type { ChatMessageResponse, Citation, Scope } from '../api/types'

export type ChatTurn = {
  role: 'user' | 'assistant'
  content: string
  citations?: Citation[]
  trace?: ChatMessageResponse['trace']
}

export const useChatStore = defineStore('chat', () => {
  const sessionId = ref<string | null>(null)
  const turns = ref<ChatTurn[]>([])
  const sending = ref(false)
  const error = ref<string | null>(null)
  const scope = ref<Scope | null>(null)

  async function ask(question: string) {
    if (!question.trim() || sending.value) return
    turns.value.push({ role: 'user', content: question })
    sending.value = true
    error.value = null
    try {
      if (!sessionId.value) {
        const session = await createChatSession({ scope: scope.value ?? undefined })
        sessionId.value = session.id
      }
      const res = await sendChatMessage(sessionId.value!, {
        message: question,
        retrieval_mode: 'hybrid',
        use_nanobot_reasoning: false,
        top_k: 8,
      })
      turns.value.push({
        role: 'assistant',
        content: res.answer,
        citations: res.citations,
        trace: res.trace,
      })
    } catch (e) {
      error.value = e instanceof Error ? e.message : String(e)
    } finally {
      sending.value = false
    }
  }

  function reset() {
    sessionId.value = null
    turns.value = []
    sending.value = false
    error.value = null
    scope.value = null
  }

  function setScope(s: Scope | null) {
    scope.value = s
  }

  return { sessionId, turns, sending, error, scope, ask, reset, setScope }
})
