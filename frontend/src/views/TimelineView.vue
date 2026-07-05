<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  FileText,
  Image as ImageIcon,
  Code2,
  Table as TableIcon,
  FileCheck2,
  Loader2,
  AlertCircle,
  CheckCircle2,
  CircleDashed,
} from 'lucide-vue-next'
import { listKnowledge } from '../api/knowledge'
import { listTasks } from '../api/tasks'
import type { ContentType, NoteListItem, TaskRead, TaskStatus } from '../api/types'

const { t, locale } = useI18n()

type EventKind = 'note' | 'task'
type EventTypeFilter = 'all' | EventKind

type TEvent = {
  id: string
  kind: EventKind
  ts: string
  title: string
  sub: string
  status?: TaskStatus | string
  contentType?: ContentType
  source?: string | null
}

const loading = ref(false)
const error = ref('')
const filter = ref<EventTypeFilter>('all')
const notes = ref<NoteListItem[]>([])
const tasks = ref<TaskRead[]>([])

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [k, tt] = await Promise.all([
      listKnowledge({ limit: 100 }),
      listTasks({ limit: 100 }),
    ])
    notes.value = k.items
    tasks.value = tt.items
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    loading.value = false
  }
}

onMounted(load)

function bucketOf(iso: string): string {
  const now = new Date()
  const d = new Date(iso)
  const dayMs = 86400000
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime()
  const dTime = d.getTime()
  if (dTime >= startOfToday) return 'today'
  if (dTime >= startOfToday - dayMs) return 'yesterday'
  if (dTime >= startOfToday - dayMs * 6) return 'this-week'
  if (dTime >= startOfToday - dayMs * 29) return 'this-month'
  return 'earlier'
}

const bucketOrder = ['today', 'yesterday', 'this-week', 'this-month', 'earlier']

function bucketLabel(key: string): string {
  switch (key) {
    case 'today': return t('timeline.today')
    case 'yesterday': return t('timeline.yesterday')
    case 'this-week': return t('timeline.this-week')
    case 'this-month': return t('timeline.this-month')
    default: return t('timeline.earlier')
  }
}

const events = computed<TEvent[]>(() => {
  const noteEvents: TEvent[] = notes.value
    .filter(() => filter.value === 'all' || filter.value === 'note')
    .map((n) => ({
      id: n.id,
      kind: 'note' as const,
      ts: n.created_at,
      title: n.title,
      sub: n.summary?.slice(0, 140) || '',
      status: n.status,
      contentType: n.content_type,
      source: n.source,
    }))
  const taskEvents: TEvent[] = tasks.value
    .filter(() => filter.value === 'all' || filter.value === 'task')
    .map((tt) => ({
      id: tt.id,
      kind: 'task' as const,
      ts: tt.updated_at || tt.created_at,
      title: tt.message || tt.type,
      sub: `${tt.type} · ${Math.round((tt.progress || 0) * 100)}%${tt.error ? ' · ' + tt.error.slice(0, 80) : ''}`,
      status: tt.status,
    }))
  return [...noteEvents, ...taskEvents].sort(
    (a, b) => new Date(b.ts).getTime() - new Date(a.ts).getTime(),
  )
})

const grouped = computed(() => {
  const buckets: Record<string, TEvent[]> = {}
  for (const ev of events.value) {
    const b = bucketOf(ev.ts)
    if (!buckets[b]) buckets[b] = []
    buckets[b].push(ev)
  }
  return bucketOrder
    .filter((b) => buckets[b]?.length)
    .map((b) => ({ bucket: b, label: bucketLabel(b), items: buckets[b] }))
})

const stats = computed(() => ({
  total: events.value.length,
  notes: notes.value.length,
  tasks: tasks.value.length,
}))

const statsLabel = computed(() => {
  if (locale.value === 'zh') {
    return `${stats.value.notes} 篇资料 · ${stats.value.tasks} 个任务`
  }
  return `${stats.value.notes} notes · ${stats.value.tasks} tasks`
})

function iconFor(ev: TEvent) {
  if (ev.kind === 'task') return FileCheck2
  if (ev.contentType === 'image') return ImageIcon
  if (ev.contentType === 'code') return Code2
  if (ev.contentType === 'table') return TableIcon
  return FileText
}

function statusIconFor(ev: TEvent) {
  if (ev.kind !== 'task') return null
  const s = ev.status as TaskStatus
  if (s === 'succeeded') return CheckCircle2
  if (s === 'failed') return AlertCircle
  if (s === 'running' || s === 'queued') return Loader2
  return CircleDashed
}

function statusColor(ev: TEvent) {
  const s = ev.status
  if (s === 'succeeded' || s === 'ready') return 'var(--green)'
  if (s === 'failed') return 'var(--red, #ef4444)'
  if (s === 'running' || s === 'queued' || s === 'processing') return 'var(--blue)'
  return 'var(--muted)'
}

