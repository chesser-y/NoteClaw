<script setup lang="ts">
import { onMounted } from 'vue'
import { RefreshCw } from 'lucide-vue-next'
import PageHeader from '../components/PageHeader.vue'
import EmptyState from '../components/EmptyState.vue'
import TaskBadge from '../components/TaskBadge.vue'
import { useTaskStore } from '../stores/tasks'

const taskStore = useTaskStore()

onMounted(() => {
  taskStore.refresh()
})
</script>

<template>
  <section class="content-wrap">
    <PageHeader
      eyebrow="Tasks"
      title="任务中心"
      description="入库、OCR、多模态理解、PPTX、生图、nanobot 检索等耗时流程都会以 task 的形式追踪。"
    />

    <div class="mb-5 flex justify-end">
      <button class="btn" type="button" @click="taskStore.refresh">
        <RefreshCw :size="16" />
        刷新任务
      </button>
    </div>

    <div v-if="taskStore.error" class="mb-6 border border-[#70433b] bg-[#261716] p-4 text-sm text-[#f0b8ad]">
      {{ taskStore.error }}
    </div>

    <div v-if="taskStore.tasks.length" class="space-y-3">
      <article v-for="task in taskStore.tasks" :key="task.id" class="surface grid gap-4 p-5 md:grid-cols-[1fr_auto]">
        <div>
          <div class="mb-2 flex flex-wrap items-center gap-3">
            <h3 class="text-lg text-white">{{ task.type }}</h3>
            <TaskBadge :status="task.status" />
          </div>
          <p class="mb-3 text-sm text-[#9aa3a0]">{{ task.message || '等待任务消息' }}</p>
          <div class="h-2 w-full bg-[#202525]">
            <div class="h-full bg-[#d9d2bf]" :style="{ width: `${Math.round(task.progress * 100)}%` }"></div>
          </div>
        </div>
        <div class="text-right text-sm text-[#8f9996]">
          <div>{{ task.id }}</div>
          <div class="mt-2">{{ Math.round(task.progress * 100) }}%</div>
        </div>
      </article>
    </div>

    <EmptyState
      v-else
      title="暂无任务"
      description="创建入库、生成或 nanobot 搜集任务后，这里会展示任务进度和结果。"
    />
  </section>
</template>
