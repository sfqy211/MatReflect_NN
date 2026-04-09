import { useMutation, useQuery } from '@tanstack/react-query'

import { apiGet, apiPost } from '../../lib/api'
import type {
  RenderBatchRequest,
  RenderFilesResponse,
  RenderMode,
  RenderOutputsResponse,
  RenderReconstructRequest,
  RenderScenesResponse,
  TaskDetailResponse,
  TaskStartResponse,
} from '../../types/api'


export function useRenderScenes(renderMode: RenderMode) {
  return useQuery({
    queryKey: ['render-scenes', renderMode],
    queryFn: () => apiGet<RenderScenesResponse>(`/render/scenes?render_mode=${renderMode}`),
    staleTime: 60_000,
  })
}


export function useRenderInputs(renderMode: RenderMode, search: string) {
  return useQuery({
    queryKey: ['render-inputs', renderMode, search],
    queryFn: () =>
      apiGet<RenderFilesResponse>(
        `/render/files?render_mode=${renderMode}&page=1&page_size=200&search=${encodeURIComponent(search)}`,
      ),
  })
}


export function useRenderOutputs(renderMode: RenderMode) {
  return useQuery({
    queryKey: ['render-outputs', renderMode],
    queryFn: () =>
      apiGet<RenderOutputsResponse>(`/render/outputs?render_mode=${renderMode}&page=1&page_size=24`),
    refetchInterval: 15_000,
  })
}


export function useRenderTaskDetail(taskId: string | null) {
  return useQuery({
    queryKey: ['render-task-detail', taskId],
    queryFn: () => apiGet<TaskDetailResponse>(`/render/tasks/${taskId}`),
    enabled: Boolean(taskId),
    refetchInterval: (query) => {
      const status = query.state.data?.record.status
      return status === 'success' || status === 'failed' || status === 'cancelled' ? false : 2_500
    },
  })
}


export function useStartRender() {
  return useMutation({
    mutationFn: (payload: RenderBatchRequest) => apiPost<TaskStartResponse>('/render/batch', payload),
  })
}


export function useStartReconstruct() {
  return useMutation({
    mutationFn: (payload: RenderReconstructRequest) =>
      apiPost<TaskStartResponse>('/render/reconstruct', payload),
  })
}


export function useStopRender() {
  return useMutation({
    mutationFn: (taskId: string) => apiPost<TaskStartResponse>('/render/stop', { task_id: taskId }),
  })
}


export function useConvertOutputs() {
  return useMutation({
    mutationFn: (renderMode: RenderMode) => apiPost<TaskStartResponse>('/render/convert', { render_mode: renderMode, filenames: [] }),
  })
}
