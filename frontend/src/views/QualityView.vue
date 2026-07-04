<script setup lang="ts">
import { useRouter } from 'vue-router'
import { ChevronLeft, Activity } from 'lucide-vue-next'

const router = useRouter()

type Metric = {
  label: string
  value: string
  sub: string
  trend?: 'up' | 'down'
  trendValue?: string
}

const retrieval: Metric[] = [
  { label: 'Recall@10', value: '0.82', sub: '20 queries · T2Retrieval subset', trend: 'up', trendValue: '+0.04' },
  { label: 'MRR', value: '0.61', sub: 'mean reciprocal rank', trend: 'up', trendValue: '+0.02' },
  { label: 'Citation hit rate', value: '0.94', sub: '答案是否引用了相关 chunk', trend: 'up', trendValue: '+0.01' },
]

const answer: Metric[] = [
  { label: 'Faithfulness', value: '0.88', sub: '答案是否忠实于来源', trend: 'up', trendValue: '+0.03' },
  { label: 'Unsupported claim rate', value: '0.06', sub: '未支撑声明比例', trend: 'down', trendValue: '-0.02' },
  { label: 'Source coverage', value: '2.4', sub: '平均引用来源数', trend: 'up', trendValue: '+0.3' },
]

const system: Metric[] = [
  { label: 'P50 latency', value: '1.2s', sub: 'chat 端到端', trend: 'down', trendValue: '-0.1s' },
  { label: 'P95 latency', value: '3.4s', sub: 'chat 端到端', trend: 'down', trendValue: '-0.4s' },
  { label: 'Task success rate', value: '0.91', sub: '近 7 天任务成功率', trend: 'up', trendValue: '+0.02' },
]

const knowledge: Metric[] = [
  { label: 'Duplicate rate', value: '0.04', sub: '相似度 > 0.85 的笔记占比', trend: 'down', trendValue: '-0.01' },
  { label: 'Untagged items', value: '2', sub: '需要补标签的笔记', trend: 'down', trendValue: '-1' },
  { label: 'Low-confidence OCR', value: '1', sub: '置信度 < 0.7 的图片', trend: 'up', trendValue: '+0' },
]

const agents = [
  { name: 'Retrieval', recall: 0.82, mrr: 0.61, hit: 0.94, tasks: 18 },
  { name: 'Generation', recall: 0.78, mrr: 0.55, hit: 0.91, tasks: 12 },
  { name: 'OCR + Vision', recall: 0.85, mrr: 0.69, hit: 0.96, tasks: 4 },
  { name: 'Harness', recall: 0.74, mrr: 0.52, hit: 0.88, tasks: 6 },
]

function trendClass(m: Metric) {
  if (!m.trend) return ''
  return m.trend === 'up' ? '' : 'down'
}

// chart bars: 8 weeks of latency values
const chartData = [
  { week: 'W1', p50: 1.8, p95: 4.6 },
  { week: 'W2', p50: 1.7, p95: 4.4 },
  { week: 'W3', p50: 1.6, p95: 4.1 },
  { week: 'W4', p50: 1.5, p95: 3.9 },
  { week: 'W5', p50: 1.4, p95: 3.7 },
  { week: 'W6', p50: 1.3, p95: 3.5 },
  { week: 'W7', p50: 1.2, p95: 3.4 },
  { week: 'W8', p50: 1.2, p95: 3.4 },
]
const maxLatency = 5
</script>

