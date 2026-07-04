<script setup lang="ts">
import { ref } from 'vue'

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

const rows: Row[] = []

const healthClass = (h?: Row['health']) => (h === 'risk' ? 'risk' : h === 'off' ? 'off' : '')
const healthLabel = (h?: Row['health']) => (h === 'risk' ? '↗ At risk' : h === 'off' ? '↘ Off track' : '↗ On track')
</script>

<template>
  <section class="map-view">
    <header class="topbar tight">
      <span>Map</span>
      <span class="spacer"></span>
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
        <div v-if="!rows.length" class="placeholder" style="padding: 60px 16px; font-size: 13px;">
          暂无项目地图数据
        </div>
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
