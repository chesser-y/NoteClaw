<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { Sparkles, FileText, Presentation, StickyNote, Send, Loader2, ChevronDown, X, Check, Eye, Download, ExternalLink } from "lucide-vue-next"
import { marked } from 'marked'
import { previewGeneration, createGenerationTask } from '../api/generate'
import { listTasks } from '../api/tasks'
import { listKnowledge, getKnowledgeFacets, type Facets } from '../api/knowledge'
import { API_BASE } from '../api/http'
import type { ContentType, GenerationType, NoteListItem, TaskRead, GenerationPreviewResponse } from '../api/types'
import TemplateCard from '../components/studio/TemplateCard.vue'
import NotePreview from '../components/preview/NotePreview.vue'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()

type TemplateId = 'brief' | 'notes' | 'slides'

const templates = computed<{ id: TemplateId; label: string; sub: string; icon: typeof FileText; type: GenerationType; promptHint: string }[]>(() => [
  { id: 'brief', label: t('studio.tpl-brief-label'), sub: t('studio.tpl-brief-sub'), icon: FileText, type: 'report_draft', promptHint: t('studio.tpl-brief-hint') },
  { id: 'notes', label: t('studio.tpl-notes-label'), sub: t('studio.tpl-notes-sub'), icon: StickyNote, type: 'learning_note', promptHint: t('studio.tpl-notes-hint') },
  { id: 'slides', label: t('studio.tpl-slides-label'), sub: t('studio.tpl-slides-sub'), icon: Presentation, type: 'ppt_outline', promptHint: t('studio.tpl-slides-hint') },
])

const prompt = ref((route.query.prompt as string) || '')
const activeTemplate = ref<TemplateId | null>(null)
const sending = ref(false)
const error = ref('')
const preview = ref<GenerationPreviewResponse | null>(null)
const recentTasks = ref<TaskRead[]>([])
const recentNotes = ref<NoteListItem[]>([])
const agentInput = ref('')

// Scope picker state
const scopeTags = ref<string[]>([])
const scopeTypes = ref<ContentType[]>([])
const scopeOpen = ref(false)
const scopeRoot = ref<HTMLElement | null>(null)
const facets = ref<Facets>({ tags: [], sources: [], categories: [], content_types: [] })
const tagQuery = ref('')

const contentTypeOptions: { value: ContentType; label: string }[] = [
  { value: 'text', label: 'Text' },
  { value: 'code', label: 'Code' },
  { value: 'image', label: 'Image' },
  { value: 'table', label: 'Table' },
  { value: 'document', label: 'PDF' },
  { value: 'webpage', label: 'Web' },
]

async function loadFacets() {
  try {
    facets.value = await getKnowledgeFacets()
  } catch {
    facets.value = { tags: [], sources: [], categories: [], content_types: [] }
  }
}

function toggleScopeOpen() {
  if (!scopeOpen.value) loadFacets()
  scopeOpen.value = !scopeOpen.value
}

function closeScope() {
  scopeOpen.value = false
}

function onClickOutside(e: MouseEvent) {
  if (!scopeOpen.value) return
  if (scopeRoot.value && !scopeRoot.value.contains(e.target as Node)) closeScope()
}

function toggleTag(tag: string) {
  const set = new Set(scopeTags.value)
  if (set.has(tag)) set.delete(tag)
  else set.add(tag)
  scopeTags.value = [...set]
}

function toggleType(t: ContentType) {
  const set = new Set(scopeTypes.value)
  if (set.has(t)) set.delete(t)
  else set.add(t)
  scopeTypes.value = [...set]
}

function clearScope() {
  scopeTags.value = []
  scopeTypes.value = []
}

const filteredTags = computed(() => {
  const q = tagQuery.value.trim().toLowerCase()
  const all = facets.value.tags ?? []
  if (!q) return all.slice(0, 30)
  return all.filter(([t]) => t.toLowerCase().includes(q)).slice(0, 30)
})

const scopeActiveCount = computed(() => scopeTags.value.length + scopeTypes.value.length)

