<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { Search, X, Tag, FileText, Folder, Type, Eye, Network, Sparkles, Library as LibIcon } from 'lucide-vue-next'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { getKnowledgeGraph, getKnowledge } from '../api/knowledge'
import type { KGNode, KGResponse, NoteListItem } from '../api/types'
import GraphCanvas from '../components/graph/GraphCanvas.vue'
import NotePreview from '../components/preview/NotePreview.vue'
import { useUiStore } from '../stores/ui'

const { t } = useI18n()
const router = useRouter()
const ui = useUiStore()

const data = ref<KGResponse | null>(null)
const loading = ref(false)
const error = ref('')
const focusTag = ref('')
const nodeSearch = ref('')
const minTagCount = ref(1)
const minEdgeWeight = ref(1)
const selected = ref<KGNode | null>(null)
const linkedTitles = ref<Record<string, NoteListItem>>({})
const previewId = ref<string | null>(null)
const canvasRef = ref<InstanceType<typeof GraphCanvas> | null>(null)

const stats = computed(() => data.value?.stats)
const nodeCount = computed(() => data.value?.nodes.length ?? 0)

const subtitleText = computed(() => {
  if (!stats.value) return ''
  return t('graph.subtitle', {
    tags: stats.value.tag_count,
    notes: stats.value.note_count,
    edges: stats.value.edge_count,
  })
})

async function load() {
  loading.value = true
  error.value = ''
  try {
    data.value = await getKnowledgeGraph({
      include_notes: true,
      include_categories: true,
      include_content_types: true,
      min_tag_count: minTagCount.value,
      min_edge_weight: minEdgeWeight.value,
      limit_tags: 120,
      limit_notes: 400,
      focus_tag: focusTag.value || undefined,
    })
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    loading.value = false
  }
}

function applyFocus() {
  selected.value = null
  load()
}

function clearFocus() {
  focusTag.value = ''
  selected.value = null
  load()
}

function onNodeClick(node: KGNode | null) {
  selected.value = node
}

function onFocusTag(tag: string) {
  // Don't auto-refocus on every click — only when user hits Enter in the focus box.
  // Keeping the focus input authoritative avoids clobbering exploration.
  // But still surface the click by selecting.
  // (No-op here; legacy behavior refocused immediately which surprised users.)
  void tag
}

function searchTagInResearch(tag: string) {
  router.push({ path: '/research', query: { tag } })
}

function askAboutTag(tag: string) {
  ui.openAsk(null, t('graph.ask-prefill', { tag }))
}

function openTagInLibrary(tag: string) {
  router.push({ path: '/library', query: { tag } })
}

const linkedNoteIds = computed<string[]>(() => {
  if (!selected.value || !data.value) return []
  const id = selected.value.id
  const out: string[] = []
  for (const e of data.value.edges) {
    if (e.source === id && e.target.startsWith('note:')) out.push(e.target.substring(5))
    else if (e.target === id && e.source.startsWith('note:')) out.push(e.source.substring(5))
  }
  return out
})

watch(linkedNoteIds, async (ids) => {
  const missing = ids.filter((id) => !linkedTitles.value[id])
  if (!missing.length) return
  await Promise.all(
    missing.map(async (id) => {
      try {
        const note = await getKnowledge(id)
        linkedTitles.value[id] = note
      } catch {
        /* leave missing */
      }
    }),
  )
}, { immediate: true })

watch(nodeSearch, (q) => {
  canvasRef.value?.resetHighlight()
  void q
})

function openNotePreview(noteId: string) {
  previewId.value = noteId
}
function closeNotePreview() {
  previewId.value = null
}

const nodeIcon = (type: string) => {
  if (type === 'tag') return Tag
  if (type === 'category') return Folder
  if (type === 'content_type') return Type
  return FileText
}

onMounted(load)
</script>

