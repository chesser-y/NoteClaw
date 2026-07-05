<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Compass, Search, Brain, ShieldCheck, ChevronDown, Loader2, Check } from 'lucide-vue-next'
import type { ChatMessageResponse, Citation } from '../../api/types'

const props = defineProps<{
  trace?: ChatMessageResponse['trace']
  live?: boolean
}>()

type RawStep = {
  role?: string
  title?: string
  action?: string
  status?: string
  input_summary?: string | null
  output_summary?: string | null
  duration_ms?: number | null
  citations?: Citation[]
}

const metadata = computed(() => (props.trace?.metadata ?? {}) as Record<string, any>)

const steps = computed<RawStep[]>(() => {
  const raw = metadata.value.steps
  if (Array.isArray(raw)) return raw as RawStep[]
  return []
})

const plan = computed<string[]>(() => {
  const raw = metadata.value.plan
  if (Array.isArray(raw)) return raw as string[]
  return []
})

const review = computed(() => {
  const r = metadata.value.review
  if (!r || typeof r !== 'object') return null
  return r as { verdict?: string; confidence?: number; risks?: string[] }
})

const totalMs = computed(() =>
  steps.value.reduce((sum, s) => sum + (s.duration_ms ?? 0), 0),
)
const totalSeconds = computed(() => Math.max(1, Math.round(totalMs.value / 1000)))
const citationCount = computed(() =>
  steps.value.reduce((sum, s) => sum + (s.citations?.length ?? 0), 0),
)

const EXPECTED_TOTAL = 4
const completedCount = computed(() => steps.value.length)
const currentRole = computed(() => {
  if (!steps.value.length) return 'Coordinator'
  const last = steps.value[steps.value.length - 1]
  return labelFor(last.role || '')
})

const expanded = ref<Record<string, boolean>>({})
const ioExpand = ref<Record<string, boolean>>({})

watch(
  () => props.live,
  (live) => {
    if (live) expanded.value.expanded = true
  },
  { immediate: true },
)

function toggle() {
  expanded.value.expanded = !expanded.value.expanded
}

function toggleIo(key: string) {
  ioExpand.value[key] = !ioExpand.value[key]
}

const roleConfig: Record<string, { icon: typeof Compass; label: string; color: string }> = {
  coordinator: { icon: Compass, label: 'Coordinator', color: 'var(--blue)' },
  researcher: { icon: Search, label: 'Researcher', color: 'var(--green)' },
  reasoner: { icon: Brain, label: 'Reasoner', color: 'var(--pink)' },
  reviewer: { icon: ShieldCheck, label: 'Reviewer', color: 'var(--orange)' },
}

function cfg(role?: string) {
  return roleConfig[role || 'coordinator'] ?? roleConfig.coordinator
}
function labelFor(role: string) {
  return cfg(role).label
}

const statusText = computed(() => {
  if (props.live) {
    if (!completedCount.value) return 'Coordinator planning…'
    return `Working… ${completedCount.value}/${EXPECTED_TOTAL} · ${currentRole.value}`
  }
  if (!steps.value.length) return ''
  const parts = [`Done · ${steps.value.length} agents`, `${totalSeconds.value}s`]
  if (citationCount.value) parts.push(`${citationCount.value} cites`)
  return parts.join(' · ')
})
</script>