const detectedType = computed<GenerationType>(() => {
  const p = prompt.value.toLowerCase()
  if (/(表格|table)/.test(p)) return 'table'
  if (/(图示|diagram|流程)/.test(p)) return 'diagram'
  if (/(视频脚本|video script)/.test(p)) return 'video_script'
  if (/(ppt|幻灯片|slides)/.test(p)) return 'ppt_outline'
  if (/(简报|汇报|brief|报告)/.test(p)) return 'report_draft'
  if (/(笔记|notes)/.test(p)) return 'learning_note'
  return templates.value.find((tt) => tt.id === activeTemplate.value)?.type ?? 'learning_note'
})

async function loadRecent() {
  try {
    const [tasksRes, notesRes] = await Promise.all([
      listTasks({ limit: 6 }).catch(() => ({ items: [] as TaskRead[], total: 0, limit: 6, offset: 0 })),
      listKnowledge({ source: 'generation', limit: 6 }).catch(() => ({ items: [] as NoteListItem[], total: 0, limit: 6, offset: 0 })),
    ])
    recentTasks.value = tasksRes.items.filter((tt: TaskRead) => /generate|ppt|slide/i.test(tt.type))
    recentNotes.value = notesRes.items
  } catch (e) {
    console.error(e)
  }
}

function selectTemplate(id: TemplateId) {
  activeTemplate.value = id
  const tpl = templates.value.find((tt) => tt.id === id)
  if (tpl) prompt.value = tpl.promptHint
}

function buildScope() {
  if (!scopeTags.value.length && !scopeTypes.value.length) return undefined
  return {
    tags: scopeTags.value.length ? scopeTags.value : undefined,
    content_types: scopeTypes.value.length ? scopeTypes.value : undefined,
  }
}