<template>
  <section class="graph-view">
    <header class="topbar tight">
      <span>{{ t('graph.title') }}</span>
      <span class="spacer"></span>
      <span v-if="subtitleText" class="muted stat-strip">{{ subtitleText }}</span>
    </header>

    <header class="topbar tight">
      <div class="search-row">
        <Search :size="14" style="color: var(--muted);" />
        <input
          v-model="focusTag"
          class="field"
          :placeholder="t('graph.focus-placeholder')"
          style="height: 30px; font-size: 13px; flex: 1; max-width: 280px;"
          @keydown.enter="applyFocus"
        />
        <button v-if="focusTag" class="icon-button" @click="clearFocus" :title="t('action.close')">
          <X :size="14" />
        </button>
      </div>
      <div class="search-row">
        <Network :size="14" style="color: var(--muted);" />
        <input
          v-model="nodeSearch"
          class="field"
          :placeholder="t('graph.search-placeholder')"
          style="height: 30px; font-size: 13px; flex: 1; max-width: 220px;"
        />
        <button v-if="nodeSearch" class="icon-button" @click="nodeSearch = ''" :title="t('action.close')">
          <X :size="14" />
        </button>
      </div>
      <div class="slider-group">
        <label>
          {{ t('graph.min-tag-count') }}
          <input type="range" min="1" max="10" v-model.number="minTagCount" @change="load" />
          <span class="badge-num">{{ minTagCount }}</span>
        </label>
        <label>
          {{ t('graph.min-edge-weight') }}
          <input type="range" min="1" max="10" v-model.number="minEdgeWeight" @change="load" />
          <span class="badge-num">{{ minEdgeWeight }}</span>
        </label>
      </div>
      <span class="spacer"></span>
      <button class="btn btn-ghost" style="height: 30px; font-size: 12px;" @click="load">
        {{ t('action.reload') }}
      </button>
    </header>

    <div class="graph-body">
      <div v-if="loading" class="placeholder">{{ t('graph.loading') }}</div>
      <div v-else-if="error" class="placeholder err">{{ error }}</div>
      <div v-else-if="!nodeCount" class="placeholder">
        {{ t('empty.graph') }}
      </div>
      <div v-else class="canvas-wrap">
        <GraphCanvas
          ref="canvasRef"
          :nodes="data!.nodes"
          :edges="data!.edges"
          :search-query="nodeSearch"
          @select-node="onNodeClick"
          @focus-tag="onFocusTag"
        />

        <div class="legend-overlay">
          <div class="legend-title">{{ t('graph.legend-title') }}</div>
          <div class="legend-row">
            <span class="legend-dot" style="background: #626be6;"></span>
            <span>{{ t('graph.legend-tag') }}</span>
          </div>
          <div class="legend-row">
            <span class="legend-dot" style="background: #4aaeff;"></span>
            <span>{{ t('graph.legend-category') }}</span>
          </div>
          <div class="legend-row">
            <span class="legend-dot" style="background: #e0a23a;"></span>
            <span>{{ t('graph.legend-content-type') }}</span>
          </div>
          <div class="legend-row">
            <span class="legend-dot small" style="background: #7d808a;"></span>
            <span>{{ t('graph.legend-note') }}</span>
          </div>
          <div class="legend-divider"></div>
          <div class="legend-row">
            <span class="legend-line solid"></span>
            <span>{{ t('graph.edge-cooccurs') }}</span>
          </div>
          <div class="legend-row">
            <span class="legend-line dashed"></span>
            <span>{{ t('graph.edge-has-tag') }}</span>
          </div>
          <div class="legend-divider"></div>
          <div class="legend-row">
            <span class="legend-ring"></span>
            <span>{{ t('graph.bridge-hint') }}</span>
          </div>
        </div>
      </div>

      <aside v-if="selected" class="detail-panel">
        <header>
          <component :is="nodeIcon(selected.type)" :size="14" />
          <span>{{ selected.label }}</span>
          <button class="icon-button" @click="selected = null"><X :size="14" /></button>
        </header>
        <div class="meta-grid">
          <div><span class="label">{{ t('graph.type') }}</span><span>{{ selected.type }}</span></div>
          <div><span class="label">{{ t('graph.weight') }}</span><span>{{ selected.weight ?? '—' }}</span></div>
          <div><span class="label">ID</span><span class="mono small">{{ selected.id }}</span></div>
        </div>

        <div v-if="selected.type === 'tag'" class="actions-block">
          <div class="block-label">{{ t('graph.actions-title') }}</div>
          <button class="action-btn" @click="searchTagInResearch(selected.label)">
            <Search :size="13" /> {{ t('action.search') }}
          </button>
          <button class="action-btn" @click="askAboutTag(selected.label)">
            <Sparkles :size="13" /> {{ t('action.ask-about') }}
          </button>
          <button class="action-btn" @click="openTagInLibrary(selected.label)">
            <LibIcon :size="13" /> {{ t('action.open-in-library') }}
          </button>
        </div>

        <div v-if="selected.type === 'tag'" class="hint">
          {{ t('graph.hint-focus') }}
        </div>
        <div v-if="linkedNoteIds.length" class="notes">
          <div class="label">{{ t('graph.linked-notes', { count: linkedNoteIds.length }) }}</div>
          <ul>
            <li v-for="id in linkedNoteIds.slice(0, 20)" :key="id" class="note-link" @click="openNotePreview(id)">
              <Eye :size="11" class="eye-icon" />
              <span>{{ linkedTitles[id]?.title || id.slice(0, 16) + '…' }}</span>
            </li>
          </ul>
        </div>
      </aside>
    </div>

    <NotePreview :note-id="previewId" @close="closeNotePreview" />
  </section>
