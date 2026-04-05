export type ModuleKey = 'render' | 'analysis' | 'models' | 'settings'

export type SystemSummary = {
  project_root: string
  mitsuba_dir: string
  mitsuba_exe: string
  mtsutil_exe: string
  mitsuba_exists: boolean
  mtsutil_exists: boolean
  available_modules: string[]
  available_path_keys: string[]
}

export type FileListItem = {
  name: string
  path: string
  size: number
  modified_at: string
  is_dir: boolean
  preview_url?: string | null
}

export type FileListResponse = {
  path_key: string
  resolved_path: string
  page: number
  page_size: number
  total: number
  items: FileListItem[]
}

export type RenderMode = 'brdfs' | 'fullbin' | 'npy'
export type AnalysisImageSet = 'brdfs' | 'fullbin' | 'npy' | 'grids' | 'comparisons'

export type RenderSceneItem = {
  label: string
  path: string
  is_default: boolean
}

export type RenderScenesResponse = {
  default_scene?: string | null
  items: RenderSceneItem[]
}

export type RenderFilesResponse = {
  render_mode: RenderMode
  input_dir: string
  total: number
  items: FileListItem[]
}

export type RenderOutputsResponse = {
  render_mode: RenderMode
  path_key: string
  resolved_path: string
  total: number
  items: FileListItem[]
}

export type RenderBatchRequest = {
  render_mode: RenderMode
  scene_path: string
  selected_files: string[]
  integrator_type: string
  sample_count: number
  auto_convert: boolean
  skip_existing: boolean
  custom_cmd: string | null
}

export type TaskStartResponse = {
  task_id: string
  status: 'pending' | 'running' | 'success' | 'failed' | 'cancelled'
}

export type TaskRecord = {
  task_id: string
  task_type: string
  created_at: string
  started_at?: string | null
  finished_at?: string | null
  status: 'pending' | 'running' | 'success' | 'failed' | 'cancelled'
  progress: number
  message: string
  log_path?: string | null
  result_payload: Record<string, unknown>
}

export type TaskDetailResponse = {
  record: TaskRecord
  logs: string[]
}

export type TaskEvent = {
  task_id: string
  event: 'snapshot' | 'log' | 'done'
  status: 'pending' | 'running' | 'success' | 'failed' | 'cancelled'
  progress: number
  message: string
  result_payload: Record<string, unknown>
}

export type AnalysisImagesResponse = {
  image_set: AnalysisImageSet
  resolved_path: string
  total: number
  items: FileListItem[]
}

export type MetricSummary = {
  psnr: number
  ssim: number
  delta_e: number
}

export type EvaluationPairResult = {
  label: string
  metrics: MetricSummary
}

export type EvaluationResponse = {
  processed_count: number
  skipped: string[]
  comparisons: EvaluationPairResult[]
}

export type EvaluationRequest = {
  gt_set: AnalysisImageSet
  method1_set: AnalysisImageSet
  method2_set: AnalysisImageSet
  selected_materials: string[]
}

export type GridRequest = {
  image_set: AnalysisImageSet
  output_name: string
  show_names: boolean
  cell_width: number
  padding: number
  selected_materials: string[]
}

export type ComparisonColumn = {
  image_set: AnalysisImageSet
  label: string
}

export type ComparisonRequest = {
  columns: ComparisonColumn[]
  selected_materials: string[]
  show_label: boolean
  show_filename: boolean
  output_name: string
}

export type GeneratedImageResponse = {
  item: FileListItem
  processed_count: number
  skipped: string[]
}
