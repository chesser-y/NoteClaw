<script setup lang="ts">
import { computed } from 'vue'
import { Check, Circle, Loader2, AlertCircle } from 'lucide-vue-next'
import type { TaskRead } from '../../api/types'
import Drawer from '../common/Drawer.vue'
import SourceList from '../common/SourceList.vue'

const props = defineProps<{
  task: TaskRead | null
  loading: boolean
}>()

defineEmits<{ close: [] }>()

const steps = computed(() => {
  if (!props.task) return [] as { label: string; done: boolean }[]
  const type = props.task.type.toLowerCase()
  let labels: string[] = []
  if (type.includes('ingest') || type.includes('ocr')) {
    labels = ['找到相关资料', '读取关键来源', '生成摘要', '入库完成']
  } else if (type.includes('generate') || type.includes('ppt')) {
    labels = ['找到相关资料', '提取要点', '生成对比', '等待确认']
  } else if (type.includes('harness') || type.includes('nanobot')) {
    labels = ['找到相关资料', '读取关键来源', '生成对比表', '生成最终建议']
  } else {
    labels = ['准备', '执行中', '完成']
  }
  let completed = 0
  if (props.task.status === 'succeeded') completed = labels.length
  else if (props.task.status === 'queued') completed = 0
  else if (props.task.status === 'failed' || props.task.status === 'cancelled') completed = -1
  else completed = Math.min(labels.length - 1, Math.max(0, Math.floor(props.task.progress * labels.length)))
  return labels.map((label, idx) => ({ label, done: idx < completed }))
})

const citations = computed(() => {
  const result = props.task?.result as { citations?: unknown[] } | null
  return Array.isArray(result?.citations) ? (result!.citations as any[]) : []
})
</script>

<template>
  <Drawer :open="!!task" title="Task detail" width="460px" @close="$emit('close')">
    <div v-if="!task" class="py-10 text-center text-sm text-[#73747a]">未选中任务</div>
    <div v-else class="space-y-5">
      <section>
        <div class="mb-1 text-xs text-[#73747a]">目标</div>
        <div class="text-[15px] font-semibold text-[#f0f1f2]">{{ task.type }}</div>
        <p class="mt-1 text-xs text-[#929399]">{{ task.message || '正在执行任务…' }}</p>
        <div class="mt-2 flex items-center gap-2 text-[11px] text-[#73747a]">
          <span>{{ task.id }}</span>
          <span>·</span>
          <span>{{ task.status }}</span>
        </div>
      </section>

      <section>
        <div class="mb-2 text-xs text-[#73747a]">进度</div>
        <ul class="space-y-1.5">
          <li v-for="(step, idx) in steps" :key="idx" class="flex items-center gap-2 text-sm">
            <Check v-if="step.done" :size="14" class="text-[#00c853]" />
            <Loader2 v-else-if="task.status === 'running' && idx === steps.findIndex(s => !s.done)" :size="14" class="animate-spin text-[#626be6]" />
            <Circle v-else :size="14" class="text-[#4a4b50]" />
            <span :class="step.done ? 'text-[#f0f1f2]' : 'text-[#929399]'">{{ step.label }}</span>
          </li>
        </ul>
        <div v-if="task.status === 'failed'" class="mt-3 flex items-center gap-2 rounded-lg border border-[#5a2520] bg-[#2a1614] px-3 py-2 text-xs text-[#f0b8ad]">
          <AlertCircle :size="13" />
          {{ task.error || '任务执行失败' }}
        </div>
      </section>

      <section>
        <div class="mb-2 text-xs text-[#73747a]">使用的资料</div>
        <SourceList v-if="citations.length" :sources="citations" />
        <p v-else class="text-xs text-[#73747a]">该任务尚未关联资料。</p>
      </section>

      <section v-if="task.result && Object.keys(task.result).length">
        <div class="mb-2 text-xs text-[#73747a]">Result</div>
        <pre class="max-h-[200px] overflow-auto rounded-lg border border-[#24262a] bg-[#151618] p-3 text-[11px] text-[#f0f1f2]">{{ JSON.stringify(task.result, null, 2) }}</pre>
      </section>
    </div>
  </Drawer>
</template>