const fmtTime = (iso: string) => {
  const d = new Date(iso)
  const l = locale.value === 'zh' ? 'zh-CN' : 'en-US'
  return d.toLocaleTimeString(l, { hour: '2-digit', minute: '2-digit' })
}
const fmtDate = (iso: string) => {
  const d = new Date(iso)
  if (locale.value === 'zh') {
    return `${d.getMonth() + 1}月${d.getDate()}日`
  }
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

const refreshLabel = computed(() => t('action.refresh'))
const emptyText = computed(() =>
  locale.value === 'zh'
    ? '暂无活动。在 Inbox 粘贴内容或上传文件，活动会自动出现在这里。'
    : 'No activity yet. Paste content or drop a file in Inbox and it will show up here.',
)
</script>

<template>
  <section class="timeline-view">
    <header class="topbar tight">
      <span>{{ t('view.timeline') }}</span>
      <span class="spacer"></span>
      <span class="muted small">{{ statsLabel }}</span>
    </header>

    <header class="topbar tight">
      <div style="display: flex; gap: 2px;">
        <button
          class="tab"
          :class="{ active: filter === 'all' }"
          @click="filter = 'all'"
        >
          {{ t('timeline.filter-all') }}
        </button>
        <button
          class="tab"
          :class="{ active: filter === 'note' }"
          @click="filter = 'note'"
        >
          {{ t('timeline.filter-notes') }}
        </button>
        <button
          class="tab"
          :class="{ active: filter === 'task' }"
          @click="filter = 'task'"
        >
          {{ t('timeline.filter-tasks') }}
        </button>
      </div>
      <span class="spacer"></span>
      <button class="btn btn-ghost" style="height: 28px; padding: 0 10px; font-size: 12px;" @click="load">
        <Loader2 v-if="loading" :size="12" class="spin" />
        {{ refreshLabel }}
      </button>
    </header>

    <div class="timeline-body">
      <div v-if="loading && !events.length" class="placeholder">
        <Loader2 :size="20" class="spin" />
        {{ locale === 'zh' ? '加载中…' : 'Loading…' }}
      </div>
      <div v-else-if="error" class="placeholder error">{{ error }}</div>
      <div v-else-if="!events.length" class="placeholder">
        {{ emptyText }}
      </div>

      <div v-else class="timeline-list">
        <section v-for="group in grouped" :key="group.bucket" class="timeline-group">
          <div class="group-rule">
            <span class="group-label">{{ group.label }}</span>
            <span class="group-count">{{ group.items.length }}</span>
          </div>

          <div class="group-items">
            <article
              v-for="(ev, i) in group.items"
              :key="ev.id"
              class="timeline-item"
              :class="{ last: i === group.items.length - 1 }"
            >
              <div class="dot-col">
                <span class="dot" :style="{ color: statusColor(ev) }">
                  <component :is="iconFor(ev)" :size="14" />
                </span>
                <span v-if="i !== group.items.length - 1" class="line"></span>
              </div>
              <div class="item-body">
                <div class="item-head">
                  <strong>{{ ev.title }}</strong>
                  <span class="item-time">{{ fmtTime(ev.ts) }}</span>
                </div>
                <p v-if="ev.sub" class="item-sub">{{ ev.sub }}</p>
                <div class="item-foot">
                  <span v-if="ev.kind === 'task'" class="badge" :style="{ color: statusColor(ev) }">
                    <component
                      :is="statusIconFor(ev)"
                      v-if="statusIconFor(ev)"
                      :size="11"
                      :class="{ spin: ev.status === 'running' || ev.status === 'queued' }"
                    />
                    {{ ev.status }}
                  </span>
                  <span v-else class="badge" :style="{ color: statusColor(ev) }">
                    {{ ev.contentType }}{{ ev.source ? ' · ' + ev.source : '' }}
                  </span>
                  <span class="muted small">{{ fmtDate(ev.ts) }}</span>
                </div>
              </div>
            </article>
          </div>
        </section>
      </div>
    </div>
  </section>
</template>

<style scoped>
.timeline-view {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.timeline-body {
  flex: 1;
  overflow-y: auto;
  padding: 18px 28px 32px;
}

.placeholder {
  color: var(--muted);
  text-align: center;
  padding: 60px 16px;
  font-size: 13px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}
.placeholder.error {
  color: var(--red, #ef4444);
}

.timeline-list {
  display: flex;
  flex-direction: column;
  gap: 22px;
  max-width: 720px;
}

.group-rule {
  display: flex;
  align-items: center;
  gap: 8px;
  padding-bottom: 8px;
  margin-bottom: 4px;
  border-bottom: 1px solid var(--line);
}
.group-label {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.6px;
  color: var(--muted);
}
.group-count {
  font-size: 10px;
  color: var(--muted);
  background: var(--panel-2);
  padding: 1px 6px;
  border-radius: 8px;
}

.group-items {
  display: flex;
  flex-direction: column;
}

.timeline-item {
  display: flex;
  gap: 12px;
  padding: 6px 0;
}

.dot-col {
  position: relative;
  width: 22px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
}
.dot {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: var(--panel-2);
  border: 1px solid var(--line);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  z-index: 1;
}
.line {
  width: 1px;
  flex: 1;
  background: var(--line);
  margin-top: 2px;
  margin-bottom: 2px;
}

.item-body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding-bottom: 14px;
}
.timeline-item.last .item-body {
  padding-bottom: 4px;
}

.item-head {
  display: flex;
  align-items: baseline;
  gap: 8px;
}
.item-head strong {
  flex: 1;
  font-size: 13.5px;
  color: var(--text);
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.item-time {
  font-size: 11px;
  color: var(--muted);
  font-variant-numeric: tabular-nums;
  flex-shrink: 0;
}

.item-sub {
  margin: 0;
  font-size: 12.5px;
  color: var(--text);
  opacity: 0.75;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.item-foot {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 2px;
}
.badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 10.5px;
  padding: 1px 6px;
  border-radius: 4px;
  background: var(--panel-2);
}

.spin {
  animation: spin 1s linear infinite;
}
@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.muted {
  color: var(--muted);
}
.small {
  font-size: 11px;
}
</style>