async function submit(asyncMode: boolean) {
  if (!prompt.value.trim() || sending.value) return
  sending.value = true
  error.value = ''
  preview.value = null
  try {
    const genType = detectedType.value
    const scope = buildScope()
    if (asyncMode) {
      const res = await createGenerationTask({
        generation_type: genType,
        prompt: prompt.value,
        scope,
      })
      await router.push(`/tasks?task=${res.task_id}`)
    } else {
      preview.value = await previewGeneration({
        generation_type: genType,
        prompt: prompt.value,
        scope,
      })
      // Refresh recent so the persisted note shows up
      await loadRecent()
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
  document.addEventListener('mousedown', onClickOutside)
})

import { onUnmounted } from 'vue'
onUnmounted(() => document.removeEventListener('mousedown', onClickOutside))

const previewMarkdown = computed(() => {
  if (!preview.value) return ''
  const c = preview.value.content
  if (typeof c === 'string') return c
  const gtype = preview.value.generation_type
  const obj = (c || {}) as Record<string, any>
  if (gtype === 'ppt_outline' || gtype === 'pptx') {
    const outline = obj.outline || c
    const title = String(outline?.title || 'Untitled deck').trim()
    const slides = Array.isArray(outline?.slides) ? outline.slides : []
    const lines = [`# ${title}`, '']
    slides.forEach((s: any, i: number) => {
      lines.push(`## ${i + 1}. ${s?.title || 'Slide ' + (i + 1)}`)
      for (const key of ['bullets', 'points', 'subtitle']) {
        const b = s?.[key]
        if (!b) continue
        const arr = Array.isArray(b) ? b : [b]
        for (const x of arr) lines.push(`- ${x}`)
      }
      lines.push('')
    })
    return lines.join('\n')
  }
  if (gtype === 'table' || gtype === 'video_script') {
    return String(obj.markdown || '')
  }
  if (gtype === 'image') {
    const prompt = String(obj.prompt || '')
    const url = obj.url ? String(obj.url) : ''
    const lines = ['# Generated image', '', prompt]
    if (url) lines.push('', `![generated image](${url})`)
    return lines.join('\n')
  }
  // fallback: pretty JSON inside a fenced block
  try {
    return '```json\n' + JSON.stringify(c, null, 2) + '\n```'
  } catch {
    return ''
  }
})

const previewHtml = computed(() => {
  const md = previewMarkdown.value
  if (!md) return ''
  try {
    return marked.parse(md) as string
  } catch {
    return ''
  }
})

const downloadUrl = computed(() => {
  if (!preview.value?.note_id) return ''
  return `${API_BASE}/knowledge/${preview.value.note_id}/file`
})

const libraryUrl = computed(() => {
  if (!preview.value?.note_id) return ''
  return `/library?id=${preview.value.note_id}`
})

const downloadLabel = computed(() => {
  const ext = preview.value?.document_extension
  return ext ? `${t('action.download')} .${ext}` : t('action.download')
})

const htmlSlides = computed<string[]>(() => {
  if (!preview.value) return []
  const fromContent = (preview.value.content as any)?.html_slides
  if (Array.isArray(fromContent)) return fromContent as string[]
  return preview.value.html_slides ?? []
})

type RecentItem =
  | { kind: 'task'; id: string; title: string; sub: string; status: string; ts: string; raw: TaskRead }
  | { kind: 'note'; id: string; title: string; sub: string; status: string; ts: string; raw: NoteListItem }

const recentItems = computed<RecentItem[]>(() => {
  const tasks: RecentItem[] = recentTasks.value.map((t) => ({
    kind: 'task' as const,
    id: t.id,
    title: t.type,
    sub: t.message || t.status,
    status: t.status,
    ts: t.updated_at || t.created_at,
    raw: t,
  }))
  const notes: RecentItem[] = recentNotes.value.map((n) => ({
    kind: 'note' as const,
    id: n.id,
    title: n.title,
    sub: n.summary || n.content_type,
    status: n.status,
    ts: n.created_at,
    raw: n,
  }))
  return [...tasks, ...notes].sort((a, b) => new Date(b.ts).getTime() - new Date(a.ts).getTime()).slice(0, 8)
})

const previewNoteId = ref<string | null>(null)
function openNotePreview(id: string) {
  previewNoteId.value = id
}
function closeNotePreview() {
  previewNoteId.value = null
}

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
      <span>{{ t('view.studio') }}</span>
      <span class="spacer"></span>
    </header>

    <div class="favorite-page">
      <div class="favorite-main">
        <div class="favorite-content">
          <h1>{{ t('view.studio') }}</h1>
          <p class="summary">
            {{ t('studio.summary') }}
          </p>

          <div class="surface" style="padding: 8px; margin-bottom: 12px;">
            <textarea
              v-model="prompt"
              class="field"
              style="min-height: 96px; resize: none; border: 0; background: transparent;"
              :placeholder="t('studio.prompt-placeholder')"
            ></textarea>
            <div class="scope-bar">
              <div class="scope-chips">
                <span v-for="tag in scopeTags" :key="'tag-' + tag" class="scope-chip">
                  #{{ tag }}
                  <button class="chip-x" type="button" @click="toggleTag(tag)"><X :size="10" /></button>
                </span>
                <span v-for="ct in scopeTypes" :key="'ct-' + ct" class="scope-chip type-chip">
                  {{ ct }}
                  <button class="chip-x" type="button" @click="toggleType(ct)"><X :size="10" /></button>
                </span>
                <button
                  v-if="scopeActiveCount"
                  class="scope-clear"
                  type="button"
                  @click="clearScope"
                >{{ t('studio.scope-clear') }}</button>
              </div>
              <div ref="scopeRoot" class="scope-host">
                <button
                  class="scope-trigger"
                  type="button"
                  :class="{ active: scopeActiveCount > 0 }"
                  @click="toggleScopeOpen"
                >
                  <Sparkles :size="12" />
                  {{ t('studio.scope-button') }}
                  <span v-if="scopeActiveCount" class="scope-badge">{{ scopeActiveCount }}</span>
                  <ChevronDown :size="12" />
                </button>
                <div v-if="scopeOpen" class="scope-popover">
                  <header class="pop-head">
                    <span>{{ t('studio.scope-pop-title') }}</span>
                    <button class="icon-button" @click="closeScope"><X :size="13" /></button>
                  </header>

                  <section class="pop-section">
                    <div class="section-title">{{ t('studio.scope-types') }}</div>
                    <div class="type-grid">
                      <button
                        v-for="opt in contentTypeOptions"
                        :key="opt.value"
                        type="button"
                        class="type-pill"
                        :class="{ active: scopeTypes.includes(opt.value) }"
                        @click="toggleType(opt.value)"
                      >
                        <Check v-if="scopeTypes.includes(opt.value)" :size="11" />
                        <span v-else class="check-spacer"></span>
                        {{ opt.label }}
                      </button>
                    </div>
                  </section>

                  <section class="pop-section">
                    <div class="section-title">{{ t('studio.scope-tags') }}</div>
                    <input
                      v-model="tagQuery"
                      class="field tag-search"
                      :placeholder="t('studio.scope-tag-search')"
                    />
                    <div class="tag-list">
                      <button
                        v-for="[tag, count] in filteredTags"
                        :key="tag"
                        type="button"
                        class="tag-row"
                        :class="{ active: scopeTags.includes(tag) }"
                        @click="toggleTag(tag)"
                      >
                        <Check v-if="scopeTags.includes(tag)" :size="11" class="check" />
                        <span v-else class="check-spacer"></span>
                        <span class="tag-name">{{ tag }}</span>
                        <span class="tag-count">{{ count }}</span>
                      </button>
                      <div v-if="!filteredTags.length" class="muted small">{{ t('studio.scope-no-tags') }}</div>
                    </div>
                  </section>

                  <footer class="pop-footer">
                    <button class="btn btn-ghost" type="button" @click="clearScope">{{ t('studio.scope-clear') }}</button>
                    <button class="btn btn-primary" type="button" @click="closeScope">{{ t('studio.scope-done') }}</button>
                  </footer>
                </div>
              </div>
            </div>
            <div style="display: flex; justify-content: space-between; align-items: center; padding: 4px 8px 6px;">
              <div style="display: flex; align-items: center; gap: 8px; font-size: 12px; color: #73747a;">
                <Sparkles :size="12" />
                {{ t('studio.type-label') }}: <span class="chip chip-muted">{{ detectedType }}</span>
              </div>
              <div style="display: flex; gap: 8px;">
                <button class="btn" type="button" :disabled="sending || !prompt.trim()" @click="submit(false)">
                  <Loader2 v-if="sending" :size="14" class="animate-spin" />
                  {{ t('studio.preview') }}
                </button>
                <button class="btn btn-primary" type="button" :disabled="sending || !prompt.trim()" @click="submit(true)">
                  <Send :size="14" />
                  {{ t('studio.generate') }}
                </button>
              </div>
            </div>
          </div>

          <p v-if="error" style="border: 1px solid #5a2520; background: #2a1614; color: #f0b8ad; padding: 8px 12px; border-radius: 6px; font-size: 12px; margin-bottom: 16px;">
            {{ error }}
          </p>

          <div v-if="preview" class="surface" style="padding: 14px; margin-bottom: 22px;">
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 10px;">
              <span style="font-size: 11px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.5px;">
                {{ t('studio.preview') }} · {{ preview.generation_type }}
              </span>
              <span class="spacer" style="flex: 1;"></span>
              <RouterLink
                v-if="preview.note_id"
                :to="libraryUrl"
                class="btn btn-ghost btn-mini"
                :title="t('action.open-in-library')"
              >
                <ExternalLink :size="12" />
                {{ t('action.open-in-library') }}
              </RouterLink>
              <a
                v-if="downloadUrl"
                :href="downloadUrl"
                class="btn btn-primary btn-mini"
                :download="''"
                :title="t('action.download')"
              >
                <Download :size="12" />
                {{ downloadLabel }}
              </a>
            </div>
            <div v-if="htmlSlides.length" class="slide-strip">
              <div
                v-for="(html, i) in htmlSlides"
                :key="i"
                class="slide-thumb"
                :title="`Slide ${i + 1}`"
              >
                <iframe :srcdoc="html" sandbox=""></iframe>
                <span class="slide-num">{{ i + 1 }}</span>
              </div>
            </div>
            <div v-else class="preview-md" v-html="previewHtml"></div>
          </div>

          <h3 style="margin: 0 0 12px; color: var(--text); font-size: 14px; font-weight: 700;">{{ t('studio.start-from-template') }}</h3>
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

          <h3 style="margin: 0 0 12px; color: var(--text); font-size: 14px; font-weight: 700;">{{ t('studio.recent-outputs') }}</h3>
          <div v-if="recentItems.length" style="display: flex; flex-direction: column; gap: 6px;">
            <component
              :is="item.kind === 'task' ? 'RouterLink' : 'div'"
              v-for="item in recentItems"
              :key="item.kind + '-' + item.id"
              v-bind="item.kind === 'task' ? { to: `/tasks?task=${item.id}` } : {}"
              class="card card-hover recent-row"
              :class="{ clickable: item.kind === 'note' }"
              @click="item.kind === 'note' ? openNotePreview(item.id) : null"
            >
              <Sparkles v-if="item.kind === 'task'" :size="12" style="color: var(--blue);" />
              <FileText v-else :size="12" style="color: var(--green);" />
              <span class="recent-title">{{ item.title }}</span>
              <span class="recent-sub">{{ item.sub }}</span>
              <span class="recent-spacer"></span>
              <Eye v-if="item.kind === 'note'" :size="11" class="muted" />
              <span class="recent-status">{{ item.status }}</span>
            </component>
          </div>
          <p v-else style="border: 1px dashed var(--line); padding: 14px; text-align: center; font-size: 12px; color: var(--muted);">
            {{ t('studio.no-outputs') }}
          </p>
        </div>
      </div>

      <aside class="favorite-side">
        <div class="side-meta">
          <div class="side-row">
            <span class="status-ring"></span>
            <span class="label">{{ t('studio.side-status') }}</span>
            <span>{{ t('studio.side-status-draft') }}</span>
          </div>
          <div class="side-row">
            <span class="label">{{ t('studio.side-type') }}</span>
            <span>{{ detectedType }}</span>
          </div>
          <div class="side-row">
            <span class="label">{{ t('studio.side-scope') }}</span>
            <span>{{ scopeActiveCount ? t('studio.side-scope-n', { n: scopeActiveCount }) : t('studio.side-scope-all') }}</span>
          </div>
          <div class="side-row">
            <span class="label">{{ t('studio.side-model') }}</span>
            <span class="mono">gpt-4o</span>
          </div>
          <div class="side-row">
            <span class="label">{{ t('studio.side-owner') }}</span>
            <span class="avatar dark" style="width: 22px; height: 22px;">U</span>
            <span>{{ t('studio.side-owner-you') }}</span>
          </div>
        </div>

        <div class="side-section">
          <h3>{{ t('studio.side-sources') }}</h3>
          <div style="display: flex; flex-direction: column; gap: 6px; color: var(--muted); font-size: 13px;">
            <div v-if="preview && preview.citations.length">
              <div v-for="(c, i) in preview.citations.slice(0, 5)" :key="i" style="display: flex; gap: 8px; padding: 6px 0; border-bottom: 1px solid var(--line-soft);">
                <span class="status-ring gray"></span>
                <span style="flex: 1; color: #c8cbd1; font-size: 12px;">{{ c.title }}</span>
              </div>
            </div>
            <div v-else style="font-size: 12px; color: var(--muted);">
              {{ scopeActiveCount ? t('studio.side-sources-scoped') : t('studio.side-sources-hint') }}
            </div>
          </div>
        </div>

        <div class="side-section">
          <h3>{{ t('studio.side-style') }}</h3>
          <div style="display: flex; gap: 6px; flex-wrap: wrap;">
            <span class="pill square">{{ t('studio.style-academic') }}</span>
            <span class="pill square">{{ t('studio.style-concise') }}</span>
            <span class="pill square">{{ t('studio.style-citations') }}</span>
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
            <p class="muted" style="margin: 0 0 10px;">{{ t('studio.agent-sub') }}</p>
            <p style="margin: 0;">{{ preview ? t('studio.agent-has-preview') : t('studio.agent-empty') }}</p>
          </div>
          <div class="agent-input">
            <input
              v-model="agentInput"
              :placeholder="t('studio.agent-input-placeholder')"
              @keydown.enter="sendAgent"
            />
            <Send :size="14" style="color: var(--muted); cursor: pointer;" @click="sendAgent" />
          </div>
        </div>
      </aside>
    </div>

    <NotePreview :note-id="previewNoteId" @close="closeNotePreview" />
  </section>
</template>

<style scoped>
.studio-view {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.scope-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px 8px;
  border-top: 1px dashed var(--line);
  margin-top: 6px;
  flex-wrap: wrap;
}

.scope-chips {
  display: flex;
  align-items: center;
  gap: 4px;
  flex: 1;
  flex-wrap: wrap;
  min-height: 26px;
}

.scope-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  padding: 2px 4px 2px 8px;
  border-radius: 999px;
  background: rgba(98, 107, 230, 0.18);
  border: 1px solid rgba(98, 107, 230, 0.4);
  color: var(--text);
}