</template>

<style scoped>
.graph-view {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.search-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.slider-group {
  display: flex;
  gap: 16px;
  font-size: 11px;
  color: var(--muted);
}
.slider-group label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.slider-group input[type='range'] {
  width: 90px;
}
.badge-num {
  background: var(--panel-3);
  padding: 1px 6px;
  border-radius: 4px;
  color: var(--text);
  font-size: 10px;
  font-variant-numeric: tabular-nums;
}

.stat-strip {
  font-size: 11px;
  font-variant-numeric: tabular-nums;
}

.graph-body {
  flex: 1;
  display: flex;
  gap: 12px;
  padding: 12px 16px;
  min-height: 0;
  position: relative;
}

.canvas-wrap {
  flex: 1;
  border-radius: var(--r-md, 8px);
  border: 1px solid var(--line);
  overflow: hidden;
  min-width: 0;
  position: relative;
}

.legend-overlay {
  position: absolute;
  top: 12px;
  left: 12px;
  background: rgba(13, 16, 17, 0.78);
  backdrop-filter: blur(6px);
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 10px 12px;
  font-size: 11px;
  color: var(--text);
  display: flex;
  flex-direction: column;
  gap: 5px;
  pointer-events: none;
  max-width: 200px;
  z-index: 5;
}
.legend-title {
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.6px;
  color: var(--muted);
  margin-bottom: 4px;
}
.legend-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
  border: 1px solid rgba(255, 255, 255, 0.2);
}
.legend-dot.small {
  width: 6px;
  height: 6px;
  margin-left: 2px;
  margin-right: 2px;
}
.legend-line {
  width: 18px;
  height: 0;
  border-top: 2px solid #626be6;
  flex-shrink: 0;
}
.legend-line.dashed {
  border-top: 1.5px dashed #5a5d68;
}
.legend-ring {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  border: 1.2px dashed #f0b8ad;
  flex-shrink: 0;
}
.legend-divider {
  height: 1px;
  background: var(--line);
  margin: 4px 0;
}

.detail-panel {
  width: 280px;
  flex-shrink: 0;
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: var(--r-md, 8px);
  display: flex;
  flex-direction: column;
  overflow-y: auto;
}
.detail-panel header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border-bottom: 1px solid var(--line);
  color: var(--text);
  font-size: 13px;
  font-weight: 600;
}
.detail-panel header button {
  margin-left: auto;
}
.meta-grid {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px;
  border-bottom: 1px solid var(--line);
  font-size: 12px;
}
.meta-grid > div {
  display: flex;
  justify-content: space-between;
  gap: 8px;
}
.meta-grid .label {
  color: var(--muted);
}
.mono {
  font-family: var(--mono, monospace);
}
.small {
  font-size: 11px;
  color: var(--muted);
  word-break: break-all;
}

.actions-block {
  padding: 12px;
  border-bottom: 1px solid var(--line);
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.block-label {
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.6px;
  color: var(--muted);
  margin-bottom: 4px;
}
.action-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 7px 10px;
  font-size: 12px;
  border-radius: 6px;
  border: 1px solid var(--line);
  background: var(--panel-2);
  color: var(--text);
  cursor: pointer;
  transition: background 120ms ease, border-color 120ms ease;
  text-align: left;
}
.action-btn:hover {
  background: var(--panel-3);
  border-color: rgba(98, 107, 230, 0.5);
}

.hint {
  padding: 10px 12px;
  font-size: 11px;
  color: var(--muted);
  border-bottom: 1px solid var(--line);
  line-height: 1.5;
}
.notes ul {
  margin: 0;
  padding: 6px 12px 12px 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  list-style: none;
}

.note-link {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 8px;
  border-radius: 5px;
  font-size: 12px;
  color: var(--text);
  cursor: pointer;
  transition: background 120ms ease;
}
.note-link:hover {
  background: var(--panel-2);
}
.note-link span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
}
.eye-icon {
  color: var(--muted);
  flex-shrink: 0;
}
.notes .label {
  display: block;
  padding: 10px 12px 4px;
  font-size: 11px;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.placeholder {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--muted);
  font-size: 13px;
}
.placeholder.err {
  color: #f0b8ad;
}
</style>
