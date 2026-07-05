<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Plus, Paperclip, Send, FileText, Image as ImageIcon, Code2, Table, FolderUp, Files } from 'lucide-vue-next'
import type { PreviewState } from '../../composables/useIngest'
import { useIngest } from '../../composables/useIngest'
import { useUiStore } from '../../stores/ui'

const { t } = useI18n()

const emit = defineEmits<{
  preview: [state: PreviewState]
  ask: [question: string]
}>()

const ui = useUiStore()
const ingest = useIngest()
const input = ref(ui.askPrefill || '')
const dragOver = ref(false)
const dragKind = ref<'idle' | 'single' | 'batch' | 'folder'>('idle')
const fileInput = ref<HTMLInputElement | null>(null)
const multiInput = ref<HTMLInputElement | null>(null)
const dirInput = ref<HTMLInputElement | null>(null)

const addSourceOpen = ref(false)
const addSourceRoot = ref<HTMLElement | null>(null)

function detectAndPreview(text: string) {
  if (!text.trim()) return
  const next = ingest.fromText(text)
  if (next) emit('preview', next)
}

function onPaste(e: ClipboardEvent) {
  const text = e.clipboardData?.getData('text') ?? ''
  if (text.trim()) {
    e.preventDefault()
    input.value = text
    detectAndPreview(text)
  }
}

function onSave() {
  detectAndPreview(input.value)
}

function onAsk() {
  const text = input.value.trim()
  if (!text) return
  emit('ask', text)
  input.value = ''
}

function onKeydown(e: KeyboardEvent) {
  if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
    e.preventDefault()
    onAsk()
  }
}

function onFileChange(e: Event) {
  const target = e.target as HTMLInputElement
  const file = target.files?.[0]
  if (file) emit('preview', ingest.fromFile(file))
  target.value = ''
}

function onMultiChange(e: Event) {
  const target = e.target as HTMLInputElement
  const files = target.files
  if (files && files.length) ingest.uploadFiles(files)
  target.value = ''
}

function onDirChange(e: Event) {
  const target = e.target as HTMLInputElement
  const files = target.files
  if (files && files.length) ingest.uploadFiles(files, 'folder')
  target.value = ''
}

function pickSingle() {
  addSourceOpen.value = false
  fileInput.value?.click()
}
function pickMulti() {
  addSourceOpen.value = false
  multiInput.value?.click()
}
function pickFolder() {
  addSourceOpen.value = false
  dirInput.value?.click()
}

function onClickOutside(e: MouseEvent) {
  if (!addSourceOpen.value) return
  if (addSourceRoot.value && !addSourceRoot.value.contains(e.target as Node)) {
    addSourceOpen.value = false
  }
}
onMounted(() => document.addEventListener('mousedown', onClickOutside))
onUnmounted(() => document.removeEventListener('mousedown', onClickOutside))

watch(
  () => ui.askPrefillNonce,
  (n) => {
    if (n && ui.askPrefill) {
      const q = ui.askPrefill
      ui.askPrefill = ''
      input.value = q
      emit('ask', q)
    }
  },
)

type FsEntry = {
  isFile: boolean
  isDirectory: boolean
  name: string
  file?: (cb: (f: File) => void, err: (e: unknown) => void) => void
  createReader?: () => {
    readEntries: (cb: (entries: FsEntry[]) => void, err: (e: unknown) => void) => void
  }
}

function readAllDirEntries(reader: ReturnType<NonNullable<FsEntry['createReader']>>): Promise<FsEntry[]> {
  return new Promise((resolve) => {
    const all: FsEntry[] = []
    const readBatch = () => {
      reader.readEntries(
        (batch) => {
          if (!batch.length) {
            resolve(all)
            return
          }
          all.push(...batch)
          readBatch()
        },
        () => resolve(all),
      )
    }
    readBatch()
  })
}

async function collectFilesFromEntry(entry: FsEntry, prefix = ''): Promise<File[]> {
  if (entry.isFile && entry.file) {
    return new Promise((resolve) => {
      entry.file!(
        (f) => {
          const path = prefix + f.name
          const withPath = Object.assign(f, { webkitRelativePath: path })
          resolve([withPath])
        },
        () => resolve([]),
      )
    })
  }
  if (entry.isDirectory && entry.createReader) {
    const reader = entry.createReader()
    const children = await readAllDirEntries(reader)
    const nested = await Promise.all(
      children.map((c) => collectFilesFromEntry(c, prefix + entry.name + '/')),
    )
    return nested.flat()
  }
  return []
}

