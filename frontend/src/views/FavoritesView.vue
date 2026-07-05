<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { Star, MessageSquare, Eye } from 'lucide-vue-next'
import { listKnowledge, setNoteFavorite } from '../api/knowledge'
import { listChatSessions, setSessionFavorite } from '../api/chat'
import type { ChatSessionRead, ContentType, NoteListItem } from '../api/types'
import NotePreview from '../components/preview/NotePreview.vue'

const { t } = useI18n()
const router = useRouter()

type Tab = 'notes' | 'sessions'
const tab = ref<Tab>('notes')

const notes = ref<NoteListItem[]>([])
const sessions = ref<ChatSessionRead[]>([])
const loading = ref(false)
const selected = ref<NoteListItem | null>(null)
const previewId = ref<string | null>(null)

async function load() {
  loading.value = true
  try {
    const [notesRes, sessionsRes] = await Promise.all([
      listKnowledge({ is_favorite: true, limit: 100 }),
      listChatSessions(100, { favorites: true }),
    ])
    notes.value = notesRes.items
    sessions.value = sessionsRes
  } finally {
    loading.value = false
  }
}

onMounted(load)

function openPreview() {
  if (selected.value) previewId.value = selected.value.id
}
function closePreview() {
  previewId.value = null
}

async function toggleNoteFav(item: NoteListItem, ev: Event) {
  ev.stopPropagation()
  const next = !item.is_favorite
  const before = item.is_favorite
  item.is_favorite = next
  try {
    await setNoteFavorite(item.id, next)
    if (next === false) {
      notes.value = notes.value.filter((n) => n.id !== item.id)
    }
  } catch {
    item.is_favorite = before
  }
}

async function toggleSessionFav(s: ChatSessionRead, ev: Event) {
  ev.stopPropagation()
  const next = !s.is_favorite
  const before = s.is_favorite
  s.is_favorite = next
  try {
    await setSessionFavorite(s.id, next)
    if (next === false) {
      sessions.value = sessions.value.filter((x) => x.id !== s.id)
    }
  } catch {
    s.is_favorite = before
  }
}

function openSession(s: ChatSessionRead) {
  router.push({ name: 'inbox', query: { session: s.id } })
}

