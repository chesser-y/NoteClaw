<script setup lang="ts">
import { computed } from 'vue'
import { FileText, Image as ImageIcon, Code2, Table, Globe, Github, Star } from 'lucide-vue-next'
import type { ContentType } from '../../api/types'
import AskTrigger from '../ask/AskTrigger.vue'

const props = defineProps<{
  title: string
  contentType: ContentType
  summary: string
  tags: string[]
  source?: string
  sourceUrl?: string
  createdAt?: string
  score?: number
  noteId?: string
}>()

const iconFor = computed(() => {
  switch (props.contentType) {
    case 'image':
      return ImageIcon
    case 'code':
      return Code2
    case 'table':
      return Table
    case 'webpage':
      return Globe
    case 'repository':
      return Github
    case 'document':
    case 'text':
    default:
      return FileText
  }
})

const meta = computed(() => {
  const parts: string[] = []
  parts.push(props.contentType)
  if (props.source) parts.push(props.source)
  if (props.createdAt) {
    const date = new Date(props.createdAt)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const days = Math.floor(diffMs / (1000 * 60 * 60 * 24))
    if (days <= 0) parts.push('saved today')
    else if (days === 1) parts.push('saved yesterday')
    else if (days < 7) parts.push(`saved ${days} days ago`)
    else parts.push(`saved ${date.toLocaleDateString()}`)
  }
  if (props.score != null) parts.push(`score ${(props.score * 100).toFixed(0)}%`)
  return parts.join(' · ')
})
</script>

<template>
  <article class="card card-hover group relative flex flex-col gap-3 py-4">
    <header class="flex items-start gap-3">
      <div class="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-[rgba(98, 107, 230, 0.16)] text-[#626be6]">
        <component :is="iconFor" :size="16" />
      </div>
      <div class="min-w-0 flex-1">
        <h3 class="truncate text-[15px] font-semibold text-[#f0f1f2]">{{ title }}</h3>
        <div class="mt-0.5 truncate text-xs text-[#73747a]">{{ meta }}</div>
      </div>
      <button
        class="opacity-0 transition group-hover:opacity-100"
        type="button"
        aria-label="Star"
        @click.stop
      >
        <Star :size="14" class="text-[#73747a] hover:text-[#ff9f35]" />
      </button>
    </header>

    <p class="line-clamp-2 text-sm leading-6 text-[#c8c9cd]">
      {{ summary || '等待摘要生成…' }}
    </p>

    <div v-if="tags.length" class="flex flex-wrap gap-1.5">
      <span v-for="tag in tags.slice(0, 5)" :key="tag" class="chip">{{ tag }}</span>
    </div>

    <div class="mt-auto flex items-center justify-end gap-1 pt-1 opacity-0 transition group-hover:opacity-100">
      <AskTrigger v-if="noteId" :note-ids="[noteId]" :title="title" label="问这篇" />
      <AskTrigger v-else label="问这篇" />
    </div>
  </article>
</template>
