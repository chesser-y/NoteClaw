<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Plus, Sparkles, ArrowUpRight, FileText, Image as ImageIcon, Code2 } from 'lucide-vue-next'
import { useUiStore } from '../stores/ui'
import { useIngest } from '../composables/useIngest'
import { listKnowledge } from '../api/knowledge'
import { listTasks } from '../api/tasks'
import type { NoteListItem, TaskRead } from '../api/types'
import HomeHero from '../components/home/HomeHero.vue'
import SourcePreview from '../components/home/SourcePreview.vue'
import UnderstandingPanel from '../components/home/UnderstandingPanel.vue'
import AskTrigger from '../components/ask/AskTrigger.vue'

const ui = useUiStore()
const ingest = useIngest()

const recent = ref<NoteListItem[]>([])
const tasks = ref<TaskRead[]>([])
const loadingRecent = ref(false)

async function loadRecent() {
  loadingRecent.value = true
  try {
    const [k, t] = await Promise.allSettled([
      listKnowledge({ limit: 4 }),
      listTasks({ limit: 4 }),
    ])
    if (k.status === 'fulfilled') recent.value = k.value.items
    if (t.status === 'fulfilled') tasks.value = t.value.items
  } finally {
    loadingRecent.value = false
  }
}

onMounted(loadRecent)

const todayLabel = computed(() => {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`
})

const iconFor = (t: string) => {
  if (t === 'image') return ImageIcon
  if (t === 'code') return Code2
  return FileText
}
</script>

<template>
  <section class="content-wrap">
    <header class="mb-6 flex items-center justify-between">
      <div>
        <h1 class="section-title">Ask, drop, paste, or create…</h1>
        <p class="muted mt-1 text-sm">粘贴、拖入，或直接问我。</p>
      </div>
      <div class="flex items-center gap-2">
        <button class="btn" type="button" @click="ingest.clear(); ui.openAsk(null)">
          <Sparkles :size="14" />
          Ask
        </button>
        <button class="btn btn-primary" type="button" @click="ui.openPalette()">
          <Plus :size="14" />
          New
          <span class="kbd ml-1">⌘K</span>
        </button>
      </div>
    </header>

    <div class="grid gap-6 lg:grid-cols-[minmax(0,1fr)_280px]">
      <div class="space-y-6">
        <HomeHero v-if="!ingest.preview.value" @preview="ingest.setPreview" />
        <div v-else class="grid gap-4 lg:grid-cols-2">
          <SourcePreview :preview="ingest.preview.value" />
          <UnderstandingPanel :preview="ingest.preview.value" :saving="ingest.saving.value" :error="ingest.error.value" @save="ingest.save" @cancel="ingest.clear" @ask="ui.openAsk(null, `关于这段内容：${ingest.preview.value.title}`)" />
        </div>

        <div>
          <div class="mb-3 flex items-center justify-between">
            <h2 class="text-sm font-semibold text-[#111827]">最近内容</h2>
            <RouterLink to="/library" class="flex items-center gap-1 text-xs text-[#6b7280] hover:text-[#4f46e5]">
              查看全部 <ArrowUpRight :size="12" />
            </RouterLink>
          </div>
          <div v-if="recent.length" class="grid gap-3 sm:grid-cols-2">
            <RouterLink
              v-for="item in recent"
              :key="item.id"
              :to="`/library?id=${item.id}`"
              class="card card-hover flex items-start gap-3 py-4"
            >
              <component :is="iconFor(item.content_type)" :size="16" class="mt-0.5 text-[#6b7280]" />
              <div class="min-w-0 flex-1">
                <div class="truncate text-sm font-medium text-[#111827]">{{ item.title }}</div>
                <div class="mt-0.5 truncate text-xs text-[#9ca3af]">{{ item.summary || '—' }}</div>
              </div>
            </RouterLink>
          </div>
          <p v-else-if="!loadingRecent" class="rounded-xl border border-dashed border-[#e5e7eb] bg-white px-4 py-6 text-center text-xs text-[#9ca3af]">
            还没有保存的资料。粘贴文本或拖入文件即可开始。
          </p>
        </div>
      </div>

      <aside class="space-y-5">
        <div class="surface p-4">
          <div class="mb-3 flex items-center justify-between">
            <div class="text-xs font-semibold uppercase tracking-wide text-[#6b7280]">Today</div>
            <div class="text-xs text-[#9ca3af]">{{ todayLabel }}</div>
          </div>
          <p class="text-sm text-[#111827]">把今天看到的内容粘到上方，让 NoteClaw 帮你整理。</p>
        </div>

        <div class="surface p-4">
          <div class="mb-3 text-xs font-semibold uppercase tracking-wide text-[#6b7280]">最近任务</div>
          <div v-if="tasks.length" class="space-y-2">
            <RouterLink
              v-for="t in tasks"
              :key="t.id"
              :to="`/tasks?task=${t.id}`"
              class="flex items-center gap-2 rounded-md px-2 py-1.5 text-sm hover:bg-[#f3f4f6]"
            >
              <span
                class="status-dot"
                :class="{ 'status-dot--warn': t.status === 'running', 'status-dot--idle': t.status === 'queued' }"
              ></span>
              <span class="truncate text-[#111827]">{{ t.type }}</span>
              <span class="ml-auto text-[11px] text-[#9ca3af]">{{ Math.round(t.progress * 100) }}%</span>
            </RouterLink>
          </div>
          <p v-else class="text-xs text-[#9ca3af]">暂无任务。</p>
        </div>

        <div class="surface p-4">
          <div class="mb-3 text-xs font-semibold uppercase tracking-wide text-[#6b7280]">推荐继续</div>
          <div class="space-y-1.5">
            <AskTrigger label="总结最近保存的内容" />
            <AskTrigger label="找出相关笔记" />
            <RouterLink to="/studio" class="btn btn-ghost h-8 w-full justify-start px-2 text-xs">
              <Sparkles :size="14" />
              生成 PPT 大纲
            </RouterLink>
          </div>
        </div>
      </aside>
    </div>
  </section>
</template>
