import { useMutation, useQuery } from '@tanstack/react-query'

import { apiGet, apiPost } from '../../lib/api'
import type { FileListResponse, SystemCompileRequest, SystemSummary, TaskDetailResponse, TaskStartResponse } from '../../types/api'

export function useSystemSummary() {
  return useQuery({
    queryKey: ['system-summary'],
    queryFn: () => apiGet<SystemSummary>('/system/summary'),
    refetchInterval: 15000,
  })
}

export function useRenderGallery() {
  return useQuery({
    queryKey: ['render-gallery'],
    queryFn: () =>
      apiPost<FileListResponse>('/fs/list', {
        path_key: 'render_outputs_binary_png',
        page: 1,
        page_size: 8,
        suffix: ['.png'],
      }),
    refetchInterval: 15000,
  })
}

export function useSystemCompileTaskDetail(taskId: string | null) {
  return useQuery({
    queryKey: ['system-compile-task', taskId],
    queryFn: () => apiGet<TaskDetailResponse>(`/system/compile/tasks/${taskId}`),
    enabled: Boolean(taskId),
    refetchInterval: (query) => {
      const status = query.state.data?.record.status
      return status === 'success' || status === 'failed' || status === 'cancelled' ? false : 2_500
    },
  })
}

export function useStartSystemCompile() {
  return useMutation({
    mutationFn: (payload: SystemCompileRequest) => apiPost<TaskStartResponse>('/system/compile', payload),
  })
}

export function useStopSystemCompile() {
  return useMutation({
    mutationFn: (taskId: string) => apiPost<TaskStartResponse>('/system/compile/stop', { task_id: taskId }),
  })
}
