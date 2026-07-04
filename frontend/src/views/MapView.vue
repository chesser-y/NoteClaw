<script setup lang="ts">
import { ref } from 'vue'
import { Plus, Filter } from 'lucide-vue-next'
import { useUiStore } from '../stores/ui'

const ui = useUiStore()
const tab = ref<'active' | 'planned' | 'completed'>('active')

type Row = {
  indent: 0 | 1 | 2
  name: string
  detail?: string
  icon: string
  iconColor: '' | 'red' | 'green' | 'cyan'
  iconSmall?: boolean
  target?: string
  health?: 'on' | 'risk' | 'off'
  sources?: number
  tasks?: number
  projects?: string
}

const rows: Row[] = [
  { indent: 0, name: 'Research', icon: '⌂', iconColor: '', target: '2026', health: 'on', projects: '34 / 102', sources: 87, tasks: 12 },
  { indent: 1, name: 'RAG', icon: '▣', iconColor: '', iconSmall: true, target: '2026', health: 'on', projects: '12 / 38', sources: 44, tasks: 4 },
  { indent: 2, name: 'PDF RAG', detail: 'Multimodal PDF understanding', icon: '●', iconColor: '', iconSmall: true, target: 'Q3 2026', health: 'on', projects: '6 / 14', sources: 24, tasks: 3 },
  { indent: 2, name: 'Visual Documents', detail: 'docVQA / infovqa / arxivqa', icon: '●', iconColor: 'cyan', iconSmall: true, target: 'Q3 2026', health: 'on', projects: '4 / 12', sources: 12, tasks: 1 },
  { indent: 2, name: 'Chinese Retrieval', detail: 'T2Retrieval evaluation', icon: '●', iconColor: 'red', iconSmall: true, target: 'Q4 2026', health: 'risk', projects: '2 / 8', sources: 8, tasks: 0 },
  { indent: 1, name: 'Agent', icon: '✦', iconColor: '', iconSmall: true, target: '2026', health: 'risk', projects: '8 / 24', sources: 14, tasks: 3 },
  { indent: 2, name: 'Task execution', detail: 'Harness jobs and step traces', icon: '●', iconColor: '', iconSmall: true, target: 'H2 2026', health: 'on', projects: '3 / 9', sources: 6, tasks: 2 },
  { indent: 2, name: 'Multi-document reasoning', detail: 'Cross-note comparison', icon: '●', iconColor: 'cyan', iconSmall: true, target: 'Q4 2026', health: 'off', projects: '1 / 6', sources: 4, tasks: 1 },
  { indent: 1, name: 'Note-taking UX', icon: '▯', iconColor: '', iconSmall: true, target: '2026', health: 'on', projects: '14 / 40', sources: 29, tasks: 5 },
  { indent: 2, name: 'Capture', detail: 'Multimodal inbox flow', icon: '●', iconColor: '', iconSmall: true, target: 'Q3 2026', health: 'on', projects: '4 / 12', sources: 9, tasks: 2 },
  { indent: 2, name: 'Review', detail: 'Triage, dedupe, OCR confidence', icon: '●', iconColor: 'red', iconSmall: true, target: 'Q3 2026', health: 'risk', projects: '3 / 8', sources: 7, tasks: 1 },
  { indent: 2, name: 'Personalization', detail: 'Tag/category quality', icon: '●', iconColor: 'cyan', iconSmall: true, target: 'Q4 2026', health: 'on', projects: '2 / 6', sources: 5, tasks: 0 },
  { indent: 0, name: 'Product', icon: '⌂', iconColor: 'red', target: '2026', health: 'on', projects: '8 / 24', sources: 12, tasks: 3 },
]

const healthClass = (h?: Row['health']) => (h === 'risk' ? 'risk' : h === 'off' ? 'off' : '')
const healthLabel = (h?: Row['health']) => (h === 'risk' ? '↗ At risk' : h === 'off' ? '↘ Off track' : '↗ On track')
</script>

<template>
  <section class="map-view">
    <header class="topbar tight">
      <span>Map</span>
      <span class="dot-menu">...</span>
      <span class="spacer"></span>
      <span class="tool-icons">
        <Filter :size="16" />
        <Plus :size="16" @click="ui.openPalette()" style="cursor: pointer;" />
      </span>
    </header>

    <header class="topbar tight">
      <button class="tab" :class="{ active: tab === 'active' }" @click="tab = 'active'">Active</button>
      <button class="tab" :class="{ active: tab === 'planned' }" @click="tab = 'planned'">Planned</button>
      <button class="tab" :class="{ active: tab === 'completed' }" @click="tab = 'completed'">Completed</button>
    </header>

    <div class="initiative-table">
      <div class="initiative-head">
        <div>Name</div>
        <div>Target</div>
        <div>Health</div>
        <div>Projects</div>
        <div>Sources / Tasks</div>
        <div>Activity</div>
      </div>
      <div class="initiative-body">
        <div
          v-for="(row, i) in rows"
          :key="i"
          class="initiative-row"
          :style="row.indent === 1 ? { marginLeft: '32px' } : row.indent === 2 ? { marginLeft: '64px' } : {}"
        >
          <div class="initiative-name">
            <span
              class="node-icon"
              :class="[row.iconColor, { small: row.iconSmall }]"
            >{{ row.icon }}</span>
            <div>
              {{ row.name }}
              <small v-if="row.detail">{{ row.detail }}</small>
            </div>
          </div>
          <div>{{ row.target || '—' }}</div>
          <div>
            <span v-if="row.health" class="health-pill" :class="healthClass(row.health)">
              {{ healthLabel(row.health) }}
            </span>
            <span v-else style="color: var(--muted);">—</span>
          </div>
          <div>{{ row.projects || '—' }}</div>
          <div>
            <span v-if="row.sources !== undefined">{{ row.sources }} sources · {{ row.tasks }} tasks</span>
            <span v-else style="color: var(--muted);">—</span>
          </div>
          <div style="color: var(--green); font-weight: 700;">≋</div>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.map-view {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}
</style>
