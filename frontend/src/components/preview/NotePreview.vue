<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { marked } from 'marked'
import { X, Loader2, FileWarning, Download, ExternalLink } from 'lucide-vue-next'
import { getKnowledge } from '../../api/knowledge'
import { API_BASE } from '../../api/http'
import type { NoteDetail } from '../../api/types'

const props = defineProps<{ noteId: string | null }>()
const emit = defineEmits<{ close: [] }>()

const note = ref<NoteDetail | null>(null)
const loading = ref(false)
const error = ref('')

async function load() {
  if (!props.noteId) {
    note.value = null
    return
  }
  loading.value = true
  error.value = ''
  note.value = null
  try {
    note.value = await getKnowledge(props.noteId)
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch(() => props.noteId, load)

function onKey(e: KeyboardEvent) {
  if (e.key === 'Escape') emit('close')
}
onMounted(() => window.addEventListener('keydown', onKey))

const fileUrl = computed(() => {
  if (!note.value) return ''
  return `${API_BASE}/knowledge/${note.value.id}/file`
})

const hasFile = computed(() => {
  const meta = (note.value as NoteDetail & { metadata?: Record<string, unknown> } | null)?.metadata
  return Boolean(meta && typeof meta === 'object' && 'stored_path' in meta)
})

const contentKind = computed<'markdown' | 'code' | 'html' | 'image' | 'pdf' | 'table' | 'text' | 'unknown'>(() => {
  if (!note.value) return 'unknown'
  const t = note.value.content_type
  if (t === 'image') return 'image'
  if (t === 'code') return 'code'
  if (t === 'table') return 'table'
  if (t === 'document') {
    const ext = (note.value as NoteDetail & { metadata?: Record<string, unknown> }).metadata?.extension as string | undefined
    if (ext?.toLowerCase() === '.pdf' || note.value.title.toLowerCase().endsWith('.pdf')) return 'pdf'
    if (ext?.toLowerCase() === '.html' || note.value.title.toLowerCase().endsWith('.html')) return 'html'
    return 'markdown'
  }
  if (t === 'text') return 'markdown'
  return 'text'
})

const renderedMarkdown = computed(() => {
  if (!note.value) return ''
  if (contentKind.value !== 'markdown') return ''
  try {
    return marked.parse(note.value.content || '', { async: false }) as string
  } catch {
    return ''
  }
})

const codeLanguage = computed(() => {
  const meta = (note.value as NoteDetail & { metadata?: Record<string, unknown> } | null)?.metadata
  return (meta?.language as string) || ''
})

const tableRows = computed<string[][]>(() => {
  if (!note.value || contentKind.value !== 'table') return []
  const text = note.value.content || ''
  const lines = text.split(/\r?\n/).filter((l) => l.trim())
  return lines.map((line) => line.split(',').map((c) => c.trim()))
})
</script>

<template>
  <Teleport to="body">
    <template v-if="noteId">
      <div class="preview-backdrop" @click="emit('close')"></div>
      <aside class="preview-panel" role="dialog" aria-modal="true">
        <header class="preview-head">
          <div class="head-title">
            <span v-if="note">{{ note.title }}</span>
            <span v-else-if="loading">Loading…</span>
            <span v-else>{{ noteId }}</span>
          </div>
          <div class="head-actions">
            <a
              v-if="note && hasFile"
              :href="fileUrl"
              download
              class="icon-button"
              title="Download"
            >
              <Download :size="14" />
            </a>
            <a
              v-if="note && hasFile"
              :href="fileUrl"
              target="_blank"
              rel="noopener"
              class="icon-button"
              title="Open in new tab"
            >
              <ExternalLink :size="14" />
            </a>
            <button class="icon-button" type="button" @click="emit('close')" aria-label="Close">
              <X :size="16" />
            </button>
          </div>
        </header>

        <div v-if="note" class="preview-meta-bar">
          <span class="badge">{{ note.content_type }}</span>
          <span v-if="note.source" class="muted small">{{ note.source }}</span>
          <span class="muted small">{{ note.created_at?.slice(0, 10) }}</span>
          <span class="tag-row">
            <span v-for="tag in (note.tags || []).slice(0, 6)" :key="tag" class="tag-chip">#{{ tag }}</span>
          </span>
        </div>

        <div class="preview-body">
          <div v-if="loading" class="placeholder"><Loader2 :size="20" class="spin" /></div>
          <div v-else-if="error" class="placeholder error">
            <FileWarning :size="20" /> {{ error }}
          </div>
          <template v-else-if="note">
            <div v-if="contentKind === 'image'" class="media-wrap">
              <img v-if="hasFile" :src="fileUrl" :alt="note.title" />
              <pre v-else class="fallback-text">{{ note.content }}</pre>
            </div>

            <div v-else-if="contentKind === 'pdf'" class="media-wrap">
              <iframe v-if="hasFile" :src="fileUrl" :title="note.title"></iframe>
              <pre v-else class="fallback-text">{{ note.content }}</pre>
            </div>

            <div v-else-if="contentKind === 'html'" class="media-wrap">
              <iframe
                v-if="note.content"
                :srcdoc="note.content"
                :title="note.title"
                sandbox=""
              ></iframe>
              <iframe v-else-if="hasFile" :src="fileUrl" :title="note.title"></iframe>
            </div>

            <div v-else-if="contentKind === 'code'" class="code-wrap">
              <div class="code-head">
                <span class="muted small">{{ codeLanguage || 'code' }}</span>
              </div>
              <pre class="code-block"><code>{{ note.content }}</code></pre>
            </div>

            <div v-else-if="contentKind === 'table'" class="table-wrap">
              <table v-if="tableRows.length">
                <thead>
                  <tr><th v-for="(c, i) in tableRows[0]" :key="i">{{ c }}</th></tr>
                </thead>
                <tbody>
                  <tr v-for="(row, ri) in tableRows.slice(1)" :key="ri">
                    <td v-for="(c, ci) in row" :key="ci">{{ c }}</td>
                  </tr>
                </tbody>
              </table>
              <pre v-else class="fallback-text">{{ note.content }}</pre>
            </div>

            <article v-else-if="contentKind === 'markdown'" class="md-body" v-html="renderedMarkdown"></article>

            <pre v-else class="fallback-text">{{ note.content }}</pre>
          </template>
        </div>
      </aside>
    </template>
  </Teleport>
</template>

<style scoped>
.preview-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.55);
  z-index: 70;
  backdrop-filter: blur(2px);
}

