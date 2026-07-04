<script setup lang="ts">
import { ref } from 'vue'
import { Plus, Paperclip, Send, FileText, Image as ImageIcon, Code2, Table } from 'lucide-vue-next'
import type { PreviewState } from '../../composables/useIngest'
import { useIngest } from '../../composables/useIngest'

const emit = defineEmits<{
  preview: [state: PreviewState]
  ask: [question: string]
}>()

const ingest = useIngest()
const input = ref('')
const dragOver = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)

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

function onDrop(e: DragEvent) {
  dragOver.value = false
  const file = e.dataTransfer?.files?.[0]
  if (file) {
    emit('preview', ingest.fromFile(file))
    return
  }
  const text = e.dataTransfer?.getData('text')
  if (text) detectAndPreview(text)
}
</script>

<template>
  <div
    class="home-hero-input"
    :class="{ 'is-drag': dragOver }"
    @dragover.prevent="dragOver = true"
    @dragleave="dragOver = false"
    @drop.prevent="onDrop"
  >
    <textarea
      v-model="input"
      class="hero-textarea"
      placeholder="Ask, paste, drop…  直接提问，或粘贴文本/代码/表格，拖入 PDF/图片"
      @paste="onPaste"
      @keydown="onKeydown"
    ></textarea>

    <div class="hero-toolbar">
      <button class="btn btn-ghost hero-tool-btn" type="button" @click="fileInput?.click()">
        <Plus :size="13" />
        Add source
      </button>
      <input
        ref="fileInput"
        type="file"
        class="hidden"
        accept="image/*,.pdf,.md,.txt,.csv,.json,.html,.py,.ts,.js,.go"
        @change="onFileChange"
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
          title="保存为资料"
        >
          保存
        </button>
        <button
          class="btn btn-primary"
          type="button"
          :disabled="!input.trim()"
          @click="onAsk"
          title="提问 (⌘/Ctrl + Enter)"
        >
          <Send :size="13" />
          提问
        </button>
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
  transition: border-color 160ms ease, box-shadow 160ms ease;
}

.home-hero-input.is-drag {
  border-color: var(--blue);
  box-shadow: 0 0 0 3px rgba(98, 107, 230, 0.22);
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

.hero-divider {
  width: 1px;
  height: 14px;
  background: var(--line);
  margin: 0 4px;
}

.hero-toolbar :deep(.chip) {
  cursor: default;
}
</style>