.scope-chip.type-chip {
  background: rgba(74, 174, 255, 0.16);
  border-color: rgba(74, 174, 255, 0.4);
  text-transform: capitalize;
}

.chip-x {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 14px;
  height: 14px;
  background: transparent;
  border: 0;
  color: var(--muted);
  cursor: pointer;
  border-radius: 50%;
  padding: 0;
}
.chip-x:hover {
  background: rgba(255, 255, 255, 0.1);
  color: var(--text);
}

.scope-clear {
  background: transparent;
  border: 0;
  color: var(--muted);
  font-size: 11px;
  cursor: pointer;
  text-decoration: underline;
  text-underline-offset: 2px;
}

.scope-host {
  position: relative;
  display: inline-flex;
}

.scope-trigger {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 28px;
  padding: 0 10px;
  background: var(--panel-2);
  border: 1px solid var(--line);
  border-radius: 6px;
  color: var(--text);
  font-size: 12px;
  cursor: pointer;
}
.scope-trigger:hover {
  background: var(--panel-3);
}
.scope-trigger.active {
  border-color: var(--blue);
}

.scope-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 16px;
  height: 16px;
  padding: 0 4px;
  border-radius: 8px;
  background: var(--blue);
  color: white;
  font-size: 10px;
  font-weight: 600;
}

