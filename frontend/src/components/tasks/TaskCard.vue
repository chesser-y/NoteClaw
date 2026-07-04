<script setup lang="ts">
import { computed } from 'vue'
import { Check, Loader2, AlertCircle, ArrowRight } from 'lucide-vue-next'
import type { TaskRead } from '../../api/types'

const props = defineProps<{ task: TaskRead }>()

const statusLabel = computed(() => {
  switch (props.task.status) {
    case 'queued':
      return { text: 'Queued', kind: 'idle' as const }
    case 'running':
      return { text: 'In progress', kind: 'warn' as const }
    case 'succeeded':
      return { text: 'Done', kind: 'success' as const }
    case 'failed':
      return { text: 'Failed', kind: 'error' as const }
    case 'cancelled':
      return { text: 'Cancelled', kind: 'idle' as const }
    default:
      return { text: props.task.status, kind: 'idle' as const }
  }
})

const subLabel = computed(() => {
  if (props.task.status === 'running' && props.task.message) return props.task.message
  if (props.task.status === 'succeeded') return relativeTime(props.task.updated_at)
  if (props.task.status === 'failed') return props.task.error ?? '任务失败'
  return props.task.message || ''
})

function relativeTime(iso: string): string {
  const now = new Date()
  const then = new Date(iso)
  const seconds = Math.max(1, Math.floor((now.getTime() - then.getTime()) / 1000))
  if (seconds < 60) return `${seconds} seconds ago`
  if (seconds < 3600) return `${Math.floor(seconds / 60)} minutes ago`
  if (seconds < 86400) return `${Math.floor(seconds / 3600)} hours ago`
  return `${Math.floor(seconds / 86400)} days ago`
}

const steps = computed(() => {
  const type = props.task.type.toLowerCase()
  if (type.includes('ingest') || type.includes('ocr')) {
    return ['读取来源', '抽取内容', '生成摘要', '入库']
  }
  if (type.includes('generate') || type.includes('ppt') || type.includes('slide')) {
    return ['找到相关资料', '提取要点', '生成对比', '等待确认']
  }
  if (type.includes('harness') || type.includes('nanobot')) {
    return ['检索', '读取关键来源', '对比分析', '生成建议']
  }
  return ['queued', 'running', 'succeeded']
})

const currentStep = computed(() => {
  if (props.task.status === 'queued') return -1
  if (props.task.status === 'succeeded') return steps.value.length - 1
  if (props.task.status === 'failed' || props.task.status === 'cancelled') return -2
  return Math.min(steps.value.length - 1, Math.max(0, Math.floor(props.task.progress * steps.value.length)))
})
</script>

<template>
  <article
    class="card card-hover cursor-pointer py-4"
    @click="$emit('click')"
  >
    <header class="flex items-start justify-between gap-3">
      <div class="min-w-0 flex-1">
        <h3 class="truncate text-[15px] font-semibold text-[#f0f1f2]">{{ task.type }}</h3>
        <div class="mt-0.5 flex items-center gap-2 text-xs text-[#929399]">
          <span
            class="status-dot"
            :class="{
              'status-dot--warn': statusLabel.kind === 'warn',
              'status-dot--idle': statusLabel.kind === 'idle',
            }"
            v-if="statusLabel.kind !== 'error'"
          ></span>
          <AlertCircle v-else :size="11" class="text-[#f0b8ad]" />
          <span>{{ statusLabel.text }}</span>
          <span v-if="subLabel">· {{ subLabel }}</span>
        </div>
      </div>
      <div v-if="task.status === 'running'" class="text-xs text-[#73747a]">
        {{ Math.round(task.progress * 100) }}%
      </div>
      <Loader2 v-if="task.status === 'running'" :size="14" class="animate-spin text-[#626be6]" />
      <Check v-else-if="task.status === 'succeeded'" :size="14" class="text-[#00c853]" />
    </header>

    <div v-if="task.status === 'running' || task.status === 'queued'" class="mt-3 flex flex-wrap items-center gap-1 text-[11px]">
      <template v-for="(step, idx) in steps" :key="step">
        <span
          class="rounded-full px-2 py-0.5"
          :class="
            idx <= currentStep
              ? 'bg-[rgba(98, 107, 230, 0.16)] text-[#626be6]'
              : 'bg-[#1b1c1e] text-[#73747a]'
          "
        >
          {{ step }}
        </span>
        <ArrowRight v-if="idx < steps.length - 1" :size="10" class="text-[#4a4b50]" />
      </template>
    </div>

    <div v-else-if="task.status === 'succeeded'" class="mt-3 h-1 w-full overflow-hidden rounded-full bg-[#1b1c1e]">
      <div class="h-full w-full bg-[#00c853]"></div>
    </div>
  </article>
</template>
