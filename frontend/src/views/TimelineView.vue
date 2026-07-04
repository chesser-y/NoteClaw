<script setup lang="ts">
const months = ['APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP']
const weeks = [['26', '4', '11', '18'], ['25', '1', '8', '15'], ['22', '29', '6', '18'], ['20', '27', '3', '10'], ['24', '1', '8', '15'], ['22', '29', '5', '12']]

type Item = {
  title: string
  iconColor: string
  barColor: '' | 'blue' | 'green' | 'orange'
  startCol: number
  span: number
  milestones: { pos: number; color: '' | 'red' | 'green' }[]
  labels: string[]
}

const items: Item[] = []
</script>

<template>
  <section class="timeline-view">
    <header class="topbar tight">
      <span>Timeline</span>
      <span class="spacer"></span>
    </header>

    <div class="timeline-page">
      <div class="timeline-head">
        <div v-for="(m, i) in months" :key="m" class="month">
          {{ m }}
          <div class="weeks">
            <span v-for="(w, wi) in weeks[i]" :key="wi">{{ w }}</span>
          </div>
        </div>
      </div>

      <div class="gantt">
        <div v-if="!items.length" class="placeholder" style="padding: 60px 16px; font-size: 13px;">
          暂无 timeline 数据
        </div>
        <div
          v-for="(item, i) in items"
          :key="i"
          class="gantt-item"
          :style="{
            gridColumn: `${item.startCol} / span ${item.span}`,
          }"
        >
          <div class="gantt-title">
            <span class="status-ring" :style="{ borderColor: item.iconColor, background: item.iconColor, color: '#0d1011' }"></span>
            {{ item.title }}
            <span class="priority"><span></span><span></span><span></span></span>
          </div>
          <div class="bar" :class="item.barColor">
            <span
              v-for="(ms, mi) in item.milestones"
              :key="mi"
              class="milestone"
              :class="ms.color"
              :style="{ left: ms.pos + '%' }"
            ></span>
          </div>
          <div class="bar-labels">
            <span v-for="(l, li) in item.labels" :key="li">{{ l }}</span>
          </div>
        </div>
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

/* override gantt-item absolute pattern from style.css for grid usage */
.timeline-view :deep(.gantt-item) {
  position: relative;
  margin-bottom: 22px;
  padding-left: 8px;
}

.timeline-view :deep(.gantt) {
  display: flex;
  flex-direction: column;
  padding: 24px 32px;
  overflow-y: auto;
}
</style>
