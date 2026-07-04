<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RefreshCw, Search } from 'lucide-vue-next'
import PageHeader from '../components/PageHeader.vue'
import EmptyState from '../components/EmptyState.vue'
import { listKnowledge } from '../api/knowledge'
import { searchKnowledge } from '../api/search'
import type { ContentType, NoteListItem, SearchResult } from '../api/types'

const loading = ref(false)
const error = ref('')
const query = ref('')
const contentType = ref<ContentType | ''>('')
const notes = ref<NoteListItem[]>([])
const searchResults = ref<SearchResult[]>([])

async function loadNotes() {
  loading.value = true
  error.value = ''
  try {
    const response = await listKnowledge({
      q: query.value || undefined,
      content_type: contentType.value,
      limit: 20,
      offset: 0,
    })
    notes.value = response.items
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  } finally {
    loading.value = false
  }
}

async function runSearch() {
  if (!query.value.trim()) {
    searchResults.value = []
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
        content_types: contentType.value ? [contentType.value] : [],
        tags: [],
        category: null,
        date_from: null,
        date_to: null,
      },
      limit: 10,
    })
    searchResults.value = response.results
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  } finally {
    loading.value = false
  }
}

onMounted(loadNotes)
</script>

<template>
  <section class="content-wrap">
    <PageHeader
      eyebrow="Library"
      title="知识库"
      description="查看已经沉淀的原文、摘要、标签和来源。搜索框会走后端 hybrid 检索接口，返回引用 chunk。"
    />

    <div class="surface-soft mb-6 grid gap-3 p-4 md:grid-cols-[1fr_180px_auto_auto]">
      <div class="flex items-center gap-2 border border-[#343a38] bg-[#121414] px-3">
        <Search :size="18" class="text-[#8f9996]" />
        <input v-model="query" class="field border-0 bg-transparent px-0" placeholder="搜索知识库内容" />
      </div>
      <select v-model="contentType" class="field">
        <option value="">全部类型</option>
        <option value="text">文本</option>
        <option value="code">代码</option>
        <option value="table">表格</option>
        <option value="image">图片</option>
        <option value="document">文档</option>
      </select>
      <button class="btn btn-primary" type="button" @click="runSearch">检索</button>
      <button class="btn" type="button" @click="loadNotes">
        <RefreshCw :size="16" />
        刷新
      </button>
    </div>

    <div v-if="error" class="mb-6 border border-[#70433b] bg-[#261716] p-4 text-sm text-[#f0b8ad]">
      {{ error }}
    </div>

    <div v-if="searchResults.length" class="mb-8">
      <h2 class="mb-4 text-lg text-white">检索结果</h2>
      <div class="grid-auto">
        <article v-for="result in searchResults" :key="`${result.note_id}-${result.chunk_id}`" class="surface p-5">
          <div class="mb-3 flex items-center justify-between gap-3">
            <h3 class="text-lg text-white">{{ result.title }}</h3>
            <span class="chip">{{ result.content_type }}</span>
          </div>
          <p class="mb-4 text-sm leading-6 text-[#a9b1ae]">{{ result.snippet }}</p>
          <div class="flex flex-wrap gap-2">
            <span v-for="tag in result.tags" :key="tag" class="chip">{{ tag }}</span>
            <span v-if="result.score !== null && result.score !== undefined" class="chip">
              score {{ result.score.toFixed(2) }}
            </span>
          </div>
        </article>
      </div>
    </div>

    <div v-if="notes.length" class="grid-auto">
      <article v-for="note in notes" :key="note.id" class="surface p-5">
        <div class="mb-4 flex items-start justify-between gap-3">
          <div>
            <h3 class="text-lg text-white">{{ note.title }}</h3>
            <div class="mt-1 text-xs uppercase tracking-[0.14em] text-[#7d8784]">
              {{ note.content_type }} / {{ note.status }}
            </div>
          </div>
          <span class="chip">{{ note.source ?? 'local' }}</span>
        </div>
        <p class="mb-5 min-h-[72px] text-sm leading-6 text-[#a9b1ae]">
          {{ note.summary || '等待摘要生成' }}
        </p>
        <div class="flex flex-wrap gap-2">
          <span v-for="tag in note.tags" :key="tag" class="chip">{{ tag }}</span>
        </div>
      </article>
    </div>

    <EmptyState
      v-else-if="!loading"
      title="还没有知识卡片"
      description="先去信息输入页添加文本、代码、表格或图片，后端会生成摘要、标签并写入知识库。"
    />
  </section>
</template>
