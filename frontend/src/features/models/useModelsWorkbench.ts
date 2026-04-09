import { useMutation, useQuery } from '@tanstack/react-query'

import { apiDelete, apiGet, apiPost } from '../../lib/api'
import type {
  FileListResponse,
  HyperDecodeRequest,
  HyperExtractRequest,
  HyperTrainRunRequest,
  NeuralH5ConvertRequest,
  NeuralKerasTrainRequest,
  NeuralPytorchTrainRequest,
  TaskDetailResponse,
  TaskStartResponse,
  TrainModelCreateRequest,
  TrainModelDeleteResponse,
  TrainModelMutationResponse,
  TrainModelsResponse,
  TrainRunsResponse,
} from '../../types/api'


export function useTrainModels() {
  return useQuery({
    queryKey: ['train-models'],
    queryFn: () => apiGet<TrainModelsResponse>('/train/models'),
    staleTime: 60_000,
  })
}


export function useTrainRuns(modelKey: string | null, enabled = true) {
  return useQuery({
    queryKey: ['train-runs', modelKey],
    queryFn: () => apiGet<TrainRunsResponse>(`/train/runs?model_key=${encodeURIComponent(modelKey ?? '')}`),
    staleTime: 15_000,
    enabled: enabled && Boolean(modelKey),
  })
}


export function useTrainTaskDetail(taskId: string | null) {
  return useQuery({
    queryKey: ['train-task-detail', taskId],
    queryFn: () => apiGet<TaskDetailResponse>(`/train/tasks/${taskId}`),
    enabled: Boolean(taskId),
    refetchInterval: (query) => {
      const status = query.state.data?.record.status
      return status === 'success' || status === 'failed' || status === 'cancelled' ? false : 2_500
    },
  })
}


export function useMaterialsDirectory(search: string) {
  return useQuery({
    queryKey: ['train-materials', search],
    queryFn: () =>
      apiPost<FileListResponse>('/fs/list', {
        path_key: 'inputs_binary',
        page: 1,
        page_size: 200,
        suffix: ['.binary'],
        search,
      }),
  })
}


export function useWorkspaceFiles(directory: string, suffix: string[], search: string, enabled = true) {
  return useQuery({
    queryKey: ['workspace-files', directory, suffix.join(','), search],
    queryFn: () =>
      apiPost<FileListResponse>('/fs/list-path', {
        directory,
        page: 1,
        page_size: 200,
        suffix,
        search,
      }),
    enabled: enabled && Boolean(directory.trim()),
  })
}


export function useCreateTrainModel() {
  return useMutation({
    mutationFn: (payload: TrainModelCreateRequest) =>
      apiPost<TrainModelMutationResponse>('/train/models', payload),
  })
}


export function useDeleteTrainModel() {
  return useMutation({
    mutationFn: (modelKey: string) =>
      apiDelete<TrainModelDeleteResponse>(`/train/models/${encodeURIComponent(modelKey)}`),
  })
}


export function useStartNeuralPytorch() {
  return useMutation({
    mutationFn: (payload: NeuralPytorchTrainRequest) =>
      apiPost<TaskStartResponse>('/train/neural/pytorch', payload),
  })
}


export function useStartNeuralKeras() {
  return useMutation({
    mutationFn: (payload: NeuralKerasTrainRequest) =>
      apiPost<TaskStartResponse>('/train/neural/keras', payload),
  })
}


export function useStartNeuralH5Convert() {
  return useMutation({
    mutationFn: (payload: NeuralH5ConvertRequest) =>
      apiPost<TaskStartResponse>('/train/neural/keras/convert', payload),
  })
}


export function useStartHyperRun() {
  return useMutation({
    mutationFn: (payload: HyperTrainRunRequest) =>
      apiPost<TaskStartResponse>('/train/hyper/run', payload),
  })
}


export function useStartHyperExtract() {
  return useMutation({
    mutationFn: (payload: HyperExtractRequest) =>
      apiPost<TaskStartResponse>('/train/hyper/extract', payload),
  })
}


export function useStartHyperDecode() {
  return useMutation({
    mutationFn: (payload: HyperDecodeRequest) =>
      apiPost<TaskStartResponse>('/train/hyper/decode', payload),
  })
}


export function useStopTrainTask() {
  return useMutation({
    mutationFn: (taskId: string) => apiPost<TaskStartResponse>('/train/stop', { task_id: taskId }),
  })
}
