<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { MessageSquareText, Send } from 'lucide-vue-next'
import { useUiStore } from '../../stores/ui'
import { createChatSession, sendChatMessage } from '../../api/chat'
import type { ChatMessageResponse } from '../../api/types'
import SourceList from '../common/SourceList.vue'
import Drawer from '../common/Drawer.vue'

const ui = useUiStore()

const input = ref(ui.askPrefill || '')
const sending = ref(false)
const error = ref('')
const last = ref<ChatMessageResponse | null>(null)

watch(
  () => ui.askPrefill,
  (v) => {
    if (v) input.value = v
  },
)

const scopeLabel = computed(() =>
  ui.askScope && ui.askScope.noteIds.length
    ? `当前资料 · ${ui.askScope.noteIds.length} 篇`
    : '全部资料',
)

async function submit() {
  const message = input.value.trim()
  if (!message || sending.value) return
  sending.value = true
  error.value = ''
  try {
    const scope =
      ui.askScope && ui.askScope.noteIds.length
        ? { note_ids: ui.askScope.noteIds }
        : undefined
    const session = await createChatSession({
      title: ui.askScope?.title ?? message.slice(0, 40),
      scope,
    })
    const res = await sendChatMessage(session.id, {
      message,
      retrieval_mode: 'hybrid',
      use_nanobot_reasoning: false,
      top_k: 6,
    })
    last.value = res
    input.value = ''
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    sending.value = false
  }
}
</script>

<template>
  <Drawer :open="ui.askOpen" title="Ask NoteClaw" width="480px" @close="ui.closeAsk()">
    <div class="space-y-4">
      <p class="text-sm text-[#6b7280]">
        你可以问<span class="font-medium text-[#4f46e5]">{{ scopeLabel }}</span>，也可以问全部资料。
      </p>

      <form
        class="flex items-center gap-2 rounded-xl border border-[#e5e7eb] bg-white px-3 py-2 focus-within:border-[#4f46e5] focus-within:shadow-[0_0_0_3px_rgba(79,70,229,0.15)]"
        @submit.prevent="submit"
      >
        <MessageSquareText :size="16" class="text-[#9ca3af]" />
        <input
          v-model="input"
          class="min-w-0 flex-1 bg-transparent text-sm text-[#111827] outline-none placeholder:text-[#9ca3af]"
          placeholder="输入问题..."
          type="text"
        />
        <button class="btn btn-primary h-8 px-3" type="submit" :disabled="sending || !input.trim()">
          <Send :size="14" />
          {{ sending ? '询问中' : '发送' }}
        </button>
      </form>

      <p v-if="error" class="rounded-lg border border-[#fcd9d4] bg-[#fef3f1] px-3 py-2 text-xs text-[#b42618]">
        {{ error }}
      </p>

      <div v-if="last" class="space-y-3">
        <div class="rounded-xl border border-[#e5e7eb] bg-[#fafbfc] p-4 text-sm leading-6 text-[#111827]">
          {{ last.answer }}
        </div>

        <div>
          <div class="mb-2 text-xs font-medium uppercase tracking-wide text-[#6b7280]">Sources used</div>
          <SourceList :sources="last.citations" />
        </div>

        <div class="text-[11px] text-[#9ca3af]">
          检索模式：{{ last.trace.retrieval_mode }} · nanobot：{{ last.trace.used_nanobot ? '是' : '否' }}
        </div>
      </div>
    </div>
  </Drawer>
</template>