.scope-popover {
  position: absolute;
  top: calc(100% + 6px);
  right: 0;
  width: 320px;
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: var(--r-md, 8px);
  box-shadow: 0 12px 36px rgba(0, 0, 0, 0.4);
  z-index: 50;
  display: flex;
  flex-direction: column;
  max-height: 520px;
}

.pop-head {
  display: flex;
  align-items: center;
  padding: 10px 12px;
  border-bottom: 1px solid var(--line);
  font-weight: 600;
  font-size: 13px;
}
.pop-head button {
  margin-left: auto;
}

.pop-section {
  padding: 10px 12px;
  border-bottom: 1px solid var(--line);
}
.section-title {
  font-size: 10px;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.6px;
  margin-bottom: 6px;
}

.type-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
.type-pill {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  background: var(--panel-2);
  border: 1px solid var(--line);
  border-radius: 5px;
  font-size: 11px;
  color: var(--text);
  cursor: pointer;
}
.type-pill:hover {
  background: var(--panel-3);
}
.type-pill.active {
  background: rgba(74, 174, 255, 0.18);
  border-color: rgba(74, 174, 255, 0.5);
}

.tag-search {
  width: 100%;
  height: 28px;
  background: var(--panel-2);
  border: 1px solid var(--line);
  border-radius: 5px;
  padding: 0 8px;
  color: var(--text);
  font-size: 12px;
  margin-bottom: 8px;
}

