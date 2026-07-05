<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { marked } from 'marked'
import markedKatex from 'marked-katex-extension'
import mermaid from 'mermaid'
import 'katex/dist/katex.min.css'

const props = defineProps<{
  content: string
}>()

const katexExtension = markedKatex({ throwOnError: false })
marked.use(katexExtension)

let mermaidConfigured = false
function ensureMermaid() {
  if (mermaidConfigured) return
  mermaid.initialize({
    startOnLoad: false,
    theme: 'default',
    securityLevel: 'loose',
    fontFamily: 'inherit',
  })
  mermaidConfigured = true
}

const renderer = new marked.Renderer()
const origCode = renderer.code.bind(renderer)
renderer.code = (token: any) => {
  if (token && token.lang === 'mermaid') {
    const text = String(token.text || '').replace(/"/g, '&quot;')
    return `<div class="mermaid" data-mermaid="1">${text}</div>`
  }
  return origCode(token)
}
marked.use({ renderer })

const container = ref<HTMLElement | null>(null)

const html = computed(() => {
  const src = props.content || ''
  if (!src.trim()) return ''
  try {
    return marked.parse(src, { async: false }) as string
  } catch {
    return ''
  }
})

async function runMermaid() {
  await nextTick()
  if (!container.value) return
  const nodes = container.value.querySelectorAll<HTMLElement>('.mermaid')
  if (!nodes.length) return
  ensureMermaid()
  nodes.forEach((n) => {
    if (n.getAttribute('data-processed') === '1') return
    n.removeAttribute('data-processed')
    try {
      n.innerHTML = decodeHtmlEntities(n.textContent || '')
    } catch {
      /* keep raw */
    }
  })
  try {
    await mermaid.run({ nodes: Array.from(nodes) })
    nodes.forEach((n) => n.setAttribute('data-processed', '1'))
  } catch (e) {
    /* single diagram failure should not nuke others */
    console.warn('mermaid render failed', e)
  }
}

function decodeHtmlEntities(s: string): string {
  const txt = document.createElement('textarea')
  txt.innerHTML = s
  return txt.value
}

onMounted(runMermaid)
watch(html, runMermaid)
</script>

<template>
  <div ref="container" class="markdown-body" v-html="html"></div>
</template>
