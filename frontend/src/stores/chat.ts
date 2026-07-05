import { defineStore } from 'pinia'
import { ref } from 'vue'
import { createChatSession, sendChatMessageStream } from '../api/chat'
import type { ChatMessageResponse, ChatReasoningMode, Citation, Scope } from '../api/types'

export type ChatTurn = {
  role: 'user' | 'assistant'
  content: string
  citations?: Citation[]
  trace?: ChatMessageResponse['trace']
  pending?: boolean
  status?: string
}

const MODE_KEY = 'noteclaw.chat-mode'
const PERSIST_MODE: ChatReasoningMode = (localStorage.getItem(MODE_KEY) as ChatReasoningMode) || 'normal'

export const useChatStore = defineStore('chat', () => {
  const sessionId = ref<string | null>(null)
  const turns = ref<ChatTurn[]>([])
  const sending = ref(false)
  const error = ref<string | null>(null)
  const scope = ref<Scope | null>(null)
  const mode = ref<ChatReasoningMode>(PERSIST_MODE)

  function setMode(next: ChatReasoningMode) {
    mode.value = next
    localStorage.setItem(MODE_KEY, next)
  }

  async function ask(question: string) {
    if (!question.trim() || sending.value) return
    turns.value.push({ role: 'user', content: question })
    const assistantTurn: ChatTurn = {
      role: 'assistant',
      content: '',
      citations: [],
      pending: true,
      status: 'Question received',
    }
    turns.value.push(assistantTurn)
    sending.value = true
    error.value = null
    let finalReceived = false
    try {
      if (!sessionId.value) {
        const session = await createChatSession({ scope: scope.value ?? undefined })
        sessionId.value = session.id
      }
      const currentMode = mode.value
      const useWeb = currentMode === 'web'
      await sendChatMessageStream(
        sessionId.value!,
        {
          message: question,
          retrieval_mode: 'hybrid',
          use_nanobot_reasoning: currentMode === 'deep',
          use_web_research: useWeb,
          reasoning_mode: currentMode,
          top_k: 8,
          max_reasoning_steps: currentMode === 'normal' ? 3 : 4,
          web_results: 4,
          fetch_web_pages: useWeb,
        },
        {
          onStatus(status) {
            assistantTurn.status = status.message || status.stage || 'Working'
            if (Array.isArray(status.plan)) {
              assistantTurn.trace = {
                retrieval_mode: 'hybrid',
                used_nanobot: currentMode !== 'normal',
                metadata: {},
                plan: status.plan,
              }
            }
          },
          onDelta(delta) {
            assistantTurn.content += delta
            assistantTurn.status = ''
          },
          onFinal(res) {
            finalReceived = true
            assistantTurn.content = res.answer || assistantTurn.content
            assistantTurn.citations = res.citations
            assistantTurn.trace = res.trace
            assistantTurn.pending = false
            assistantTurn.status = ''
          },
        },
      )
      if (!finalReceived) {
        assistantTurn.pending = false
        assistantTurn.status = ''
      }
    } catch (e) {
      error.value = e instanceof Error ? e.message : String(e)
      assistantTurn.pending = false
      assistantTurn.status = ''
      if (!assistantTurn.content) {
        turns.value = turns.value.filter((turn) => turn !== assistantTurn)
      }
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

  return { sessionId, turns, sending, error, scope, mode, ask, reset, setScope, setMode }
})
