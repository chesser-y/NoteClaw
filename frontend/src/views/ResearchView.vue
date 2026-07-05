<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { Search, Clock, Hash, Database as SourceIcon, Loader2 } from 'lucide-vue-next'
import { searchKnowledge } from '../api/search'
import type { ContentType, SearchMode, SearchResult } from '../api/types'
import FilterPopover from '../components/library/FilterPopover.vue'
import NotePreview from '../components/preview/NotePreview.vue'

const { t } = useI18n()
const route = useRoute()

const query = ref('')
const mode = ref<SearchMode>('hybrid')
const loading = ref(false)
const error = ref('')
const results = ref<SearchResult[]>([])
const lastQuery = ref('')

const filterTags = ref<string[]>([])
const filterSource = ref('')
const filterDateFrom = ref('')
const filterDateTo = ref('')

const tabs: { label: string; value: SearchMode }[] = [
  { label: 'Keyword', value: 'keyword' },
  { label: 'Semantic', value: 'semantic' },
  { label: 'Hybrid', value: 'hybrid' },
]

function applyQueryTag(tag: string | string[] | undefined) {
  if (!tag) return
  const tags = Array.isArray(tag) ? tag : [tag]
  filterTags.value = [...new Set([...filterTags.value, ...tags])]
}

onMounted(() => {
  const tagQuery = route.query.tag
  if (tagQuery) {
    applyQueryTag(tagQuery as string | string[])
    query.value = `#${filterTags.value[0]}`
    runSearch()
  }
})

watch(
  () => route.query.tag,
  (newTag) => {
    if (!newTag) return
    applyQueryTag(newTag as string | string[])
    query.value = `#${filterTags.value[filterTags.value.length - 1]}`
    runSearch()
  },
)

async function runSearch() {
  const q = query.value.trim()
  if (!q) return
  loading.value = true
  error.value = ''
  try {
    const res = await searchKnowledge({
      query: q,
      mode: mode.value,
      filters: {
        content_types: [],
        tags: filterTags.value,
        category: null,
        source: filterSource.value || null,
        date_from: filterDateFrom.value || null,
        date_to: filterDateTo.value || null,
      },
      limit: 30,
    })
    results.value = res.results
    lastQuery.value = q
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
    results.value = []
  } finally {
    loading.value = false
  }
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    runSearch()
  }
}

const typeColor = (t: ContentType) => {
  switch (t) {
    case 'image': return '#4aaeff'
    case 'code': return 'var(--green)'
    case 'table': return 'var(--orange)'
    case 'document': return 'var(--pink)'
    default: return 'var(--blue)'
  }
}

const typeLabel = (t: ContentType) => {
  if (t === 'image') return 'Image'
  if (t === 'code') return 'Code'
  if (t === 'table') return 'Table'
  if (t === 'document') return 'PDF'
  if (t === 'webpage') return 'Web'
  return 'Note'
}

