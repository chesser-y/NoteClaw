<script setup lang="ts">
import { computed } from 'vue'
import { FileText, Image as ImageIcon, Code2, Table, File } from 'lucide-vue-next'
import type { PreviewState } from '../../composables/useIngest'

const props = defineProps<{ preview: PreviewState }>()

const iconFor = {
  text: FileText,
  code: Code2,
  table: Table,
  image: ImageIcon,
  document: File,
  unknown: FileText,
}

const imageUrl = computed(() => {
  if (props.preview.kind === 'image' && props.preview.file) {
    return typeof URL !== 'undefined' && 'createObjectURL' in URL
      ? URL.createObjectURL(props.preview.file)
      : ''
  }
  return ''
})
</script>

<template>
  <div class="surface flex flex-col p-4">
    <div class="mb-3 flex items-center gap-2">
      <component :is="iconFor[props.preview.kind]" :size="16" class="text-[#929399]" />
      <span class="text-xs font-medium uppercase tracking-wide text-[#929399]">Content preview</span>
      <span class="ml-auto chip chip-muted">{{ props.preview.contentType }}</span>
    </div>
    <div class="mb-2 truncate text-sm font-semibold text-[#f0f1f2]">{{ props.preview.title }}</div>

    <div class="min-h-0 flex-1 overflow-auto rounded-lg border border-[#24262a] bg-[#151618] p-3">
      <template v-if="props.preview.kind === 'image' && props.preview.file">
        <img :src="imageUrl" :alt="props.preview.title" class="max-h-[280px] rounded-md" />
      </template>
      <template v-else-if="props.preview.kind === 'code'">
        <pre class="whitespace-pre-wrap break-words font-mono text-xs text-[#f0f1f2]">{{ props.preview.raw }}</pre>
      </template>
      <template v-else-if="props.preview.raw">
        <p class="whitespace-pre-wrap break-words text-sm leading-6 text-[#f0f1f2]">{{ props.preview.raw }}</p>
      </template>
      <template v-else>
        <p class="text-sm text-[#73747a]">文件已就绪，保存后由后端抽取并显示内容。</p>
      </template>
    </div>
  </div>
</template>
