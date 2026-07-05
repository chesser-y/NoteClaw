<script setup lang="ts">
import { computed } from 'vue'
import { marked } from 'marked'
import markedKatex from 'marked-katex-extension'
import 'katex/dist/katex.min.css'

const props = defineProps<{
  content: string
}>()

const katexExtension = markedKatex({ throwOnError: false })
marked.use(katexExtension)

const html = computed(() => {
  const src = props.content || ''
  if (!src.trim()) return ''
  try {
    return marked.parse(src, { async: false }) as string
  } catch {
    return ''
  }
})
</script>

<template>
  <div class="markdown-body" v-html="html"></div>
</template>