function sniffDragKind(e: DragEvent): 'folder' | 'batch' | 'single' | 'text' {
  const items = e.dataTransfer?.items
  if (items && items.length) {
    let dirCount = 0
    let fileCount = 0
    for (let i = 0; i < items.length; i++) {
      const it = items[i]
      const entry = (it as unknown as { webkitGetAsEntry?: () => FsEntry | null }).webkitGetAsEntry?.()
      if (entry?.isDirectory) dirCount++
      else if (entry?.isFile) fileCount++
    }
    if (dirCount > 0) return 'folder'
    if (fileCount > 1) return 'batch'
    if (fileCount === 1) return 'single'
  }
  const files = e.dataTransfer?.files
  if (files && files.length > 1) return 'batch'
  if (files && files.length === 1) return 'single'
  return 'text'
}

function onDragOver(e: DragEvent) {
  dragOver.value = true
  const k = sniffDragKind(e)
  dragKind.value = k === 'text' ? 'idle' : k
}

function onDragLeave() {
  dragOver.value = false
  dragKind.value = 'idle'
}

async function onDrop(e: DragEvent) {
  dragOver.value = false
  dragKind.value = 'idle'
  const kind = sniffDragKind(e)
  const items = e.dataTransfer?.items
  if (items && items.length && kind === 'folder') {
    const entries: FsEntry[] = []
    for (let i = 0; i < items.length; i++) {
      const it = items[i]
      const entry = (it as unknown as { webkitGetAsEntry?: () => FsEntry | null }).webkitGetAsEntry?.()
      if (entry) entries.push(entry)
    }
    const fileLists = await Promise.all(entries.map((entry) => collectFilesFromEntry(entry)))
    const files = fileLists.flat()
    if (files.length) ingest.uploadFiles(files, 'folder')
    return
  }
  const files = e.dataTransfer?.files
  if (files && files.length > 1) {
    ingest.uploadFiles(files)
    return
  }
  const file = files?.[0]
  if (file) {
    emit('preview', ingest.fromFile(file))
    return
  }
  const text = e.dataTransfer?.getData('text')
  if (text) detectAndPreview(text)
}

const dragHint = computed(() => {
  switch (dragKind.value) {
    case 'folder': return t('home.drop-folder')
    case 'batch': return t('home.drop-batch')
    case 'single': return t('home.drop-single')
    default: return ''
  }
})

const dragSub = computed(() => {
  switch (dragKind.value) {
    case 'folder': return t('home.drop-folder-sub')
    case 'batch': return t('home.drop-batch-sub')
    default: return ''
  }
})
</script>