const relativeTime = (iso?: string | null) => {
  if (!iso) return ''
  const diff = (Date.now() - new Date(iso).getTime()) / 1000
  if (diff < 60) return 'just now'
  if (diff < 3600) return `${Math.floor(diff / 60)}m`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h`
  if (diff < 86400 * 7) return `${Math.floor(diff / 86400)}d ago`
  return new Date(iso).toLocaleDateString()
}

const scorePct = (s?: number | null) => (s == null ? '' : `${Math.round(s * 100)}%`)

const previewId = ref<string | null>(null)
function openPreview(noteId: string) {
  previewId.value = noteId
}
function closePreview() {
  previewId.value = null
}
</script>

<template>
  <section class="research-view">
    <header class="topbar tight">
      <span>{{ t('research.title') }}</span>
      <span class="spacer"></span>
      <span class="muted" style="font-size: 12px;">{{ t('research.subtitle') }}</span>
    </header>

    <header class="topbar tight" style="gap: 12px;">
      <div class="search-input-wrap">
        <Search :size="14" class="search-icon" />
        <input
          v-model="query"
          class="field search-input"
          :placeholder="t('research.placeholder')"
          @keydown="onKeydown"
        />
      </div>
      <div style="display: flex; gap: 2px;">
        <button
          v-for="t in tabs"
          :key="t.value"
          class="tab"
          :class="{ active: mode === t.value }"
          @click="mode = t.value"
        >
          {{ t.label }}
        </button>
      </div>
      <span class="spacer"></span>
      <FilterPopover
        :selected-tags="filterTags"
        :source="filterSource"
        :date-from="filterDateFrom"
        :date-to="filterDateTo"
        @update:selected-tags="(v) => { filterTags = v }"
        @update:source="(v) => { filterSource = v }"
        @update:date-from="(v) => { filterDateFrom = v }"
        @update:date-to="(v) => { filterDateTo = v }"
      />
      <button
        class="btn btn-primary"
        type="button"
        :disabled="!query.trim() || loading"
        @click="runSearch"
      >
        <Loader2 v-if="loading" :size="13" class="spin" />
        {{ t('research.search-button') }}
      </button>
    </header>

    <div class="active-filter-strip" v-if="filterTags.length || filterSource || filterDateFrom || filterDateTo">
      <span class="muted small">{{ t('research.filters') }}:</span>
      <span v-for="tag in filterTags" :key="tag" class="chip chip-active">
        <Hash :size="10" /> {{ tag }}
      </span>
      <span v-if="filterSource" class="chip chip-active">
        <SourceIcon :size="10" /> {{ filterSource }}
      </span>
      <span v-if="filterDateFrom || filterDateTo" class="chip chip-active">
        <Clock :size="10" /> {{ filterDateFrom || '…' }} → {{ filterDateTo || '…' }}
      </span>
    </div>

    <div class="results-area">
      <div v-if="loading" class="placeholder">
        <Loader2 :size="20" class="spin" /> {{ t('research.searching') }}
      </div>
      <div v-else-if="error" class="placeholder error">{{ error }}</div>
      <div v-else-if="!lastQuery" class="placeholder">
        {{ t('empty.research-empty') }}
      </div>
      <div v-else-if="!results.length" class="placeholder">
        {{ t('empty.research-no-hit') }}
      </div>
      <div v-else class="result-list">
        <div class="result-meta">{{ t('research.result-meta', { count: results.length, mode }) }}</div>
        <article
          v-for="r in results"
          :key="(r.note_id || '') + (r.chunk_id || '')"
          class="result-card"
          @click="openPreview(r.note_id)"
        >
          <div class="result-head">
            <span class="pill square" :style="{ color: typeColor(r.content_type) }">
              {{ typeLabel(r.content_type) }}
            </span>
            <strong class="result-title">{{ r.title }}</strong>
            <span v-if="r.score != null" class="result-score">{{ scorePct(r.score) }}</span>
          </div>
          <p v-if="r.snippet" class="result-snippet">{{ r.snippet }}</p>
          <p v-else-if="r.summary" class="result-snippet muted">{{ r.summary }}</p>
          <div class="result-foot">
            <span v-if="r.source" class="muted small">
              <SourceIcon :size="10" /> {{ r.source }}
            </span>
            <span v-if="r.created_at" class="muted small">
              <Clock :size="10" /> {{ relativeTime(r.created_at) }}
            </span>
            <span class="right-tags">
              <span
                v-for="tag in (r.tags || []).slice(0, 4)"
                :key="tag"
                class="pill square"
              >
                #{{ tag }}
              </span>
              <span v-if="(r.tags || []).length > 4" class="pill square">
                +{{ (r.tags || []).length - 4 }}
              </span>
            </span>
          </div>
        </article>
      </div>
    </div>

    <NotePreview :note-id="previewId" @close="closePreview" />
  </section>
</template>

<style scoped>
.research-view {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.search-input-wrap {
  position: relative;
  display: inline-flex;
  align-items: center;
}
.search-icon {
  position: absolute;
  left: 10px;
  color: var(--muted);
  pointer-events: none;
}
.search-input {
  height: 32px;
  max-width: 480px;
  min-width: 280px;
  font-size: 13px;
  padding-left: 30px;
  background: var(--panel-2);
  border: 1px solid var(--line);
  border-radius: 6px;
  color: var(--text);
}

.active-filter-strip {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 28px;
  border-bottom: 1px solid var(--line);
  flex-wrap: wrap;
}
.chip-active {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 999px;
  background: rgba(98, 107, 230, 0.18);
  border: 1px solid rgba(98, 107, 230, 0.4);
  color: var(--text);
}

.results-area {
  flex: 1;
  overflow-y: auto;
  padding: 18px 28px;
}

.placeholder {
  color: var(--muted);
  text-align: center;
  padding: 60px 16px;
  font-size: 13px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}
.placeholder.error {
  color: var(--red, #ef4444);
}

.result-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.result-meta {
  font-size: 11px;
  color: var(--muted);
  margin-bottom: 6px;
}
.result-card {
  background: var(--panel-2);
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  cursor: pointer;
}
.result-card:hover {
  border-color: rgba(98, 107, 230, 0.45);
}
.result-head {
  display: flex;
  align-items: center;
  gap: 8px;
}
.result-title {
  flex: 1;
  font-size: 14px;
  color: var(--text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.result-score {
  font-size: 11px;
  color: var(--blue);
  font-variant-numeric: tabular-nums;
}
.result-snippet {
  margin: 0;
  font-size: 12.5px;
  line-height: 1.55;
  color: var(--text);
  opacity: 0.85;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.result-foot {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.right-tags {
  margin-left: auto;
  display: inline-flex;
  gap: 4px;
}

.spin {
  animation: spin 1s linear infinite;
}
@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
