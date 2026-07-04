<script setup lang="ts">
import { ref } from 'vue'
import { FileText, Image as ImageIcon, Code2, Table, Plus, Paperclip } from 'lucide-vue-next'
import type { PreviewState } from '../../composables/useIngest'
import { useIngest } from '../../composables/useIngest'

const emit = defineEmits<{ preview: [state: PreviewState] }>()

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

function onSubmit() {
  detectAndPreview(input.value)
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
    class="surface flex flex-col gap-3 p-5 transition-shadow"
    :class="dragOver ? 'border-[#4f46e5] shadow-[0_0_0_3px_rgba(79,70,229,0.15)]' : ''"
    @dragover.prevent="dragOver = true"
    @dragleave="dragOver = false"
    @drop.prevent="onDrop"
  >
    <textarea
      v-model="input"
      class="field textarea min-h-[140px] resize-none border-0 p-0 text-[15px] shadow-none focus:shadow-none"
      placeholder="Ask, paste, drop…  粘贴文本、代码、表格，或拖入 PDF / 图片"
      @paste="onPaste"
    ></textarea>

    <div class="flex flex-wrap items-center gap-2">
      <button class="btn btn-ghost h-8 px-2 text-xs" type="button" @click="fileInput?.click()">
        <Plus :size="13" />
        Add source
      </button>
      <input ref="fileInput" type="file" class="hidden" accept="image/*,.pdf,.md,.txt,.csv,.json,.html,.py,.ts,.js,.go" @change="onFileChange" />

      <div class="mx-1 h-4 w-px bg-[#e5e7eb]"></div>

      <span class="chip chip-muted"><FileText :size="11" /> Text</span>
      <span class="chip chip-muted"><Code2 :size="11" /> Code</span>
      <span class="chip chip-muted"><Table :size="11" /> Table</span>
      <span class="chip chip-muted"><ImageIcon :size="11" /> Image</span>
      <span class="chip chip-muted"><Paperclip :size="11" /> PDF</span>

      <button class="btn btn-primary ml-auto h-8" type="button" :disabled="!input.trim()" @click="onSubmit">
        <Plus :size="14" />
        理解 / 保存
      </button>
    </div>
  </div>
</template>
