<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useTaskStore } from '../stores/tasks'
import type { TaskRead, TaskStatus } from '../api/types'
import TaskDetailDrawer from '../components/tasks/TaskDetailDrawer.vue'

const store = useTaskStore()
const selected = ref<TaskRead | null>(null)

onMounted(() => store.refresh())

const buckets = computed(() => {
  const queued: TaskRead[] = []
  const inProgress: TaskRead[] = []
  const done: TaskRead[] = []
  for (const t of store.tasks) {
    if (t.status === 'queued') queued.push(t)
    else if (t.status === 'running') inProgress.push(t)
    else if (t.status === 'succeeded' || t.status === 'failed') done.push(t)
  }
  return {
    queued,
    inProgress,
    review: [] as TaskRead[],
    done,
  }
})

const statusRingClass = (status: TaskStatus) => {
  if (status === 'succeeded') return 'blue'
  if (status === 'failed') return 'gray'
  return ''
}

const shortId = (id: string) => id.slice(0, 12)

const titleFromTask = (t: TaskRead) => {
  if (t.message && t.message.length > 4) return t.message
  return t.type
}

const progressLabel = (t: TaskRead) => `${Math.round(t.progress * 100)}%`

function openTask(t: TaskRead) {
  selected.value = t
}
</script>

<template>
  <section class="tasks-view">
    <header class="topbar tight">
      <span>Tasks</span>
      <span class="spacer"></span>
    </header>

    <div class="kanban">
      <div class="kanban-col">
        <div class="col-title">
          <span class="status-ring gray"></span>
          Queued
          <span class="count">{{ buckets.queued.length }}</span>
          <span class="plus">+</span>
        </div>
        <div
          v-for="t in buckets.queued"
          :key="t.id"
          class="task-card"
          @click="openTask(t)"
        >
          <div class="task-id">{{ shortId(t.id) }}</div>
          <div class="task-title">
            <span class="status-ring gray"></span>
            {{ titleFromTask(t) }}
          </div>
          <div class="task-tags">
            <span class="pill square">{{ t.type }}</span>
            <span class="pill square"><span class="small-dot" style="color: var(--muted);"></span>{{ progressLabel(t) }}</span>
          </div>
        </div>
        <div v-if="!buckets.queued.length" class="muted" style="font-size: 12px; padding: 12px;">No items</div>
      </div>

      <div class="kanban-col">
        <div class="col-title">
          <span class="status-ring"></span>
          In progress
          <span class="count">{{ buckets.inProgress.length }}</span>
          <span class="plus">+</span>
        </div>
        <div
          v-for="t in buckets.inProgress"
          :key="t.id"
          class="task-card"
          @click="openTask(t)"
        >
          <span class="pill right-chip">Working... <span class="small-dot" style="color: var(--orange);"></span></span>
          <div class="task-id">{{ shortId(t.id) }}</div>
          <div class="task-title">
            <span class="status-ring"></span>
            {{ titleFromTask(t) }}
          </div>
          <div class="task-tags">
            <span class="pill square">{{ t.type }}</span>
            <span class="pill square"><span class="small-dot" style="color: var(--orange);"></span>{{ progressLabel(t) }}</span>
          </div>
        </div>
        <div v-if="!buckets.inProgress.length" class="muted" style="font-size: 12px; padding: 12px;">No items</div>
      </div>

      <div class="kanban-col">
        <div class="col-title">
          <span class="status-ring" style="border-color: var(--orange);"></span>
          Need review
          <span class="count">{{ buckets.review.length }}</span>
          <span class="plus">+</span>
        </div>
        <div
          v-for="t in buckets.review"
          :key="t.id"
          class="task-card"
          @click="openTask(t)"
        >
          <span class="pill right-chip">Waiting <span class="small-dot" style="color: var(--orange);"></span></span>
          <div class="task-id">{{ shortId(t.id) }}</div>
          <div class="task-title">
            <span class="status-ring"></span>
            {{ titleFromTask(t) }}
          </div>
          <div class="task-tags">
            <span class="pill square">{{ t.type }}</span>
            <span class="pill square"><span class="small-dot" style="color: var(--blue);"></span>Review</span>
          </div>
        </div>
        <div v-if="!buckets.review.length" class="muted" style="font-size: 12px; padding: 12px;">No items</div>
      </div>

      <div class="kanban-col">
        <div class="col-title">
          <span class="status-ring green"></span>
          Done
          <span class="count">{{ buckets.done.length }}</span>
          <span class="plus">+</span>
        </div>
        <div
          v-for="t in buckets.done"
          :key="t.id"
          class="task-card"
          @click="openTask(t)"
        >
          <div class="task-id">{{ shortId(t.id) }}</div>
          <div class="task-title">
            <span class="status-ring" :class="statusRingClass(t.status)">✓</span>
            {{ titleFromTask(t) }}
          </div>
          <div class="task-tags">
            <span class="pill square">{{ t.type }}</span>
            <span class="pill square"><span class="small-dot" style="color: var(--green);"></span>{{ t.status }}</span>
          </div>
        </div>
        <div v-if="!buckets.done.length" class="muted" style="font-size: 12px; padding: 12px;">No items</div>
      </div>
    </div>

    <TaskDetailDrawer v-if="selected" :task="selected" :loading="false" @close="selected = null" />
  </section>
</template>

<style scoped>
.tasks-view {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}
</style>
