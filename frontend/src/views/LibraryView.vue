<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Search, SlidersHorizontal, MessageSquareText, RefreshCw } from 'lucide-vue-next'
import { listKnowledge } from '../api/knowledge'
import { searchKnowledge } from '../api/search'
import type { ContentType, NoteListItem, SearchResult } from '../api/types'
import { useUiStore } from '../stores/ui'
import NoteCard from '../components/library/NoteCard.vue'

const ui = useUiStore()

type Filter = 'recent' | 'all' | 'document' | 'image' | 'code' | 'starred'
const filters: { id: Filter; label: string }[] = [
  { id: 'recent', label: '最近使用' },
  { id: 'all', label: '全部' },
  { id: 'document', label: '文档' },
  { id: 'image', label: '图片' },
  { id: 'code', label: '代码' },
  { id: 'starred', label: '收藏' },
]

const activeFilter = ref<Filter>('all')
const query = ref('')
const loading = ref(false)
const error = ref('')
const notes = ref<NoteListItem[]>([])
const searchResults = ref<SearchResult[] | null>(null)
const showAdvanced = ref(false)

const contentTypeForFilter = computed<ContentType | ''>(() => {
  if (activeFilter.value === 'document') return 'document'
  if (activeFilter.value === 'image') return 'image'
  if (activeFilter.value === 'code') return 'code'
  return ''
})

async function loadNotes() {
  loading.value = true
  error.value = ''
  try {
    searchResults.value = null
    const response = await listKnowledge({
      q: query.value || undefined,
      content_type: contentTypeForFilter.value,
      limit: 24,
    })
    notes.value = response.items
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    loading.value = false
  }
}

async function runSearch() {
  if (!query.value.trim()) {
    await loadNotes()
    return
  }
  loading.value = true
  error.value = ''
  try {
    const response = await searchKnowledge({
      query: query.value,
      mode: 'hybrid',
      filters: {
        content_types: contentTypeForFilter.value ? [contentTypeForFilter.value] : [],
        tags: [],
        category: null,
        date_from: null,
        date_to: null,
      },
      limit: 12,
    })
    searchResults.value = response.results
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    loading.value = false
  }
}

function onAsk() {
  ui.openAsk(null, query.value.trim() || undefined)
}

onMounted(loadNotes)
</script>

<template>
  <section class="content-wrap">
    <header class="mb-5 flex items-end justify-between">
      <div>
        <h1 class="section-title">Library</h1>
        <p class="muted mt-1 text-sm">管理沉淀下来的资料 · 搜索会调用 hybrid 检索</p>
      </div>
      <button class="btn h-8" type="button" @click="loadNotes">
        <RefreshCw :size="13" />
        刷新
      </button>
    </header>

    <div class="surface mb-5 flex items-center gap-2 px-3 py-2">
      <Search :size="15" class="text-[#73747a]" />
      <input
        v-model="query"
        class="min-w-0 flex-1 bg-transparent text-sm text-[#f0f1f2] outline-none placeholder:text-[#73747a]"
        placeholder="Search anything in your notes..."
        @keydown.enter="runSearch"
      />
      <button class="btn btn-ghost h-7 px-2 text-xs" type="button" @click="showAdvanced = !showAdvanced">
        <SlidersHorizontal :size="12" />
        高级
      </button>
      <button class="btn btn-ghost h-7 px-2 text-xs" type="button" @click="onAsk">
        <MessageSquareText :size="12" />
        提问
      </button>
    </div>

    <div v-if="showAdvanced" class="surface mb-5 grid gap-3 p-4 md:grid-cols-3">
      <div>
        <label class="mb-1 block text-xs text-[#929399]">标签</label>
        <input class="field h-9" placeholder="#tag1, #tag2" />
      </div>
      <div>
        <label class="mb-1 block text-xs text-[#929399]">分类</label>
        <input class="field h-9" placeholder="research / engineering / ..." />
      </div>
      <div>
        <label class="mb-1 block text-xs text-[#929399]">日期范围</label>
        <div class="flex items-center gap-2">
          <input type="date" class="field h-9" />
          <span class="text-xs text-[#73747a]">—</span>
          <input type="date" class="field h-9" />
        </div>
      </div>
    </div>

    <div class="mb-6 flex flex-wrap items-center gap-1.5">
      <button
        v-for="f in filters"
        :key="f.id"
        type="button"
        class="rounded-full px-3 py-1.5 text-xs font-medium transition"
        :class="activeFilter === f.id ? 'bg-[#626be6] text-white' : 'bg-[#1b1c1e] text-[#929399] hover:bg-[#242527]'"
        @click="activeFilter = f.id; loadNotes()"
      >
        {{ f.label }}
      </button>
    </div>

    <p v-if="error" class="mb-5 rounded-lg border border-[#5a2520] bg-[#2a1614] px-3 py-2 text-xs text-[#f0b8ad]">
      {{ error }}
    </p>

    <div v-if="searchResults" class="space-y-4">
      <div class="text-xs text-[#929399]">检索结果 · {{ searchResults.length }} 条</div>
      <div class="grid gap-3 md:grid-cols-2">
        <NoteCard
          v-for="r in searchResults"
          :key="`${r.note_id}-${r.chunk_id}`"
          :title="r.title"
          :content-type="r.content_type"
          :summary="r.snippet"
          :tags="r.tags"
          :source="r.source ?? undefined"
          :score="r.score ?? undefined"
        />
      </div>
    </div>

    <div v-else-if="notes.length" class="grid gap-3 md:grid-cols-2">
      <NoteCard
        v-for="note in notes"
        :key="note.id"
        :title="note.title"
        :content-type="note.content_type"
        :summary="note.summary ?? ''"
        :tags="note.tags"
        :source="note.source ?? undefined"
        :created-at="note.created_at"
      />
    </div>

    <div v-else-if="!loading" class="surface flex flex-col items-center gap-2 px-4 py-12 text-center">
      <div class="text-sm text-[#f0f1f2]">还没有保存的资料</div>
      <p class="text-xs text-[#73747a]">回到首页粘贴文本或拖入 PDF 即可开始沉淀知识库。</p>
      <RouterLink to="/" class="btn btn-primary mt-2 h-8">返回首页</RouterLink>
    </div>
  </section>
</template>
