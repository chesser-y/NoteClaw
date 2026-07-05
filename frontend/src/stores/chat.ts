import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  createChatSession,
  getChatSession,
  sendChatMessageStream,
  type StreamStepData,
} from '../api/chat'
import type {
  ChatMessageResponse,
  ChatReasoningMode,
  Citation,
  Scope,
} from '../api/types'

export type ChatTurn = {
  role: 'user' | 'assistant'
  content: string
  citations?: Citation[]
  trace?: ChatMessageResponse['trace']
  pending?: boolean
  status?: string
  streaming?: boolean
}

const MODE_KEY = 'noteclaw.chat-mode'
const PERSIST_MODE: ChatReasoningMode = (localStorage.getItem(MODE_KEY) as ChatReasoningMode) || 'normal'

const ROLE_TITLE: Record<string, string> = {
  coordinator: 'Plan workflow',
  researcher: 'Collect evidence',
  reasoner: 'Synthesize answer',
  reviewer: 'Review result',
}

type LiveMeta = {
  steps: any[]
  plan?: string[]
  review?: any
  currentRole?: string
}

function newLiveTrace(mode: ChatReasoningMode): ChatMessageResponse['trace'] {
  return {
    retrieval_mode: 'hybrid',
    used_nanobot: mode !== 'normal',
    model: undefined,
    metadata: { steps: [], plan: [], review: null } as LiveMeta,
    steps: [],
    plan: [],
    review: null,
  } as any
}

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

    const turn: ChatTurn = {
      role: 'assistant',
      content: '',
      citations: [],
      trace: newLiveTrace(mode.value),
      pending: true,
      status: 'Question received',
      streaming: true,
    }
    turns.value.push(turn)
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
            turn.status = status.message || status.stage || 'Working'
            if (Array.isArray(status.plan)) {
              applyPlan(turn, status.plan)
            }
          },
          onStep(data) {
            applyStep(turn, data)
          },
          onDelta(delta) {
            turn.content += delta
            turn.status = ''
          },
          onFinal(response) {
            finalReceived = true
            turn.content = response.answer || turn.content
            turn.citations = response.citations
            turn.trace = response.trace
            turn.pending = false
            turn.streaming = false
            turn.status = ''
          },
        },
      )

      if (!finalReceived) {
        turn.pending = false
        turn.streaming = false
        turn.status = ''
      }
    } catch (e) {
      error.value = e instanceof Error ? e.message : String(e)
      turn.pending = false
      turn.streaming = false
      turn.status = ''
      if (!turn.content) {
        turns.value = turns.value.filter((t) => t !== turn)
      }
    } finally {
      sending.value = false
    }
  }

  function applyPlan(turn: ChatTurn, plan: string[]) {
    const trace = (turn.trace ?? newLiveTrace(mode.value)) as any
    const meta: LiveMeta = (trace.metadata ?? { steps: [] }) as LiveMeta
    turn.trace = {
      ...trace,
      plan,
      metadata: { ...meta, plan },
    } as any
  }

  function applyStep(turn: ChatTurn, data: StreamStepData) {
    const trace = (turn.trace ?? newLiveTrace(mode.value)) as any
    const meta: LiveMeta = (trace.metadata ?? { steps: [] }) as LiveMeta
    if (data.phase === 'running') {
      meta.currentRole = data.role
      turn.trace = { ...trace, metadata: { ...meta } } as any
      return
    }
    if (data.phase === 'done') {
      const nextSteps = [...(meta.steps ?? [])]
      const lastSame = nextSteps.findIndex((s) => s.role === data.role)
      const stepObj: any = {
        role: data.role,
        title: ROLE_TITLE[data.role] || data.role,
        status: 'done',
        output_summary: data.output ?? '',
        citations: data.citations ?? [],
      }
      if (lastSame >= 0) nextSteps[lastSame] = stepObj
      else nextSteps.push(stepObj)
      const nextMeta: LiveMeta = {
        steps: nextSteps,
        plan: data.plan ?? meta.plan,
        review: data.review ?? meta.review,
        currentRole: data.role,
      }
      turn.trace = {
        ...trace,
        steps: nextSteps,
        plan: nextMeta.plan ?? trace.plan ?? [],
        review: nextMeta.review ?? trace.review ?? null,
        metadata: nextMeta,
      } as any
    }
  }

  async function loadSession(id: string) {
    sending.value = true
    error.value = null
    try {
      const detail = await getChatSession(id)
      sessionId.value = detail.id
      if (detail.scope) scope.value = detail.scope as Scope
      turns.value = detail.messages
        .filter((m) => m.role === 'user' || m.role === 'assistant')
        .map((m) => ({
          role: m.role as 'user' | 'assistant',
          content: m.content,
          citations: m.citations ?? [],
          trace: m.trace as ChatMessageResponse['trace'] | undefined,
          pending: false,
          streaming: false,
        }))
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

  return { sessionId, turns, sending, error, scope, mode, ask, loadSession, reset, setScope, setMode }
})