<template>
  <section class="quality-view">
    <header class="topbar tight">
      <button class="btn btn-ghost" style="height: 32px; padding: 0 10px;" @click="router.push('/settings')">
        <ChevronLeft :size="14" />
        Settings
      </button>
      <span>Quality & Evaluation</span>
      <span class="dot-menu">...</span>
      <span class="spacer"></span>
      <span class="tool-icons">
        <Activity :size="16" />
      </span>
    </header>

    <div class="insights">
      <h2 style="margin: 0 0 6px; font-size: 18px; color: var(--text); font-weight: 750;">Retrieval quality</h2>
      <p style="margin: 0 0 18px; font-size: 13px; color: var(--muted);">基于近 30 天 demo_subset 与 T2Retrieval 子集的离线评测。</p>

      <div class="metric-grid">
        <div v-for="m in retrieval" :key="m.label" class="metric-card">
          <div class="metric-label">{{ m.label }}</div>
          <div class="metric-value">{{ m.value }}</div>
          <div class="metric-sub">{{ m.sub }}</div>
          <div v-if="m.trend" class="metric-trend" :class="trendClass(m)">
            {{ m.trend === 'up' ? '↗' : '↘' }} {{ m.trendValue }}
          </div>
        </div>
      </div>

      <h2 style="margin: 14px 0 6px; font-size: 18px; color: var(--text); font-weight: 750;">Answer quality</h2>
      <p style="margin: 0 0 18px; font-size: 13px; color: var(--muted);">GPT-4o + RAG 生成答案的质量指标。</p>
      <div class="metric-grid">
        <div v-for="m in answer" :key="m.label" class="metric-card">
          <div class="metric-label">{{ m.label }}</div>
          <div class="metric-value">{{ m.value }}</div>
          <div class="metric-sub">{{ m.sub }}</div>
          <div v-if="m.trend" class="metric-trend" :class="trendClass(m)">
            {{ m.trend === 'up' ? '↗' : '↘' }} {{ m.trendValue }}
          </div>
        </div>
      </div>

      <h2 style="margin: 14px 0 6px; font-size: 18px; color: var(--text); font-weight: 750;">System performance</h2>
      <p style="margin: 0 0 18px; font-size: 13px; color: var(--muted);">端到端响应延迟与任务执行稳定性。</p>
      <div class="metric-grid">
        <div v-for="m in system" :key="m.label" class="metric-card">
          <div class="metric-label">{{ m.label }}</div>
          <div class="metric-value">{{ m.value }}</div>
          <div class="metric-sub">{{ m.sub }}</div>
          <div v-if="m.trend" class="metric-trend" :class="trendClass(m)">
            {{ m.trend === 'up' ? '↗' : '↘' }} {{ m.trendValue }}
          </div>
        </div>
      </div>

      <h2 style="margin: 14px 0 6px; font-size: 18px; color: var(--text); font-weight: 750;">Knowledge quality</h2>
      <p style="margin: 0 0 18px; font-size: 13px; color: var(--muted);">知识库内容健康度（来自 Review 队列）。</p>
      <div class="metric-grid">
        <div v-for="m in knowledge" :key="m.label" class="metric-card">
          <div class="metric-label">{{ m.label }}</div>
          <div class="metric-value">{{ m.value }}</div>
          <div class="metric-sub">{{ m.sub }}</div>
          <div v-if="m.trend" class="metric-trend" :class="trendClass(m)">
            {{ m.trend === 'up' ? '↗' : '↘' }} {{ m.trendValue }}
          </div>
        </div>
      </div>

      <div class="insights-bottom" style="margin-top: 28px;">
        <div class="insight-card">
          <div class="insight-title">Latency trend (8 weeks)</div>
          <div class="insight-body">
            <div style="display: flex; align-items: flex-end; gap: 14px; height: 220px; padding: 12px 0;">
              <div v-for="d in chartData" :key="d.week" style="display: flex; flex-direction: column; align-items: center; gap: 4px; flex: 1;">
                <div style="display: flex; align-items: flex-end; gap: 3px; height: 180px;">
                  <div
                    :style="{ width: '12px', height: ((d.p50 / maxLatency) * 100) + '%', background: 'var(--blue)', borderRadius: '2px 2px 0 0' }"
                    :title="`P50: ${d.p50}s`"
                  ></div>
                  <div
                    :style="{ width: '12px', height: ((d.p95 / maxLatency) * 100) + '%', background: 'var(--orange)', borderRadius: '2px 2px 0 0' }"
                    :title="`P95: ${d.p95}s`"
                  ></div>
                </div>
                <span style="font-size: 10px; color: var(--muted);">{{ d.week }}</span>
              </div>
            </div>
            <div style="display: flex; gap: 12px; font-size: 11px; color: var(--muted);">
              <span><span style="display: inline-block; width: 10px; height: 10px; background: var(--blue); margin-right: 4px;"></span>P50</span>
              <span><span style="display: inline-block; width: 10px; height: 10px; background: var(--orange); margin-right: 4px;"></span>P95</span>
            </div>
          </div>
        </div>

        <div class="insight-card">
          <div class="insight-title">Agent breakdown</div>
          <div class="insight-body" style="padding: 0;">
            <div class="data-table">
              <div class="head">Agent</div>
              <div class="head">Recall</div>
              <div class="head">MRR</div>
              <div class="head">Hit</div>
              <div class="head">Tasks</div>
              <template v-for="a in agents" :key="a.name">
                <div>{{ a.name }}</div>
                <div>{{ a.recall.toFixed(2) }}</div>
                <div>{{ a.mrr.toFixed(2) }}</div>
                <div>{{ a.hit.toFixed(2) }}</div>
                <div>{{ a.tasks }}</div>
              </template>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.quality-view {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow-y: auto;
}
</style>