const relativeTime = (iso: string) => {
  const diff = (Date.now() - new Date(iso).getTime()) / 1000
  if (diff < 60) return 'just now'
  if (diff < 3600) return `${Math.floor(diff / 60)}m`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h`
  if (diff < 86400 * 7) return `${Math.floor(diff / 86400)}d ago`
  return new Date(iso).toLocaleDateString()
}

const statusClass = (status: string) => {
  if (status === 'ready') return 'green'
  if (status === 'pending' || status === 'processing') return ''
  if (status === 'failed') return 'gray'
  return 'gray'
}

const typeColor = (ct: ContentType) => {
  switch (ct) {
    case 'image': return '#4aaeff'
    case 'code': return 'var(--green)'
    case 'table': return 'var(--orange)'
    case 'document': return 'var(--pink)'
    default: return 'var(--blue)'
  }
}

const typeLabel = (ct: ContentType) => {
  if (ct === 'image') return 'Image'
  if (ct === 'code') return 'Code'
  if (ct === 'table') return 'Table'
  if (ct === 'document') return 'PDF'
  if (ct === 'webpage') return 'Web'
  return 'Note'
}

const tabs = computed<{ value: Tab; label: string; count: number }[]>(() => [
  { value: 'notes', label: t('favorites.tab-notes'), count: notes.value.length },
  { value: 'sessions', label: t('favorites.tab-sessions'), count: sessions.value.length },
])
</script>

<template>
  <section class="favorites-view">
    <header class="topbar tight">
      <span>{{ t('favorites.title') }}</span>
      <span class="spacer"></span>
      <span class="muted" style="font-size: 12px;">
        {{ notes.length + sessions.length }}
      </span>
    </header>

    <header class="topbar tight" style="gap: 12px;">
      <div style="display: flex; gap: 2px;">
        <button
          v-for="tb in tabs"
          :key="tb.value"
          class="tab"
          :class="{ active: tab === tb.value }"
          @click="tab = tb.value"
        >
          {{ tb.label }}
          <span class="muted" style="margin-left: 4px; font-size: 11px;">{{ tb.count }}</span>
        </button>
      </div>
      <span class="spacer"></span>
      <button class="icon-button" :title="t('action.refresh')" @click="load">
        <Eye :size="13" />
      </button>
    </header>

    <div class="fav-body">
      <div v-if="loading" class="placeholder">Loading...</div>

      <template v-else-if="tab === 'notes'">
        <div v-if="!notes.length" class="placeholder">
          {{ t('favorites.empty-notes') }}
        </div>
        <div v-else>
          <div
            v-for="item in notes"
            :key="item.id"
            class="issue-row"
            @click="selected = item"
          >
            <span class="status-ring" :class="statusClass(item.status)"></span>
            <span class="pill square" :style="{ color: typeColor(item.content_type) }">
              {{ typeLabel(item.content_type) }}
            </span>
            <strong>{{ item.title }}</strong>
            <span class="right-tags">
              <span
                v-for="tag in (item.tags || []).slice(0, 3)"
                :key="tag"
                class="pill square"
              >#{{ tag }}</span>
            </span>
            <span class="muted" style="font-size: 12px;">{{ item.source || 'manual' }}</span>
            <span class="date">{{ relativeTime(item.created_at) }}</span>
            <button
              class="icon-button star-btn"
              type="button"
              :title="t('favorites.title')"
              @click="toggleNoteFav(item, $event)"
            >
              <Star :size="13" :fill="item.is_favorite ? 'currentColor' : 'none'" />
            </button>
          </div>
        </div>
      </template>

      <template v-else>
        <div v-if="!sessions.length" class="placeholder">
          {{ t('favorites.empty-sessions') }}
        </div>
        <div v-else class="session-grid">
          <div
            v-for="s in sessions"
            :key="s.id"
            class="inbox-card session-card"
            @click="openSession(s)"
          >
            <MessageSquare :size="14" class="session-icon" />
            <div class="session-text">
              <strong>{{ s.title || 'Untitled' }}</strong>
              <span class="sub">
                {{ (s.message_count ?? 0) + t('inbox.messages-suffix') }}
                · {{ relativeTime(s.updated_at || s.created_at) }}
              </span>
            </div>
            <button
              class="icon-button star-btn"
              type="button"
              :title="t('favorites.title')"
              @click="toggleSessionFav(s, $event)"
            >
              <Star :size="13" :fill="s.is_favorite ? 'currentColor' : 'none'" />
            </button>
          </div>
        </div>
      </template>
    </div>

    <div v-if="selected" class="drawer-backdrop" @click="selected = null">
      <div class="drawer-panel" @click.stop>
        <header class="topbar">
          <span>{{ selected.title }}</span>
          <span class="spacer"></span>
          <button class="btn btn-ghost" style="height: 28px; padding: 0 10px; font-size: 12px;" @click="openPreview">
            <Eye :size="13" /> {{ t('action.preview') }}
          </button>
          <button class="icon-button" @click="selected = null">✕</button>
        </header>
        <div style="padding: 20px 24px; overflow-y: auto; flex: 1;">
          <div style="display: flex; gap: 8px; margin-bottom: 16px; flex-wrap: wrap;">
            <span class="pill square" :style="{ color: typeColor(selected.content_type) }">
              {{ typeLabel(selected.content_type) }}
            </span>
            <span
              v-for="tag in (selected.tags || [])"
              :key="tag"
              class="pill square"
            >#{{ tag }}</span>
          </div>
          <h3 style="margin: 0 0 12px; color: var(--text); font-size: 16px;">Summary</h3>
          <p style="margin: 0 0 24px; color: var(--muted); font-size: 14px; line-height: 1.5;">
            {{ selected.summary || '—' }}
          </p>
          <h3 style="margin: 0 0 12px; color: var(--text); font-size: 16px;">Metadata</h3>
          <div class="side-meta">
            <div class="side-row">
              <span class="label">Source</span>
              <span>{{ selected.source || 'manual' }}</span>
            </div>
            <div class="side-row">
              <span class="label">Category</span>
              <span>{{ selected.category || '—' }}</span>
            </div>
            <div class="side-row">
              <span class="label">Status</span>
              <span>{{ selected.status }}</span>
            </div>
            <div class="side-row">
              <span class="label">Created</span>
              <span>{{ new Date(selected.created_at).toLocaleString() }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <NotePreview :note-id="previewId" @close="closePreview" />
  </section>
</template>

<style scoped>
.favorites-view {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}
.fav-body {
  flex: 1;
  overflow-y: auto;
  padding: 18px 28px;
}
.session-grid {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.star-btn {
  width: 26px;
  height: 26px;
  padding: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: var(--orange, #f5a524);
}
.star-btn:hover {
  background: var(--panel-3, rgba(0,0,0,0.06));
}
.issue-row {
  position: relative;
}
.issue-row .star-btn {
  margin-left: 8px;
}
.session-card {
  cursor: pointer;
}
.session-icon {
  color: var(--muted);
  flex-shrink: 0;
  margin-top: 2px;
}
.session-text {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}
.session-text strong {
  font-size: 13px;
  color: var(--text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.session-text .sub {
  font-size: 11px;
  color: var(--muted);
}
</style>
