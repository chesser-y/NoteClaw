<script setup lang="ts">
import { ref } from 'vue'
import { Bot, Send, Sparkles, User } from 'lucide-vue-next'
import PageHeader from '../components/PageHeader.vue'
import { createChatSession, sendChatMessage } from '../api/chat'
import type { Citation, ChatSessionRead } from '../api/types'

type ChatMessage = {
  id: string
  role: 'user' | 'assistant'
  content: string
  citations?: Citation[]
  pending?: boolean
}

const session = ref<ChatSessionRead | null>(null)
const messages = ref<ChatMessage[]>([])
const input = ref('')
const useNanobot = ref(false)
const loading = ref(false)
const error = ref('')

async function ensureSession() {
  if (session.value) return session.value
  session.value = await createChatSession({
    title: '知识库问答',
    scope: { note_ids: [], tags: [], content_types: [] },
  })
  return session.value
}

async function submit() {
  const text = input.value.trim()
  if (!text || loading.value) return

  loading.value = true
  error.value = ''
  input.value = ''
  messages.value.push({ id: crypto.randomUUID(), role: 'user', content: text })
  messages.value.push({ id: 'pending', role: 'assistant', content: '正在检索知识库...', pending: true })

  try {
    const currentSession = await ensureSession()
    const response = await sendChatMessage(currentSession.id, {
      message: text,
      retrieval_mode: 'hybrid',
      use_nanobot_reasoning: useNanobot.value,
      top_k: 8,
    })
    const pendingIndex = messages.value.findIndex((message) => message.id === 'pending')
    const assistantMessage = {
      id: response.message_id,
      role: 'assistant' as const,
      content: response.answer,
      citations: response.citations,
    }
    if (pendingIndex >= 0) messages.value.splice(pendingIndex, 1, assistantMessage)
    else messages.value.push(assistantMessage)
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
    messages.value = messages.value.filter((message) => message.id !== 'pending')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <section class="content-wrap flex min-h-[calc(100vh-72px)] flex-col">
    <PageHeader
      eyebrow="Chat"
      title="知识问答"
      description="基于 SQLite/FAISS 检索上下文，再调用 LLM 生成回答。跨文档复杂推理会走 nanobot harness。"
    />

    <div class="grid flex-1 gap-6 xl:grid-cols-[minmax(0,1fr)_320px]">
      <div class="surface-soft flex min-h-[560px] flex-col">
        <div class="border-b border-[#2e3432] p-4 text-sm text-[#9aa3a0]">
          {{ session ? `会话 ${session.id}` : '尚未创建会话，发送第一条消息时自动创建' }}
        </div>

        <div class="flex-1 space-y-4 overflow-y-auto p-5">
          <div v-if="!messages.length" class="mx-auto mt-20 max-w-xl text-center">
            <Sparkles :size="28" class="mx-auto mb-4 text-[#d9d2bf]" />
            <h2 class="serif mb-3 text-2xl text-white">向你的知识库提问</h2>
            <p class="leading-7 text-[#8f9996]">
              例如：结合我已有资料，比较 FAISS 和 Chroma；或者总结这些截图里的实验流程。
            </p>
          </div>

          <div
            v-for="message in messages"
            :key="message.id"
            class="flex gap-3"
            :class="{ 'justify-end': message.role === 'user' }"
          >
            <div
              v-if="message.role === 'assistant'"
              class="mt-1 flex h-8 w-8 shrink-0 items-center justify-center border border-[#38413e] bg-[#151818]"
            >
              <Bot :size="16" />
            </div>
            <div class="max-w-3xl border border-[#333b38] bg-[#151818] p-4">
              <div class="whitespace-pre-wrap text-sm leading-7 text-[#e7e3da]">{{ message.content }}</div>
              <div v-if="message.citations?.length" class="mt-4 space-y-2">
                <div class="text-xs uppercase tracking-[0.14em] text-[#8f9996]">引用来源</div>
                <div v-for="citation in message.citations" :key="`${citation.note_id}-${citation.chunk_id}`" class="chip">
                  {{ citation.title }}
                </div>
              </div>
            </div>
            <div
              v-if="message.role === 'user'"
              class="mt-1 flex h-8 w-8 shrink-0 items-center justify-center border border-[#38413e] bg-[#f2f0ed] text-[#101313]"
            >
              <User :size="16" />
            </div>
          </div>
        </div>

        <form class="border-t border-[#2e3432] p-4" @submit.prevent="submit">
          <div class="flex gap-3">
            <textarea
              v-model="input"
              class="field min-h-[52px] flex-1 resize-none"
              placeholder="输入问题"
              @keydown.enter.exact.prevent="submit"
            ></textarea>
            <button class="btn btn-primary self-end" type="submit" :disabled="loading || !input.trim()">
              <Send :size="16" />
              发送
            </button>
          </div>
          <div v-if="error" class="mt-3 text-sm text-[#f0b8ad]">{{ error }}</div>
        </form>
      </div>

      <aside class="surface h-fit p-5">
        <h2 class="mb-3 text-lg text-white">推理设置</h2>
        <label class="mb-4 flex items-center gap-3 text-sm text-[#c9cfcc]">
          <input v-model="useNanobot" type="checkbox" />
          启用 nanobot 跨文档推理
        </label>
        <p class="text-sm leading-6 text-[#8f9996]">
          当前后端已经预留 `use_nanobot_reasoning` 和 `NanobotHarness`。实现完成后，这里会用于网页检索、多文档综合分析和代码仓库推理。
        </p>
      </aside>
    </div>
  </section>
</template>
