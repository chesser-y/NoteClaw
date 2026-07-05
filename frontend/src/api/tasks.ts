import { apiFetch } from './http'
import type { TaskListResponse, TaskRead, TaskStatus } from './types'

export function getTask(taskId: string) {
  return apiFetch<TaskRead>(`/tasks/${taskId}`)
}

export function listTasks(params: { status?: TaskStatus | ''; limit?: number; offset?: number } = {}) {
  const query = new URLSearchParams()
  if (params.status) query.set('status', params.status)
  query.set('limit', String(params.limit ?? 20))
  query.set('offset', String(params.offset ?? 0))
  return apiFetch<TaskListResponse>(`/tasks?${query.toString()}`)
}
