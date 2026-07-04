<script setup lang="ts">
import { ref } from 'vue'
import { Plus, Filter, CheckCircle2, X, Clock } from 'lucide-vue-next'
import { useUiStore } from '../stores/ui'

const ui = useUiStore()

type ReviewItem = {
  id: string
  type: 'duplicate' | 'tag-suggest' | 'low-ocr' | 'conflict' | 'pending-gen'
  title: string
  body: string
  actions: { label: string; kind: 'primary' | 'ghost' | 'danger' }[]
}

const items = ref<ReviewItem[]>([
  {
    id: 'r1',
    type: 'duplicate',
    title: '这两篇笔记可能重复',
    body: 'Open-RAGBench section 与 Inverter Output Impedance Estimation 内容重叠 60% 以上。建议合并或保留两份。',
    actions: [
      { label: '合并', kind: 'primary' },
      { label: '保留两份', kind: 'ghost' },
      { label: '稍后', kind: 'ghost' },
    ],
  },
  {
    id: 'r2',
    type: 'tag-suggest',
    title: '建议将 "Open RAG Benchmark" 加入 #PDF-RAG',
    body: '基于内容相似度与已有标签分布，这篇笔记与 #PDF-RAG 主题高度相关。',
    actions: [
      { label: '接受', kind: 'primary' },
      { label: '修改', kind: 'ghost' },
    ],
  },
  {
    id: 'r3',
    type: 'low-ocr',
    title: '截图 OCR 置信度较低',
    body: 'financial_table_image.png 的 OCR 文本中包含若干数字识别为字母（0 ↔ O、5 ↔ S）。建议人工校对或重新识别。',
    actions: [
      { label: '编辑文本', kind: 'primary' },
      { label: '重新识别', kind: 'ghost' },
    ],
  },
  {
    id: 'r4',
    type: 'conflict',
    title: '冲突信息： dividend payout 数字不一致',
    body: 'document_question_page.png 显示 2012 年 dividend payout 为 18.5%，但 financial_table_image.png 给出 19.2%。请确认正确数值。',
    actions: [
      { label: '标为冲突', kind: 'danger' },
      { label: '查看来源', kind: 'ghost' },
    ],
  },
  {
    id: 'r5',
    type: 'pending-gen',
    title: '生成结果待确认：项目展示 PPT 大纲',
    body: '已生成 12 张幻灯片草稿。第 4 张关于「评测指标」的内容较薄弱，是否补充？',
    actions: [
      { label: '接受草稿', kind: 'primary' },
      { label: '补充第 4 张', kind: 'ghost' },
      { label: '重新生成', kind: 'ghost' },
    ],
  },
  {
    id: 'r6',
    type: 'tag-suggest',
    title: '建议给 4 篇 code 笔记统一加 #CodeSearchNet',
    body: 'python_YouTube.get_vid_from_url / javascript_createInstance / go_mustWaitPinReady / ruby_KubernetesDeploy 来源相同，可批量打标。',
    actions: [
      { label: '批量接受', kind: 'primary' },
      { label: '逐个确认', kind: 'ghost' },
    ],
  },
])

function dismiss(id: string) {
  items.value = items.value.filter((i) => i.id !== id)
}

function act(id: string) {
  // For stub: just dismiss
  items.value = items.value.filter((i) => i.id !== id)
}

const typeColor: Record<ReviewItem['type'], string> = {
  duplicate: 'var(--pink)',
  'tag-suggest': 'var(--blue)',
  'low-ocr': 'var(--orange)',
  conflict: 'var(--pink)',
  'pending-gen': 'var(--green)',
}

const typeLabel: Record<ReviewItem['type'], string> = {
  duplicate: 'Duplicate',
  'tag-suggest': 'Tag',
  'low-ocr': 'OCR',
  conflict: 'Conflict',
  'pending-gen': 'Generated',
}
</script>

<template>
  <section class="review-view">
    <header class="topbar tight">
      <span>Review</span>
      <span class="dot-menu">...</span>
      <span class="spacer"></span>
      <span class="tool-icons">
        <Filter :size="16" />
        <Plus :size="16" @click="ui.openPalette()" style="cursor: pointer;" />
      </span>
    </header>

    <header class="topbar tight">
      <span style="font-size: 13px; color: var(--muted);">Needs review</span>
      <span class="pill square">{{ items.length }}</span>
      <span class="spacer"></span>
      <button class="btn btn-ghost" style="height: 28px; font-size: 12px;">
        <CheckCircle2 :size="14" />
        全部已处理
      </button>
    </header>

    <div class="review-list">
      <div v-if="!items.length" class="placeholder">
        <CheckCircle2 :size="32" style="color: var(--green);" />
        <div style="margin-top: 12px;">所有内容已确认 ✨</div>
      </div>

      <div
        v-for="item in items"
        :key="item.id"
        class="review-item"
      >
        <div class="review-title">
          <span class="pill square" :style="{ color: typeColor[item.type] }">
            {{ typeLabel[item.type] }}
          </span>
          <span>{{ item.title }}</span>
          <button class="icon-button" style="margin-left: auto; width: 28px; height: 28px;" @click="dismiss(item.id)">
            <X :size="14" />
          </button>
        </div>
        <div class="review-body">{{ item.body }}</div>
        <div class="review-actions">
          <button
            v-for="(a, ai) in item.actions"
            :key="ai"
            class="btn"
            :class="{
              'btn-primary': a.kind === 'primary',
              'btn-ghost': a.kind === 'ghost',
            }"
            :style="a.kind === 'danger' ? { color: 'var(--pink)', borderColor: 'rgba(232,91,134,.4)' } : {}"
            style="height: 28px; padding: 0 12px; font-size: 12px;"
            @click="act(item.id)"
          >
            {{ a.label }}
          </button>
          <button
            class="btn btn-ghost"
            style="height: 28px; padding: 0 10px; font-size: 12px; margin-left: auto;"
            @click="dismiss(item.id)"
          >
            <Clock :size="12" />
            稍后
          </button>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.review-view {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow-y: auto;
}
</style>
