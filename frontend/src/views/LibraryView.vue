<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Plus, Filter, SlidersHorizontal } from 'lucide-vue-next'
import { listKnowledge } from '../api/knowledge'
import type { ContentType, NoteListItem } from '../api/types'
import { useUiStore } from '../stores/ui'

const ui = useUiStore()

const items = ref<NoteListItem[]>([])
const total = ref(0)
const loading = ref(false)
const q = ref('')
const contentType = ref<ContentType | ''>('')
const selected = ref<NoteListItem | null>(null)

const tabs: { label: string; value: ContentType | '' }[] = [
  { label: 'All', value: '' },
  { label: 'Text', value: 'text' },
  { label: 'Code', value: 'code' },
  { label: 'Image', value: 'image' },
  { label: 'Table', value: 'table' },
  { label: 'Document', value: 'document' },
]

async function load() {
  loading.value = true
  try {
    const res = await listKnowledge({
      q: q.value || undefined,
      content_type: contentType.value,
      limit: 50,
    })
    items.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}

onMounted(load)

function onSearch() {
  load()
}

function setTab(t: ContentType | '') {
  contentType.value = t
  load()
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

const typeColor = (t: ContentType) => {
  switch (t) {
    case 'image': return '#4aaeff'
    case 'code': return 'var(--green)'
    case 'table': return 'var(--orange)'
    case 'document': return 'var(--pink)'
    default: return 'var(--blue)'
  }
}

const typeLabel = (t: ContentType) => {
  if (t === 'image') return 'Image'
  if (t === 'code') return 'Code'
  if (t === 'table') return 'Table'
  if (t === 'document') return 'PDF'
  if (t === 'webpage') return 'Web'
  return 'Note'
}

const filteredItems = computed(() => items.value)
</script>

<template>
  <section class="library-view">
    <header class="topbar tight">
      <span>Library</span>
      <span class="dot-menu">...</span>
      <span class="spacer"></span>
      <span class="tool-icons">
        <Filter :size="16" />
        <SlidersHorizontal :size="16" />
        <Plus :size="16" @click="ui.openPalette()" style="cursor: pointer;" />
      </span>
    </header>

    <header class="topbar tight" style="gap: 12px;">
      <input
        v-model="q"
        class="field"
        style="height: 32px; max-width: 320px; font-size: 13px;"
        placeholder="Search anything in your notes..."
        @keydown.enter="onSearch"
      />
      <div style="display: flex; gap: 2px;">
        <button
          v-for="t in tabs"
          :key="t.value"
          class="tab"
          :class="{ active: contentType === t.value }"
          @click="setTab(t.value)"
        >
          {{ t.label }}
        </button>
      </div>
      <span class="spacer"></span>
      <span class="muted" style="font-size: 12px;">{{ total }} items</span>
    </header>

    <div class="issues-table" style="padding: 18px 28px; flex: 1; overflow-y: auto;">
      <div v-if="loading" class="placeholder">Loading...</div>
      <div v-else-if="!filteredItems.length" class="placeholder">
        No notes yet. Paste content or drop a file in Inbox to get started.
      </div>
      <div v-else>
        <div
          v-for="item in filteredItems"
          :key="item.id"
          class="issue-row"
          @click="selected = item"
        >
          <span class="status-ring" :class="statusClass(item.status)"></span>
          <span class="pill square" :style="{ color: typeColor(item.content_type) }">
            {{ typeLabel(item.content_type) }}
          </span>
          <span class="priority"><span></span><span></span><span></span></span>
          <strong>{{ item.title }}</strong>
          <span class="right-tags">
            <span
              v-for="tag in (item.tags || []).slice(0, 3)"
              :key="tag"
              class="pill square"
            >
              #{{ tag }}
            </span>
            <span v-if="(item.tags || []).length > 3" class="pill square">
              +{{ (item.tags || []).length - 3 }}
            </span>
          </span>
          <span class="muted" style="font-size: 12px;">{{ item.source || 'manual' }}</span>
          <span class="date">{{ relativeTime(item.created_at) }}</span>
        </div>
      </div>
    </div>

    <div v-if="selected" class="drawer-backdrop" @click="selected = null">
      <div class="drawer-panel" @click.stop>
        <header class="topbar">
          <span>{{ selected.title }}</span>
          <span class="spacer"></span>
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
  </section>
</template>

<style scoped>
.library-view {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}
</style>