.tag-list {
  max-height: 180px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 1px;
}
.tag-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 6px;
  background: transparent;
  border: 0;
  color: var(--text);
  font-size: 12px;
  text-align: left;
  cursor: pointer;
  border-radius: 4px;
}
.tag-row:hover {
  background: var(--panel-2);
}
.tag-row.active {
  background: rgba(98, 107, 230, 0.14);
}
.check {
  color: var(--blue);
}
.check-spacer {
  width: 11px;
}
.tag-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.tag-count {
  color: var(--muted);
  font-size: 10px;
  font-variant-numeric: tabular-nums;
}

.pop-footer {
  display: flex;
  justify-content: flex-end;
  gap: 6px;
  padding: 10px 12px;
}
.pop-footer .btn {
  height: 28px;
  padding: 0 12px;
  font-size: 12px;
}

.slide-strip {
  display: flex;
  gap: 12px;
  overflow-x: auto;
  padding-bottom: 6px;
}
.slide-thumb {
  position: relative;
  flex-shrink: 0;
  width: 213px;
  height: 120px;
  border-radius: 6px;
  overflow: hidden;
  border: 1px solid var(--line);
  background: #0f1115;
}
.slide-thumb iframe {
  width: 1280px;
  height: 720px;
  border: 0;
  transform: scale(0.1664);
  transform-origin: top left;
  pointer-events: none;
}
.slide-num {
  position: absolute;
  bottom: 4px;
  right: 6px;
  font-size: 10px;
  color: var(--muted);
  background: rgba(0, 0, 0, 0.55);
  padding: 1px 5px;
  border-radius: 3px;
}

