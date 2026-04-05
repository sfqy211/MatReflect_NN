import { useMutation, useQuery } from '@tanstack/react-query'

import { apiGet, apiPost } from '../../lib/api'
import type {
  FileListResponse,
  HyperDecodeRequest,
  HyperExtractRequest,
  HyperTrainRunRequest,
  NeuralKerasTrainRequest,
  NeuralPytorchTrainRequest,
  TaskDetailResponse,
  TaskStartResponse,
  TrainModelsResponse,
  TrainProjectVariant,
  TrainRunsResponse,
} from '../../types/api'


export function useTrainModels() {
  return useQuery({
    queryKey: ['train-models'],
    queryFn: () => apiGet<TrainModelsResponse>('/train/models'),
    staleTime: 60_000,
  })
}


export function useTrainRuns(projectVariant: TrainProjectVariant | null) {
  return useQuery({
    queryKey: ['train-runs', projectVariant],
    queryFn: () =>
      apiGet<TrainRunsResponse>(
        projectVariant ? `/train/runs?project_variant=${projectVariant}` : '/train/runs',
      ),
    staleTime: 15_000,
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


export function useExtractedPtFiles(projectVariant: TrainProjectVariant, search: string) {
  const pathKey =
    projectVariant === 'hyperbrdf' ? 'train_hyper_extracted_pts' : 'train_decoupled_extracted_pts'
  return useQuery({
    queryKey: ['train-extracted-pts', projectVariant, search],
    queryFn: () =>
      apiPost<FileListResponse>('/fs/list', {
        path_key: pathKey,
        page: 1,
        page_size: 200,
        suffix: ['.pt'],
        search,
      }),
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
