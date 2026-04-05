import { useMutation, useQuery } from '@tanstack/react-query'

import { apiGet, apiPost } from '../../lib/api'
import type {
  AnalysisImageSet,
  AnalysisImagesResponse,
  ComparisonRequest,
  EvaluationRequest,
  EvaluationResponse,
  GeneratedImageResponse,
  GridRequest,
} from '../../types/api'


export function useAnalysisImages(imageSet: AnalysisImageSet, search: string) {
  return useQuery({
    queryKey: ['analysis-images', imageSet, search],
    queryFn: () =>
      apiGet<AnalysisImagesResponse>(
        `/analysis/images?image_set=${imageSet}&page=1&page_size=48&search=${encodeURIComponent(search)}`,
      ),
  })
}


export function useEvaluateAnalysis() {
  return useMutation({
    mutationFn: (payload: EvaluationRequest) => apiPost<EvaluationResponse>('/analysis/evaluate', payload),
  })
}


export function useGenerateGrid() {
  return useMutation({
    mutationFn: (payload: GridRequest) => apiPost<GeneratedImageResponse>('/analysis/grid', payload),
  })
}


export function useGenerateComparison() {
  return useMutation({
    mutationFn: (payload: ComparisonRequest) => apiPost<GeneratedImageResponse>('/analysis/comparison', payload),
  })
}
