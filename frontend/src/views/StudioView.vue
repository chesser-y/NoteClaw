<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Sparkles, FileText, Presentation, StickyNote, Send, Loader2 } from 'lucide-vue-next'
import { previewGeneration, createGenerationTask } from '../api/generate'
import { listTasks } from '../api/tasks'
import type { GenerationType, TaskRead, GenerationPreviewResponse } from '../api/types'
import TemplateCard from '../components/studio/TemplateCard.vue'

const route = useRoute()
const router = useRouter()

type TemplateId = 'brief' | 'notes' | 'slides'

const templates: { id: TemplateId; label: string; sub: string; icon: typeof FileText; type: GenerationType; promptHint: string }[] = [
  { id: 'brief', label: 'Brief', sub: '简报 / 汇报大纲', icon: FileText, type: 'report_draft', promptHint: '根据最近保存的资料生成一份汇报大纲，重点列出关键发现与建议。' },
  { id: 'notes', label: 'Notes', sub: '学习笔记', icon: StickyNote, type: 'learning_note', promptHint: '把最近保存的资料整理成学习笔记，按主题分段并附引用。' },
  { id: 'slides', label: 'Slides', sub: 'PPT 大纲', icon: Presentation, type: 'ppt_outline', promptHint: '根据最近保存的资料生成一份 PPT 大纲，10 页左右，每页要点不超过 3 条。' },
]

const prompt = ref((route.query.prompt as string) || '')
const activeTemplate = ref<TemplateId | null>(null)
const sending = ref(false)
const error = ref('')
const preview = ref<GenerationPreviewResponse | null>(null)
const recent = ref<TaskRead[]>([])

const detectedType = computed<GenerationType>(() => {
  const p = prompt.value.toLowerCase()
  if (/(表格|table)/.test(p)) return 'table'
  if (/(图示|diagram|流程)/.test(p)) return 'diagram'
  if (/(视频脚本|video script)/.test(p)) return 'video_script'
  if (/(ppt|幻灯片|slides)/.test(p)) return 'ppt_outline'
  if (/(简报|汇报|brief|报告)/.test(p)) return 'report_draft'
  if (/(笔记|notes)/.test(p)) return 'learning_note'
  return templates.find((t) => t.id === activeTemplate.value)?.type ?? 'learning_note'
})

async function loadRecent() {
  try {
    const res = await listTasks({ limit: 6 })
    recent.value = res.items.filter((t) => /generate|ppt|slide/i.test(t.type))
  } catch (e) {
    console.error(e)
  }
}

function selectTemplate(id: TemplateId) {
  activeTemplate.value = id
  const tpl = templates.find((t) => t.id === id)
  if (tpl && !prompt.value.trim()) prompt.value = tpl.promptHint
}

async function submit(asyncMode: boolean) {
  if (!prompt.value.trim() || sending.value) return
  sending.value = true
  error.value = ''
  preview.value = null
  try {
    const genType = detectedType.value
    if (asyncMode) {
      const res = await createGenerationTask({
        generation_type: genType,
        prompt: prompt.value,
      })
      await router.push(`/tasks?task=${res.task_id}`)
    } else {
      preview.value = await previewGeneration({
        generation_type: genType,
        prompt: prompt.value,
      })
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    sending.value = false
  }
}

watch(
  () => route.query.template,
  (t) => {
    if (t === 'brief' || t === 'notes' || t === 'slides') selectTemplate(t)
  },
)

onMounted(() => {
  loadRecent()
  const t = route.query.template as string | undefined
  if (t === 'brief' || t === 'notes' || t === 'slides') selectTemplate(t)
})

const previewText = computed(() => {
  if (!preview.value) return ''
  if (typeof preview.value.content === 'string') return preview.value.content
  try {
    return JSON.stringify(preview.value.content, null, 2)
  } catch {
    return ''
  }
})
</script>

<template>
  <section class="content-wrap">
    <header class="mb-6">
      <h1 class="section-title">Studio</h1>
      <p class="muted mt-1 text-sm">What do you want to make from your knowledge?</p>
    </header>

    <div class="surface mb-6 p-2">
      <textarea
        v-model="prompt"
        class="field textarea min-h-[120px] resize-none border-0 bg-transparent shadow-none focus:shadow-none"
        placeholder="根据最近保存的资料生成一份汇报大纲…"
      ></textarea>
      <div class="flex items-center justify-between gap-2 px-2 pb-2 pt-1">
        <div class="flex items-center gap-2 text-[11px] text-[#73747a]">
          <Sparkles :size="12" />
          将生成：<span class="chip chip-muted">{{ detectedType }}</span>
        </div>
        <div class="flex items-center gap-2">
          <button class="btn h-9" type="button" :disabled="sending || !prompt.trim()" @click="submit(false)">
            <Loader2 v-if="sending" :size="14" class="animate-spin" />
            预览
          </button>
          <button class="btn btn-primary h-9" type="button" :disabled="sending || !prompt.trim()" @click="submit(true)">
            <Send :size="14" />
            生成（异步）
          </button>
        </div>
      </div>
    </div>

    <p v-if="error" class="mb-5 rounded-lg border border-[#5a2520] bg-[#2a1614] px-3 py-2 text-xs text-[#f0b8ad]">
      {{ error }}
    </p>

    <div v-if="preview" class="surface mb-7 p-4">
      <div class="mb-2 text-xs font-semibold uppercase tracking-wide text-[#929399]">Preview · {{ preview.generation_type }}</div>
      <pre class="max-h-[320px] overflow-auto whitespace-pre-wrap rounded-lg border border-[#24262a] bg-[#151618] p-3 text-xs leading-6 text-[#f0f1f2]">{{ previewText }}</pre>
    </div>

    <div class="mb-7">
      <div class="mb-3 text-xs font-semibold uppercase tracking-wide text-[#929399]">Start from</div>
      <div class="grid gap-3 sm:grid-cols-3">
        <TemplateCard
          v-for="tpl in templates"
          :key="tpl.id"
          :label="tpl.label"
          :sub="tpl.sub"
          :icon="tpl.icon"
          :active="activeTemplate === tpl.id"
          @click="selectTemplate(tpl.id)"
        />
      </div>
      <p class="mt-3 text-xs text-[#73747a]">
        其他能力（表格 / 图示 / 视频脚本 / PPTX）会根据自然语言隐式触发。
      </p>
    </div>

    <div>
      <div class="mb-3 flex items-center justify-between">
        <div class="text-xs font-semibold uppercase tracking-wide text-[#929399]">Recent outputs</div>
        <RouterLink to="/tasks" class="text-xs text-[#929399] hover:text-[#626be6]">查看全部任务 →</RouterLink>
      </div>
      <div v-if="recent.length" class="space-y-2">
        <RouterLink
          v-for="t in recent"
          :key="t.id"
          :to="`/tasks?task=${t.id}`"
          class="card card-hover flex items-center gap-3 py-3"
        >
          <Sparkles :size="14" class="text-[#626be6]" />
          <span class="flex-1 truncate text-sm text-[#f0f1f2]">{{ t.type }}</span>
          <span class="text-[11px] text-[#73747a]">{{ t.status }}</span>
        </RouterLink>
      </div>
      <p v-else class="rounded-xl border border-dashed border-[#24262a] bg-[#101112] px-4 py-6 text-center text-xs text-[#73747a]">
        还没有产出。选一个模板或直接描述想生成什么。
      </p>
    </div>
  </section>
</template>