.preview-panel {
  position: fixed;
  top: 32px;
  bottom: 32px;
  left: 50%;
  transform: translateX(-50%);
  width: min(960px, calc(100vw - 32px));
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 12px;
  z-index: 71;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 16px 48px rgba(0, 0, 0, 0.5);
}

.preview-head {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  border-bottom: 1px solid var(--line);
  background: var(--panel-2);
}
.head-title {
  flex: 1;
  font-size: 14px;
  font-weight: 600;
  color: var(--text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.head-actions {
  display: inline-flex;
  gap: 4px;
}
.head-actions a,
.head-actions button {
  width: 30px;
  height: 30px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  background: transparent;
  border: 1px solid transparent;
  color: var(--muted);
  cursor: pointer;
  text-decoration: none;
}
.head-actions a:hover,
.head-actions button:hover {
  background: var(--panel-3);
  color: var(--text);
}

.preview-meta-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 16px;
  border-bottom: 1px solid var(--line);
  background: var(--panel);
  flex-wrap: wrap;
}
.badge {
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  background: var(--panel-3);
  color: var(--text);
  padding: 2px 6px;
  border-radius: 4px;
}
.tag-row {
  display: inline-flex;
  gap: 4px;
  flex-wrap: wrap;
}
.tag-chip {
  font-size: 10px;
  color: var(--muted);
  background: var(--panel-2);
  padding: 1px 6px;
  border-radius: 8px;
}

.preview-body {
  flex: 1;
  overflow-y: auto;
  background: var(--bg);
  position: relative;
}

.placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 60px 16px;
  color: var(--muted);
  font-size: 13px;
}
.placeholder.error {
  color: var(--red, #ef4444);
}

.media-wrap {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100%;
  padding: 16px;
}
.media-wrap img {
  max-width: 100%;
  max-height: calc(100vh - 200px);
  object-fit: contain;
  border-radius: 6px;
}
.media-wrap iframe {
  width: 100%;
  height: calc(100vh - 200px);
  border: 0;
  background: white;
  border-radius: 6px;
}

.code-wrap {
  display: flex;
  flex-direction: column;
  height: 100%;
}
.code-head {
  padding: 8px 16px;
  border-bottom: 1px solid var(--line);
  background: var(--panel-2);
}
.code-block {
  margin: 0;
  padding: 16px;
  font-family: var(--mono, 'SF Mono', Menlo, monospace);
  font-size: 12.5px;
  line-height: 1.6;
  color: var(--text);
  white-space: pre;
  overflow-x: auto;
  background: var(--bg);
}

.table-wrap {
  padding: 16px;
  overflow-x: auto;
}
.table-wrap table {
  border-collapse: collapse;
  width: 100%;
  font-size: 13px;
}
.table-wrap th,
.table-wrap td {
  border: 1px solid var(--line);
  padding: 6px 10px;
  text-align: left;
}
.table-wrap th {
  background: var(--panel-2);
  font-weight: 600;
  color: var(--text);
}

.md-body {
  padding: 24px 32px;
  color: var(--text);
  font-size: 14px;
  line-height: 1.7;
  max-width: 760px;
  margin: 0 auto;
}
.md-body :deep(h1),
.md-body :deep(h2),
.md-body :deep(h3) {
  margin: 1.4em 0 0.6em;
  color: var(--text);
  font-weight: 700;
}
.md-body :deep(h1) { font-size: 22px; }
.md-body :deep(h2) { font-size: 18px; }
.md-body :deep(h3) { font-size: 15px; }
.md-body :deep(p) { margin: 0.6em 0; }
.md-body :deep(ul),
.md-body :deep(ol) {
  margin: 0.6em 0;
  padding-left: 1.6em;
}
.md-body :deep(li) { margin: 0.2em 0; }
.md-body :deep(code) {
  background: var(--panel-2);
  padding: 1px 5px;
  border-radius: 3px;
  font-family: var(--mono, monospace);
  font-size: 12.5px;
}
.md-body :deep(pre) {
  background: var(--panel-2);
  padding: 12px 14px;
  border-radius: 6px;
  overflow-x: auto;
  font-size: 12.5px;
  line-height: 1.5;
}
.md-body :deep(pre code) {
  background: transparent;
  padding: 0;
}
.md-body :deep(blockquote) {
  border-left: 3px solid var(--blue);
  margin: 0.8em 0;
  padding: 0.2em 1em;
  color: var(--muted);
}
.md-body :deep(a) {
  color: var(--blue);
  text-decoration: none;
}
.md-body :deep(table) {
  border-collapse: collapse;
  margin: 0.8em 0;
}
.md-body :deep(th),
.md-body :deep(td) {
  border: 1px solid var(--line);
  padding: 4px 8px;
}

.fallback-text {
  margin: 0;
  padding: 16px 24px;
  font-family: var(--mono, monospace);
  font-size: 12.5px;
  line-height: 1.6;
  color: var(--text);
  white-space: pre-wrap;
  word-break: break-word;
}

.spin {
  animation: spin 1s linear infinite;
}
@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.muted {
  color: var(--muted);
}
.small {
  font-size: 11px;
}
</style>
