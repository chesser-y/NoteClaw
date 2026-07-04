<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { RefreshCw } from 'lucide-vue-next'
import { getTask } from '../api/tasks'
import { useTaskStore } from '../stores/tasks'
import type { TaskRead } from '../api/types'
import TaskCard from '../components/tasks/TaskCard.vue'
import TaskDetailDrawer from '../components/tasks/TaskDetailDrawer.vue'

const route = useRoute()
const taskStore = useTaskStore()
const selected = ref<TaskRead | null>(null)
const loadingDetail = ref(false)

const inProgress = computed(() => taskStore.tasks.filter((t) => t.status === 'running' || t.status === 'queued'))
const done = computed(() => taskStore.tasks.filter((t) => t.status === 'succeeded' || t.status === 'failed' || t.status === 'cancelled'))

async function openTask(task: TaskRead) {
  selected.value = task
  loadingDetail.value = true
  try {
    const fresh = await getTask(task.id)
    if (selected.value?.id === task.id) selected.value = fresh
  } catch (e) {
    console.error(e)
  } finally {
    loadingDetail.value = false
  }
}

async function refresh() {
  await taskStore.refresh()
  const queryTask = route.query.task as string | undefined
  if (queryTask) {
    const match = taskStore.tasks.find((t) => t.id === queryTask)
    if (match) await openTask(match)
  }
}

onMounted(refresh)
</script>

<template>
  <section class="content-wrap">
    <header class="mb-5 flex items-end justify-between">
      <div>
        <h1 class="section-title">Tasks</h1>
        <p class="muted mt-1 text-sm">复杂任务的进度与结果 · nanobot 跨文档推理会出现在这里</p>
      </div>
      <button class="btn h-8" type="button" @click="refresh">
        <RefreshCw :size="13" />
        刷新
      </button>
    </header>

    <p v-if="taskStore.error" class="mb-5 rounded-lg border border-[#fcd9d4] bg-[#fef3f1] px-3 py-2 text-xs text-[#b42618]">
      {{ taskStore.error }}
    </p>

    <div v-if="inProgress.length" class="mb-7">
      <h2 class="mb-3 text-xs font-semibold uppercase tracking-wide text-[#6b7280]">In progress</h2>
      <div class="space-y-3">
        <TaskCard
          v-for="t in inProgress"
          :key="t.id"
          :task="t"
          @click="openTask(t)"
        />
      </div>
    </div>

    <div v-if="done.length">
      <h2 class="mb-3 text-xs font-semibold uppercase tracking-wide text-[#6b7280]">Recent</h2>
      <div class="space-y-3">
        <TaskCard
          v-for="t in done"
          :key="t.id"
          :task="t"
          @click="openTask(t)"
        />
      </div>
    </div>

    <div v-if="!taskStore.tasks.length && !taskStore.loading" class="surface flex flex-col items-center gap-2 px-4 py-12 text-center">
      <div class="text-sm text-[#111827]">暂无任务</div>
      <p class="text-xs text-[#9ca3af]">在创作台生成 PPT、拖入 PDF，或用 ⌘K 触发 nanobot 任务。</p>
    </div>

    <TaskDetailDrawer :task="selected" :loading="loadingDetail" @close="selected = null" />
  </section>
</template>
