<script setup lang="ts">
import { FileText, Image as ImageIcon, Code2, Table, Globe, Github } from 'lucide-vue-next'
import type { ContentType } from '../../api/types'

const props = defineProps<{
  type: ContentType | string
  title: string
  score?: number | null
}>()

function normalize(type: string): ContentType {
  return type.toLowerCase() as ContentType
}

const iconFor = (type: ContentType) => {
  switch (type) {
    case 'image':
      return ImageIcon
    case 'code':
    case 'repository':
      return type === 'repository' ? Github : Code2
    case 'table':
      return Table
    case 'webpage':
      return Globe
    case 'document':
    case 'text':
    default:
      return FileText
  }
}
</script>

<template>
  <span class="inline-flex items-center gap-2 rounded-lg border border-[#24262a] bg-[#1b1c1e] px-2.5 py-1.5 text-xs text-[#c8c9cd]">
    <component :is="iconFor(normalize(props.type))" :size="13" class="text-[#929399]" />
    <span class="max-w-[220px] truncate font-medium text-[#f0f1f2]">{{ props.title }}</span>
    <span v-if="props.score != null" class="text-[#73747a]">· {{ Math.round((props.score ?? 0) * 100) }}%</span>
  </span>
</template>
