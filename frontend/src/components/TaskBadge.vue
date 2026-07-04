<script setup lang="ts">
import type { TaskStatus } from '../api/types'

const props = defineProps<{
  status: TaskStatus | string
}>()

const statusLabel: Record<string, string> = {
  queued: '排队中',
  running: '运行中',
  succeeded: '已完成',
  failed: '失败',
  cancelled: '已取消',
}
</script>

<template>
  <span class="chip">
    <span
      class="h-2 w-2 rounded-full"
      :class="{
        'bg-[#d9d2bf]': props.status === 'queued',
        'bg-[#87bba2]': props.status === 'running',
        'bg-[#9ed1ac]': props.status === 'succeeded',
        'bg-[#e08f7f]': props.status === 'failed',
        'bg-[#8f9996]': props.status === 'cancelled',
      }"
    ></span>
    {{ statusLabel[props.status] ?? props.status }}
  </span>
</template>
