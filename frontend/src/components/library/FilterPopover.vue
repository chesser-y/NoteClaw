<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from 'vue'
import { Filter, X, Check } from 'lucide-vue-next'
import { getKnowledgeFacets, type Facets } from '../../api/knowledge'

const props = defineProps<{
  selectedTags: string[]
  source: string
  dateFrom: string
  dateTo: string
}>()

const emit = defineEmits<{
  'update:selectedTags': [string[]]
  'update:source': [string]
  'update:dateFrom': [string]
  'update:dateTo': [string]
  'reset': []
}>()

const open = ref(false)
const root = ref<HTMLElement | null>(null)
const facets = ref<Facets>({ tags: [], sources: [], categories: [], content_types: [] })
const tagQuery = ref('')

async function loadFacets() {
  try {
    facets.value = await getKnowledgeFacets()
  } catch {
    facets.value = { tags: [], sources: [], categories: [], content_types: [] }
  }
}

function toggle() {
  if (!open.value) loadFacets()
  open.value = !open.value
}

function close() {
  open.value = false
}

function onClickOutside(e: MouseEvent) {
  if (!open.value) return
  if (root.value && !root.value.contains(e.target as Node)) close()
}

function toggleTag(tag: string) {
  const set = new Set(props.selectedTags)
  if (set.has(tag)) set.delete(tag)
  else set.add(tag)
  emit('update:selectedTags', [...set])
}

function clearAll() {
  emit('update:selectedTags', [])
  emit('update:source', '')
  emit('update:dateFrom', '')
  emit('update:dateTo', '')
  emit('reset')
  close()
}

const filteredTags = (limit = 30) => {
  const q = tagQuery.value.trim().toLowerCase()
  if (!q) return facets.value.tags.slice(0, limit)
  return facets.value.tags.filter(([t]) => t.toLowerCase().includes(q)).slice(0, limit)
}

const activeCount =
  props.selectedTags.length + (props.source ? 1 : 0) + (props.dateFrom || props.dateTo ? 1 : 0)

onMounted(() => document.addEventListener('mousedown', onClickOutside))
onUnmounted(() => document.removeEventListener('mousedown', onClickOutside))

watch(() => open.value, (v) => { if (v) loadFacets() })
</script>

<template>
  <div ref="root" class="filter-host">
    <button
      class="filter-trigger"
      type="button"
      :class="{ active: activeCount > 0 }"
      @click="toggle"
    >
      <Filter :size="13" />
      <span>Filter</span>
      <span v-if="activeCount" class="filter-badge">{{ activeCount }}</span>
    </button>

    <div v-if="open" class="filter-popover">
      <header class="pop-head">
        <span>Filters</span>
        <button class="icon-button" @click="close"><X :size="13" /></button>
      </header>

      <section class="pop-section">
        <div class="section-title">Tags</div>
        <input
          v-model="tagQuery"
          class="field tag-search"
          placeholder="搜索 tag…"
        />
        <div v-if="props.selectedTags.length" class="selected-chips">
          <span
            v-for="tag in props.selectedTags"
            :key="tag"
            class="chip chip-active"
            @click="toggleTag(tag)"
          >
            {{ tag }} <X :size="10" />
          </span>
        </div>
        <div class="tag-list">
          <button
            v-for="[tag, count] in filteredTags()"
            :key="tag"
            type="button"
            class="tag-row"
            :class="{ active: props.selectedTags.includes(tag) }"
            @click="toggleTag(tag)"
          >
            <Check v-if="props.selectedTags.includes(tag)" :size="11" class="check" />
            <span v-else class="check-spacer"></span>
            <span class="tag-name">{{ tag }}</span>
            <span class="tag-count">{{ count }}</span>
          </button>
          <div v-if="!facets.tags.length" class="muted small">暂无 tag</div>
        </div>
      </section>

      <section class="pop-section">
        <div class="section-title">Source</div>
        <select
          :value="props.source"
          class="field select"
          @change="(e) => emit('update:source', (e.target as HTMLSelectElement).value)"
        >
          <option value="">— Any —</option>
          <option v-for="s in facets.sources" :key="s" :value="s">{{ s }}</option>
        </select>
      </section>

      <section class="pop-section">
        <div class="section-title">Created date</div>
        <div class="date-row">
          <input
            type="date"
            :value="props.dateFrom"
            class="field date-input"
            @input="(e) => emit('update:dateFrom', (e.target as HTMLInputElement).value)"
          />
          <span class="muted small">→</span>
          <input
            type="date"
            :value="props.dateTo"
            class="field date-input"
            @input="(e) => emit('update:dateTo', (e.target as HTMLInputElement).value)"
          />
        </div>
      </section>

      <footer class="pop-footer">
        <button class="btn btn-ghost" @click="clearAll">Clear all</button>
        <button class="btn btn-primary" @click="close">Done</button>
      </footer>
    </div>
  </div>
</template>

<style scoped>
.filter-host {
  position: relative;
  display: inline-flex;
}

.filter-trigger {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 30px;
  padding: 0 12px;
  background: var(--panel-2);
  border: 1px solid var(--line);
  border-radius: 6px;
  color: var(--text);
  font-size: 12px;
  cursor: pointer;
}
.filter-trigger:hover {
  background: var(--panel-3);
}
.filter-trigger.active {
  border-color: var(--blue);
  color: var(--text);
}

.filter-badge {
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
  margin-left: 2px;
}

.filter-popover {
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

.selected-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-bottom: 8px;
}
.chip {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 999px;
  background: rgba(98, 107, 230, 0.18);
  border: 1px solid rgba(98, 107, 230, 0.4);
  color: var(--text);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 4px;
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

.select {
  width: 100%;
  height: 28px;
  background: var(--panel-2);
  border: 1px solid var(--line);
  border-radius: 5px;
  color: var(--text);
  font-size: 12px;
}

.date-row {
  display: flex;
  align-items: center;
  gap: 6px;
}
.date-input {
  flex: 1;
  height: 28px;
  background: var(--panel-2);
  border: 1px solid var(--line);
  border-radius: 5px;
  color: var(--text);
  font-size: 11px;
  padding: 0 6px;
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

.field {
  outline: none;
}

.muted {
  color: var(--muted);
}
.small {
  font-size: 11px;
}
</style>