<template>
  <div class="agent-trace" :class="{ live }">
    <button class="trace-header" type="button" @click="toggle">
      <span class="status-dot" :class="live ? 'running' : 'done'">
        <Loader2 v-if="live" :size="9" class="spin" />
        <Check v-else :size="9" />
      </span>
      <span class="status-text">{{ statusText }}</span>
      <ChevronDown :size="12" class="chev" :class="{ open: expanded.expanded }" />
    </button>

    <div v-if="expanded.expanded" class="trace-panel">
      <div v-if="plan.length" class="plan-section">
        <div class="section-label">Plan</div>
        <ol class="plan-list">
          <li v-for="(p, i) in plan.slice(0, 6)" :key="i">{{ p }}</li>
        </ol>
      </div>

      <div class="pipeline">
        <div
          v-for="(step, i) in steps"
          :key="i"
          class="stage"
          :class="{ succeeded: step.status !== 'failed' }"
        >
          <header class="stage-head">
            <component :is="cfg(step.role).icon" :size="11" :style="{ color: cfg(step.role).color }" />
            <span class="stage-role">{{ cfg(step.role).label }}</span>
            <span v-if="step.duration_ms" class="stage-time">
              {{ (step.duration_ms / 1000).toFixed(1) }}s
            </span>
          </header>
          <div v-if="step.title" class="stage-title">{{ step.title }}</div>

          <section v-if="step.input_summary" class="stage-io">
            <div class="io-label">
              <span>Input</span>
              <button v-if="step.input_summary.length > 200" type="button" @click="toggleIo(`in-${i}`)">
                {{ ioExpand[`in-${i}`] ? 'less' : 'more' }}
              </button>
            </div>
            <pre class="io-text" :class="{ truncated: !ioExpand[`in-${i}`] }">{{ step.input_summary }}</pre>
          </section>

          <section v-if="step.output_summary" class="stage-io">
            <div class="io-label">
              <span>Output</span>
              <button v-if="step.output_summary.length > 200" type="button" @click="toggleIo(`out-${i}`)">
                {{ ioExpand[`out-${i}`] ? 'less' : 'more' }}
              </button>
            </div>
            <pre class="io-text" :class="{ truncated: !ioExpand[`out-${i}`] }">{{ step.output_summary }}</pre>
          </section>

          <div v-if="step.citations?.length" class="stage-cites">
            <span
              v-for="(c, ci) in step.citations.slice(0, 4)"
              :key="ci"
              class="cite-pill"
              :title="c.snippet"
            >[{{ ci + 1 }}] {{ c.title.slice(0, 18) }}</span>
          </div>
        </div>
      </div>

      <div v-if="review" class="review-row">
        <div class="section-label">Review</div>
        <div class="review-grid">
          <div v-if="review.verdict" class="review-cell">
            <span class="cell-label">Verdict</span>
            <span :class="review.verdict === 'approved' ? 'ok' : 'warn'">{{ review.verdict }}</span>
          </div>
          <div v-if="review.confidence != null" class="review-cell">
            <span class="cell-label">Confidence</span>
            <span>{{ Math.round(review.confidence * 100) }}%</span>
          </div>
          <div v-if="review.risks?.length" class="review-cell wide">
            <span class="cell-label">Risks</span>
            <span>{{ review.risks.slice(0, 3).join(' · ') }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.agent-trace {
  margin: 6px 0 2px;
  font-size: 12px;
  font-family: var(--font-mono, ui-monospace, "SF Mono", Consolas, monospace);
}
.agent-trace.live {
  /* subtle highlight while running */
}

.trace-header {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 3px 9px 3px 6px;
  border-radius: 999px;
  background: rgba(98, 107, 230, 0.10);
  border: 1px solid rgba(98, 107, 230, 0.22);
  color: var(--text);
  cursor: pointer;
  font-size: 11px;
  font-family: inherit;
}
.trace-header:hover {
  background: rgba(98, 107, 230, 0.18);
}

.status-dot {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 13px;
  height: 13px;
  border-radius: 50%;
  color: white;
}
.status-dot.running {
  background: var(--blue);
  animation: pulse 1.4s ease-in-out infinite;
}
.status-dot.done {
  background: var(--green);
}
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.status-text {
  font-weight: 500;
  letter-spacing: 0.1px;
}

.chev {
  transition: transform 160ms ease;
  color: var(--muted);
}
.chev.open {
  transform: rotate(180deg);
}

.trace-panel {
  margin-top: 6px;
  padding: 10px 12px;
  border-radius: 8px;
  background: var(--panel-2);
  border: 1px solid var(--line);
  display: flex;
  flex-direction: column;
  gap: 8px;
  font-size: 11px;
}

.section-label {
  font-size: 9px;
  text-transform: uppercase;
  letter-spacing: 0.8px;
  color: var(--muted);
  margin-bottom: 3px;
}

.plan-section {
  padding-bottom: 6px;
  border-bottom: 1px dashed var(--line);
}
.plan-list {
  margin: 0;
  padding-left: 18px;
  display: flex;
  flex-direction: column;
  gap: 1px;
  color: var(--text);
  font-family: var(--font-mono, ui-monospace, "SF Mono", Consolas, monospace);
}

.pipeline {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.stage {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 6px;
  padding: 7px 10px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stage-head {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 10px;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.6px;
}
.stage-role {
  flex: 1;
  color: var(--text);
  text-transform: none;
  letter-spacing: 0;
  font-size: 11px;
  font-weight: 600;
}
.stage-time {
  font-size: 10px;
  color: var(--muted);
  font-variant-numeric: tabular-nums;
}
.stage-title {
  color: var(--text);
  font-size: 11px;
  font-weight: 500;
}

.stage-io {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.io-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 9px;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.6px;
}
.io-label button {
  background: transparent;
  border: 0;
  color: var(--blue);
  font-size: 9px;
  cursor: pointer;
  text-transform: none;
  letter-spacing: 0;
  padding: 0;
}
.io-text {
  margin: 0;
  padding: 4px 6px;
  background: var(--bg);
  border: 1px solid var(--line-soft, var(--line));
  border-radius: 4px;
  font-family: inherit;
  font-size: 10.5px;
  line-height: 1.45;
  color: var(--text);
  white-space: pre-wrap;
  word-break: break-word;
  overflow: hidden;
}
.io-text.truncated {
  max-height: 60px;
  position: relative;
}
.io-text.truncated::after {
  content: '';
  position: absolute;
  inset: auto 0 0 0;
  height: 16px;
  background: linear-gradient(transparent, var(--bg));
  pointer-events: none;
}

.stage-cites {
  display: flex;
  flex-wrap: wrap;
  gap: 3px;
}
.cite-pill {
  font-size: 9px;
  padding: 1px 5px;
  border-radius: 3px;
  background: var(--panel-2);
  color: var(--muted);
  border: 1px solid var(--line);
}

.review-row {
  padding-top: 6px;
  border-top: 1px dashed var(--line);
}
.review-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 4px 12px;
}
.review-cell {
  display: flex;
  flex-direction: column;
  gap: 1px;
}
.review-cell.wide {
  grid-column: 1 / -1;
}
.cell-label {
  font-size: 9px;
  text-transform: uppercase;
  letter-spacing: 0.6px;
  color: var(--muted);
}
.review-cell .ok { color: var(--green); }
.review-cell .warn { color: var(--orange); }

.spin {
  animation: spin 1s linear infinite;
}
@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
