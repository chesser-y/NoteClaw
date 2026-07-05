<script setup lang="ts">
import { computed } from 'vue'
import { Compass, Search, Brain, ShieldCheck, ChevronDown } from 'lucide-vue-next'
import type { ChatMessageResponse } from '../../api/types'

const props = defineProps<{
  trace: ChatMessageResponse['trace']
}>()

const steps = computed(() => props.trace?.steps ?? [])
const plan = computed(() => props.trace?.plan ?? [])
const review = computed(() => props.trace?.review ?? null)

const totalMs = computed(() =>
  steps.value.reduce((sum, s) => sum + (s.duration_ms ?? 0), 0),
)
const totalSeconds = computed(() => Math.max(1, Math.round(totalMs.value / 1000)))
const citationCount = computed(() =>
  steps.value.reduce((sum, s) => sum + (s.citations?.length ?? 0), 0),
)

const roleConfig: Record<
  string,
  { icon: typeof Compass; label: string; color: string }
> = {
  coordinator: { icon: Compass, label: 'Coordinator', color: 'var(--blue)' },
  researcher: { icon: Search, label: 'Researcher', color: 'var(--green)' },
  reasoner: { icon: Brain, label: 'Reasoner', color: 'var(--pink)' },
  reviewer: { icon: ShieldCheck, label: 'Reviewer', color: 'var(--orange)' },
}

function cfg(role: string) {
  return roleConfig[role] ?? roleConfig.coordinator
}
</script>

<template>
  <details class="agent-trace">
    <summary class="trace-chip">
      <span class="bot-dot">🤖</span>
      <span class="chip-text">
        {{ steps.length || 4 }} agents · {{ totalSeconds }}s
        <span v-if="citationCount"> · {{ citationCount }} 引用</span>
      </span>
      <ChevronDown :size="12" class="chev" />
    </summary>

    <div class="trace-body">
      <div v-if="plan.length" class="trace-section">
        <div class="section-head">Plan</div>
        <ol class="plan-list">
          <li v-for="(p, i) in plan" :key="i">{{ p }}</li>
        </ol>
      </div>

      <div class="step-grid">
        <div
          v-for="(step, i) in steps"
          :key="i"
          class="step-card"
        >
          <header class="step-head">
            <component
              :is="cfg(step.role).icon"
              :size="13"
              :style="{ color: cfg(step.role).color }"
            />
            <span class="step-role">{{ cfg(step.role).label }}</span>
            <span v-if="step.duration_ms" class="step-dur">
              {{ Math.round(step.duration_ms / 100) / 10 }}s
            </span>
          </header>
          <div v-if="step.title" class="step-title">{{ step.title }}</div>
          <div v-if="step.output" class="step-output">{{ step.output }}</div>
          <div v-if="step.citations?.length" class="step-cites">
            <span
              v-for="(c, ci) in step.citations.slice(0, 3)"
              :key="ci"
              class="cite-pill"
              :title="c.snippet"
            >
              [{{ ci + 1 }}] {{ c.title.slice(0, 20) }}
            </span>
          </div>
        </div>
      </div>

      <div v-if="review" class="trace-section review-section">
        <div class="section-head">Review</div>
        <div class="review-grid">
          <div v-if="review.verdict" class="review-row">
            <span class="label">Verdict</span>
            <span>{{ review.verdict }}</span>
          </div>
          <div v-if="review.confidence != null" class="review-row">
            <span class="label">Confidence</span>
            <span>{{ Math.round(review.confidence * 100) }}%</span>
          </div>
          <div v-if="review.risks?.length" class="review-row">
            <span class="label">Risks</span>
            <span>{{ review.risks.join(' · ') }}</span>
          </div>
        </div>
      </div>
    </div>
  </details>
</template>

<style scoped>
.agent-trace {
  margin-top: 6px;
  font-size: 12px;
}

.trace-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 3px 9px 3px 6px;
  border-radius: 999px;
  background: rgba(98, 107, 230, 0.12);
  border: 1px solid rgba(98, 107, 230, 0.28);
  cursor: pointer;
  list-style: none;
  user-select: none;
  color: var(--text);
  font-size: 11px;
}
.agent-trace[open] .trace-chip {
  border-radius: 999px;
}
.trace-chip::-webkit-details-marker {
  display: none;
}
.bot-dot {
  font-size: 11px;
}
.chip-text {
  font-weight: 500;
  letter-spacing: 0.2px;
}
.chev {
  transition: transform 160ms ease;
  color: var(--muted);
}
.agent-trace[open] .chev {
  transform: rotate(180deg);
}

.trace-body {
  margin-top: 8px;
  padding: 10px 12px;
  border-radius: var(--r-md, 8px);
  background: var(--panel-2);
  border: 1px solid var(--line);
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.trace-section .section-head {
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.6px;
  color: var(--muted);
  margin-bottom: 4px;
}
.plan-list {
  margin: 0;
  padding-left: 18px;
  display: flex;
  flex-direction: column;
  gap: 2px;
  color: var(--text);
}

.step-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 6px;
}
@media (max-width: 640px) {
  .step-grid {
    grid-template-columns: 1fr;
  }
}

.step-card {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 6px;
  padding: 8px 10px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.step-head {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: var(--muted);
}
.step-role {
  flex: 1;
  color: var(--text);
  font-weight: 600;
}
.step-dur {
  font-size: 10px;
  color: var(--muted);
  font-variant-numeric: tabular-nums;
}
.step-title {
  color: var(--text);
  font-size: 12px;
  font-weight: 500;
  line-height: 1.4;
}
.step-output {
  color: var(--muted);
  font-size: 11px;
  line-height: 1.45;
  max-height: 80px;
  overflow-y: auto;
  white-space: pre-wrap;
}
.step-cites {
  display: flex;
  flex-wrap: wrap;
  gap: 3px;
  margin-top: 2px;
}
.cite-pill {
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 3px;
  background: var(--panel-2);
  color: var(--muted);
  border: 1px solid var(--line);
}

.review-section {
  border-top: 1px solid var(--line-soft, var(--line));
  padding-top: 8px;
}
.review-grid {
  display: flex;
  flex-direction: column;
  gap: 3px;
  font-size: 11px;
}
.review-row {
  display: flex;
  gap: 8px;
}
.review-row .label {
  width: 80px;
  color: var(--muted);
}
</style>
