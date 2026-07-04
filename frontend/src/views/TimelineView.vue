<script setup lang="ts">
import { Plus, Filter } from 'lucide-vue-next'
import { useUiStore } from '../stores/ui'

const ui = useUiStore()

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

const items: Item[] = [
  {
    title: '多模态 RAG benchmark 设计',
    iconColor: 'var(--blue)',
    barColor: '',
    startCol: 1,
    span: 4,
    milestones: [
      { pos: 30, color: '' },
      { pos: 60, color: 'red' },
    ],
    labels: ['资料搜集', '评测集设计'],
  },
  {
    title: 'PDF RAG evaluation',
    iconColor: 'var(--green)',
    barColor: 'green',
    startCol: 1,
    span: 3,
    milestones: [
      { pos: 25, color: '' },
      { pos: 75, color: 'red' },
    ],
    labels: ['检索召回', '答案质量'],
  },
  {
    title: 'Visual document retrieval',
    iconColor: 'var(--blue)',
    barColor: 'blue',
    startCol: 2,
    span: 4,
    milestones: [
      { pos: 20, color: '' },
      { pos: 50, color: '' },
      { pos: 80, color: '' },
    ],
    labels: ['ViDoRe 样本', 'OCR 后处理', '多模态嵌入'],
  },
  {
    title: 'Code knowledge search',
    iconColor: 'var(--green)',
    barColor: '',
    startCol: 2,
    span: 3,
    milestones: [
      { pos: 30, color: '' },
      { pos: 70, color: '' },
    ],
    labels: ['CodeSearchNet', '函数级检索'],
  },
  {
    title: 'Personal notes evaluation',
    iconColor: 'var(--orange)',
    barColor: 'orange',
    startCol: 4,
    span: 3,
    milestones: [
      { pos: 40, color: '' },
    ],
    labels: ['标签订阅', '重复检测'],
  },
]
</script>

<template>
  <section class="timeline-view">
    <header class="topbar tight">
      <span>Timeline</span>
      <span class="dot-menu">...</span>
      <span class="spacer"></span>
      <span class="tool-icons">
        <Filter :size="16" />
        <Plus :size="16" @click="ui.openPalette()" style="cursor: pointer;" />
      </span>
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