<template>
  <div
    class="home-hero-input"
    :class="{ 'is-drag': dragOver, [`drag-${dragKind}`]: dragOver }"
    @dragover.prevent="onDragOver"
    @dragleave="onDragLeave"
    @drop.prevent="onDrop"
  >
    <textarea
      v-model="input"
      class="hero-textarea"
      :placeholder="t('home.hero-placeholder')"
      @paste="onPaste"
      @keydown="onKeydown"
    ></textarea>

    <div v-if="dragOver" class="drag-banner">
      <span class="drag-title">{{ t('home.release-hint', { action: dragHint }) }}</span>
      <span class="muted small">{{ dragSub }}</span>
    </div>

    <div class="hero-toolbar">
      <div ref="addSourceRoot" class="add-source-host">
        <button
          class="btn btn-ghost hero-tool-btn"
          type="button"
          :class="{ active: addSourceOpen }"
          @click="addSourceOpen = !addSourceOpen"
          :title="t('home.add-source-tooltip')"
        >
          <Plus :size="13" />
          {{ t('home.add-source') }}
        </button>
        <div v-if="addSourceOpen" class="add-source-menu">
          <button type="button" class="source-option" @click="pickSingle">
            <span class="opt-icon"><FileText :size="13" /></span>
            <span class="opt-body">
              <span class="opt-label">{{ t('home.single-file') }}</span>
              <span class="opt-hint">{{ t('home.single-file-hint') }}</span>
            </span>
          </button>
          <button type="button" class="source-option" @click="pickMulti">
            <span class="opt-icon"><Files :size="13" /></span>
            <span class="opt-body">
              <span class="opt-label">{{ t('home.multi-files') }}</span>
              <span class="opt-hint">{{ t('home.multi-files-hint') }}</span>
            </span>
          </button>
          <button type="button" class="source-option" @click="pickFolder">
            <span class="opt-icon"><FolderUp :size="13" /></span>
            <span class="opt-body">
              <span class="opt-label">{{ t('home.folder') }}</span>
              <span class="opt-hint">{{ t('home.folder-hint') }}</span>
            </span>
          </button>
        </div>
      </div>
      <input
        ref="fileInput"
        type="file"
        class="hidden"
        accept="image/*,.pdf,.md,.txt,.csv,.json,.html,.py,.ts,.js,.go"
        @change="onFileChange"
      />
      <input
        ref="multiInput"
        type="file"
        class="hidden"
        multiple
        accept="image/*,.pdf,.md,.txt,.csv,.json,.html,.py,.ts,.js,.go"
        @change="onMultiChange"
      />
      <input
        ref="dirInput"
        type="file"
        class="hidden"
        webkitdirectory
        directory
        mozdirectory
        @change="onDirChange"
      />

      <div class="hero-divider"></div>

      <span class="chip chip-muted"><FileText :size="11" /> Text</span>
      <span class="chip chip-muted"><Code2 :size="11" /> Code</span>
      <span class="chip chip-muted"><Table :size="11" /> Table</span>
      <span class="chip chip-muted"><ImageIcon :size="11" /> Image</span>
      <span class="chip chip-muted"><Paperclip :size="11" /> PDF</span>

      <div style="margin-left: auto; display: flex; gap: 8px;">
        <button
          class="btn"
          type="button"
          :disabled="!input.trim()"
          @click="onSave"
          :title="t('home.save-tooltip')"
        >
          {{ t('home.save') }}
        </button>
        <button
          class="btn btn-primary"
          type="button"
          :disabled="!input.trim()"
          @click="onAsk"
          :title="t('home.ask-tooltip')"
        >
          <Send :size="13" />
          {{ t('home.ask') }}
        </button>
      </div>
    </div>

    <div v-if="ingest.batch.value.items.length" class="batch-strip">
      <div class="batch-head">
        <span>Uploading {{ ingest.batchProgress.value.done }}/{{ ingest.batchProgress.value.total }}</span>
        <div class="batch-bar">
          <div class="batch-bar-fill" :style="{ width: ingest.batchProgress.value.pct + '%' }"></div>
        </div>
        <button v-if="!ingest.batch.value.running" class="icon-button" @click="ingest.clearBatch">✕</button>
      </div>
      <div class="batch-list">
        <div
          v-for="(item, i) in ingest.batch.value.items.slice(0, 12)"
          :key="i"
          class="batch-item"
          :class="item.status"
          :title="item.file.name + (item.error ? ' — ' + item.error : '')"
        >
          <span class="batch-name">{{ item.file.name }}</span>
          <span class="batch-status">{{ item.status }}</span>
        </div>
        <span v-if="ingest.batch.value.items.length > 12" class="muted small">
          + {{ ingest.batch.value.items.length - 12 }} more
        </span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.home-hero-input {
  width: min(720px, 100%);
  background: var(--panel-2);
  border: 1px solid var(--line);
  border-radius: var(--r-md);
  padding: 14px 16px 10px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  position: relative;
  transition: border-color 160ms ease, box-shadow 160ms ease;
}

.home-hero-input.is-drag {
  border-color: var(--blue);
  box-shadow: 0 0 0 3px rgba(98, 107, 230, 0.22);
}

.drag-banner {
  position: absolute;
  inset: 6px;
  border: 2px dashed var(--blue);
  border-radius: var(--r-md);
  background: rgba(98, 107, 230, 0.08);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  pointer-events: none;
  z-index: 4;
}
.drag-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text);
}

.hero-textarea {
  width: 100%;
  min-height: 96px;
  resize: vertical;
  background: transparent;
  border: 0;
  outline: none;
  color: var(--text);
  font-size: 15px;
  line-height: 1.5;
  font-family: inherit;
}

.hero-textarea::placeholder {
  color: #6e6f75;
}

.hero-toolbar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.hero-tool-btn {
  height: 28px;
  padding: 0 10px;
  font-size: 12px;
}
.hero-tool-btn.active {
  background: var(--panel-3);
  border-color: var(--blue);
}

.hero-divider {
  width: 1px;
  height: 14px;
  background: var(--line);
  margin: 0 4px;
}

.hero-toolbar :deep(.chip) {
  cursor: default;
}

.add-source-host {
  position: relative;
  display: inline-flex;
}

.add-source-menu {
  position: absolute;
  top: calc(100% + 6px);
  left: 0;
  width: 240px;
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: var(--r-md, 8px);
  box-shadow: 0 12px 36px rgba(0, 0, 0, 0.4);
  z-index: 50;
  padding: 4px;
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.source-option {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  background: transparent;
  border: 0;
  border-radius: 5px;
  color: var(--text);
  cursor: pointer;
  text-align: left;
  font-size: 12px;
}
.source-option:hover {
  background: var(--panel-2);
}
.opt-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 5px;
  background: rgba(98, 107, 230, 0.15);
  color: var(--blue);
  flex-shrink: 0;
}
.opt-body {
  display: flex;
  flex-direction: column;
  gap: 1px;
}
.opt-label {
  font-size: 12px;
  font-weight: 500;
}
.opt-hint {
  font-size: 10px;
  color: var(--muted);
}
</style>
