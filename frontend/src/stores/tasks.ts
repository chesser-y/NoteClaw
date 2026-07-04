import { defineStore } from 'pinia'
import { listTasks } from '../api/tasks'
import type { TaskRead } from '../api/types'

export const useTaskStore = defineStore('tasks', {
  state: () => ({
    tasks: [] as TaskRead[],
    loading: false,
    error: '',
  }),
  actions: {
    async refresh() {
      this.loading = true
      this.error = ''
      try {
        const data = await listTasks({ limit: 30 })
        this.tasks = data.items
      } catch (error) {
        this.error = error instanceof Error ? error.message : String(error)
      } finally {
        this.loading = false
      }
    },
  },
})
