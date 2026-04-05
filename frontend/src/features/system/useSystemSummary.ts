import { useQuery } from '@tanstack/react-query'

import { apiGet, apiPost } from '../../lib/api'
import type { FileListResponse, SystemSummary } from '../../types/api'

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
