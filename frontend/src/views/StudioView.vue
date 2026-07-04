<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Sparkles, FileText, Presentation, StickyNote, Send, Loader2, Plus, Filter } from 'lucide-vue-next'
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
const agentInput = ref('')

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
  if (!preview.value) return '描述想生成什么，左侧立刻出预览；点击「生成（异步）」会进入任务队列。'
  if (typeof preview.value.content === 'string') return preview.value.content
  try {
    return JSON.stringify(preview.value.content, null, 2)
  } catch {
    return ''
  }
})

function sendAgent() {
  if (!agentInput.value.trim()) return
  prompt.value = agentInput.value
  agentInput.value = ''
  submit(false)
}
</script>

<template>
  <section class="studio-view">
    <header class="topbar tight">
      <span>Studio</span>
      <span class="dot-menu">...</span>
      <span class="spacer"></span>
      <span class="tool-icons">
        <Filter :size="16" />
        <Plus :size="16" />
      </span>
    </header>

    <div class="favorite-page">
      <div class="favorite-main">
        <div class="favorite-content">
          <h1>Studio</h1>
          <p class="summary">
            从知识库里生成你想要的内容。模板只是入口 —— 表格、图示、视频脚本、PPTX 等会根据自然语言隐式触发。
          </p>

          <div class="surface" style="padding: 8px; margin-bottom: 22px;">
            <textarea
              v-model="prompt"
              class="field"
              style="min-height: 96px; resize: none; border: 0; background: transparent;"
              placeholder="根据最近保存的资料生成一份汇报大纲…"
            ></textarea>
            <div style="display: flex; justify-content: space-between; align-items: center; padding: 4px 8px 6px;">
              <div style="display: flex; align-items: center; gap: 8px; font-size: 12px; color: #73747a;">
                <Sparkles :size="12" />
                Type: <span class="chip chip-muted">{{ detectedType }}</span>
              </div>
              <div style="display: flex; gap: 8px;">
                <button class="btn" type="button" :disabled="sending || !prompt.trim()" @click="submit(false)">
                  <Loader2 v-if="sending" :size="14" class="animate-spin" />
                  Preview
                </button>
                <button class="btn btn-primary" type="button" :disabled="sending || !prompt.trim()" @click="submit(true)">
                  <Send :size="14" />
                  Generate
                </button>
              </div>
            </div>
          </div>

          <p v-if="error" style="border: 1px solid #5a2520; background: #2a1614; color: #f0b8ad; padding: 8px 12px; border-radius: 6px; font-size: 12px; margin-bottom: 16px;">
            {{ error }}
          </p>

          <div v-if="preview" class="surface" style="padding: 14px; margin-bottom: 22px;">
            <div style="font-size: 11px; color: var(--muted); margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.5px;">
              Preview · {{ preview.generation_type }}
            </div>
            <pre style="max-height: 320px; overflow: auto; white-space: pre-wrap; background: #151618; border: 1px solid var(--line); border-radius: 6px; padding: 12px; font-size: 12px; line-height: 1.5; color: var(--text); margin: 0;">{{ previewText }}</pre>
          </div>

          <h3 style="margin: 0 0 12px; color: var(--text); font-size: 14px; font-weight: 700;">Start from a template</h3>
          <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-bottom: 22px;">
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

          <h3 style="margin: 0 0 12px; color: var(--text); font-size: 14px; font-weight: 700;">Recent outputs</h3>
          <div v-if="recent.length" style="display: flex; flex-direction: column; gap: 6px;">
            <RouterLink
              v-for="t in recent"
              :key="t.id"
              :to="`/tasks?task=${t.id}`"
              class="card card-hover"
              style="padding: 10px 12px; display: flex; align-items: center; gap: 10px;"
            >
              <Sparkles :size="12" style="color: var(--blue);" />
              <span style="flex: 1; font-size: 13px; color: var(--text);">{{ t.type }}</span>
              <span style="font-size: 11px; color: var(--muted);">{{ t.status }}</span>
            </RouterLink>
          </div>
          <p v-else style="border: 1px dashed var(--line); padding: 14px; text-align: center; font-size: 12px; color: var(--muted);">
            还没有产出。选一个模板或直接描述想生成什么。
          </p>
        </div>
      </div>

      <aside class="favorite-side">
        <div class="side-meta">
          <div class="side-row">
            <span class="status-ring"></span>
            <span class="label">Status</span>
            <span>Draft</span>
          </div>
          <div class="side-row">
            <span class="label">Type</span>
            <span>{{ detectedType }}</span>
          </div>
          <div class="side-row">
            <span class="label">Model</span>
            <span class="mono">gpt-4o</span>
          </div>
          <div class="side-row">
            <span class="label">Owner</span>
            <span class="avatar dark" style="width: 22px; height: 22px;">U</span>
            <span>you</span>
          </div>
        </div>

        <div class="side-section">
          <h3>Sources</h3>
          <div style="display: flex; flex-direction: column; gap: 6px; color: var(--muted); font-size: 13px;">
            <div v-if="preview && preview.citations.length">
              <div v-for="(c, i) in preview.citations.slice(0, 5)" :key="i" style="display: flex; gap: 8px; padding: 6px 0; border-bottom: 1px solid var(--line-soft);">
                <span class="status-ring gray"></span>
                <span style="flex: 1; color: #c8cbd1; font-size: 12px;">{{ c.title }}</span>
              </div>
            </div>
            <div v-else style="font-size: 12px; color: var(--muted);">
              将基于最近的相关资料生成内容
            </div>
          </div>
        </div>

        <div class="side-section">
          <h3>Style</h3>
          <div style="display: flex; gap: 6px; flex-wrap: wrap;">
            <span class="pill square">Academic</span>
            <span class="pill square">Concise</span>
            <span class="pill square">Citations</span>
          </div>
        </div>

        <div class="agent-panel">
          <div class="agent-top">
            <span class="avatar dark" style="width: 18px; height: 18px; font-size: 9px;">NC</span>
            <span>NoteClaw</span>
            <span class="pill square">gpt-4o</span>
            <span class="spacer"></span>
            <span style="color: var(--muted); cursor: pointer;">−</span>
            <span style="color: var(--muted); cursor: pointer;">×</span>
          </div>
          <div class="agent-body">
            <p class="muted" style="margin: 0 0 10px;">基于当前模板与资料生成草稿…</p>
            <p style="margin: 0;">{{ preview ? '已生成预览。可以让我修改风格、加引用、扩展某段。' : '告诉我你想生成什么，我会基于资料库回答。' }}</p>
          </div>
          <div class="agent-input">
            <input
              v-model="agentInput"
              placeholder="Tell NoteClaw what to do next..."
              @keydown.enter="sendAgent"
            />
            <Send :size="14" style="color: var(--muted); cursor: pointer;" @click="sendAgent" />
          </div>
        </div>
      </aside>
    </div>
  </section>
</template>

<style scoped>
.studio-view {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}
</style>
