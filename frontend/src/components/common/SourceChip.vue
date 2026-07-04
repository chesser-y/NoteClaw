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
  <span class="inline-flex items-center gap-2 rounded-lg border border-[#e5e7eb] bg-white px-2.5 py-1.5 text-xs text-[#374151]">
    <component :is="iconFor(normalize(props.type))" :size="13" class="text-[#6b7280]" />
    <span class="max-w-[220px] truncate font-medium text-[#111827]">{{ props.title }}</span>
    <span v-if="props.score != null" class="text-[#9ca3af]">· {{ Math.round((props.score ?? 0) * 100) }}%</span>
  </span>
</template>