.recent-row {
  padding: 10px 12px;
  display: flex;
  align-items: center;
  gap: 10px;
  text-decoration: none;
}
.recent-row.clickable {
  cursor: pointer;
}
.recent-title {
  flex: 0 1 auto;
  font-size: 13px;
  color: var(--text);
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 40%;
}
.recent-sub {
  flex: 1;
  font-size: 11px;
  color: var(--muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.recent-spacer {
  flex: 0 0 auto;
}
.recent-status {
  font-size: 11px;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.4px;
}

.btn-mini {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  height: 26px;
  padding: 0 10px;
  font-size: 11px;
  font-weight: 500;
  border-radius: 5px;
  text-decoration: none;
  cursor: pointer;
}

.preview-md {
  max-height: 480px;
  overflow: auto;
  background: var(--panel-2);
  border: 1px solid var(--line);
  border-radius: 6px;
  padding: 14px 16px;
  font-size: 13px;
  line-height: 1.6;
  color: var(--text);
}
.preview-md :deep(h1) {
  font-size: 18px;
  margin: 0 0 10px;
  font-weight: 700;
}
.preview-md :deep(h2) {
  font-size: 14px;
  margin: 14px 0 6px;
  font-weight: 600;
  color: var(--text);
}
.preview-md :deep(h3) {
  font-size: 13px;
  margin: 12px 0 4px;
  font-weight: 600;
}
.preview-md :deep(p) {
  margin: 6px 0;
}
.preview-md :deep(ul),
.preview-md :deep(ol) {
  margin: 6px 0;
  padding-left: 22px;
}
.preview-md :deep(li) {
  margin: 2px 0;
}
.preview-md :deep(code) {
  background: rgba(255, 255, 255, 0.08);
  padding: 1px 4px;
  border-radius: 3px;
  font-size: 12px;
}
.preview-md :deep(pre) {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 5px;
  padding: 10px 12px;
  overflow: auto;
  font-size: 12px;
}
.preview-md :deep(pre code) {
  background: transparent;
  padding: 0;
}
.preview-md :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin: 8px 0;
}
.preview-md :deep(th),
.preview-md :deep(td) {
  border: 1px solid var(--line);
  padding: 6px 10px;
  text-align: left;
  font-size: 12px;
}
.preview-md :deep(img) {
  max-width: 100%;
  border-radius: 4px;
  margin: 6px 0;
}
.preview-md :deep(blockquote) {
  border-left: 3px solid var(--blue);
  padding-left: 10px;
  color: var(--muted);
  margin: 8px 0;
}
</style>
