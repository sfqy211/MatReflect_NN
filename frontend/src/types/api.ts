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
  compile_defaults: SystemCompileDefaults
  settings: SystemSettings
  checks: SystemDependencyCheck[]
  env_checks: SystemVirtualEnvCheck[]
}

export type SystemCompileDefaults = {
  preset_label: string
  compile_cmd: string
  conda_env: string
  vcvarsall_path: string
  work_dir: string
  dep_bin: string
  dep_lib: string
  dependency_paths: string[]
}

export type SystemDependencySetting = {
  id: string
  label: string
  path: string
}

export type SystemDependencyCheck = {
  id: string
  label: string
  path: string
  exists: boolean
  is_dir: boolean
  is_file: boolean
  status: string
  message: string
}

export type SystemVirtualEnvSetting = {
  id: string
  label: string
  manager: string
  env_name: string
  role: string
}

export type SystemVirtualEnvCheck = {
  id: string
  label: string
  manager: string
  env_name: string
  role: string
  exists: boolean
  status: string
  message: string
  prefix: string
}

export type SystemSettings = {
  project_root: string
  mitsuba_exe: string
  mtsutil_exe: string
  binary_input_dir: string
  npy_input_dir: string
  fullbin_input_dir: string
  brdf_output_dir: string
  npy_output_dir: string
  fullbin_output_dir: string
  grids_output_dir: string
  comparisons_output_dir: string
  preset_label: string
  conda_env: string
  compile_cmd: string
  vcvarsall_path: string
  work_dir: string
  dependencies: SystemDependencySetting[]
  virtual_envs: SystemVirtualEnvSetting[]
}

export type SystemSettingsRequest = SystemSettings

export type SystemSettingsResponse = {
  settings: SystemSettings
  checks: SystemDependencyCheck[]
  env_checks: SystemVirtualEnvCheck[]
}

export type SystemCompileRequest = {
  compile_cmd: string
  conda_env: string
  compile_label: string
  vcvarsall_path: string
  work_dir: string
  dependency_paths: string[]
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
export type RenderSourceModel = 'gt' | 'neural' | 'hyperbrdf'
export type RenderReconstructModel = 'neural' | 'hyperbrdf' | string
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

export type RenderReconstructRequest = {
  model_key: RenderReconstructModel
  checkpoint_path: string
  merl_dir: string
  output_dir: string
  selected_materials: string[]
  conda_env: string
  dataset: TrainDataset
  sparse_samples: number
  cuda_device: string
  neural_device: 'cpu' | 'cuda'
  neural_epochs: number
  scene_path: string
  integrator_type: string
  sample_count: number
  auto_convert: boolean
  skip_existing: boolean
  custom_cmd: string | null
  render_after_reconstruct: boolean
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

export type DeleteImageRequest = {
  image_paths: string[]
  delete_matching_exr: boolean
}

export type DeleteImageResponse = {
  deleted: string[]
  missing: string[]
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
  gt_dir: string
  method1_dir: string
  method2_dir: string
  gt_label: string
  method1_label: string
  method2_label: string
  selected_materials: string[]
}

export type GridRequest = {
  image_set: AnalysisImageSet
  source_dir: string
  output_dir: string
  output_name: string
  show_names: boolean
  cell_width: number
  padding: number
  selected_materials: string[]
}

export type ComparisonColumn = {
  image_set?: AnalysisImageSet | null
  directory: string
  label: string
}

export type ComparisonRequest = {
  columns: ComparisonColumn[]
  selected_materials: string[]
  show_label: boolean
  show_filename: boolean
  output_dir: string
  output_name: string
}

export type GeneratedImageResponse = {
  item: FileListItem
  processed_count: number
  skipped: string[]
}

export type TrainProjectVariant = string
export type TrainDataset = 'MERL' | 'EPFL'
export type NeuralTrainEngine = 'pytorch' | 'keras'
export type TrainModelCategory = 'neural' | 'hyper' | 'custom'
export type TrainModelAdapter = 'neural-pytorch' | 'neural-keras' | 'hyper-family' | 'custom-cli'

export type ModelParameter = {
  key: string
  label: string
  type: 'int' | 'float' | 'str' | 'bool' | 'select'
  default: unknown
  min?: number | null
  max?: number | null
  options?: string[] | null
}

export type TrainModelItem = {
  key: string
  label: string
  category: TrainModelCategory
  adapter: TrainModelAdapter
  built_in: boolean
  description: string
  supports_training: boolean
  supports_extract: boolean
  supports_decode: boolean
  supports_runs: boolean
  supports_reconstruction: boolean
  model_dir: string
  requirements_path: string
  commands_doc: string
  parameters: ModelParameter[]
  render_modes: string[]
  default_paths: Record<string, string>
  runtime: Record<string, string>
  adapter_options: Record<string, unknown>
}

export type TrainModelsResponse = {
  items: TrainModelItem[]
}

export type TrainRunSummary = {
  model_key: string
  label: string
  adapter: TrainModelAdapter
  run_name: string
  run_dir: string
  checkpoint_path: string
  dataset: string
  completed_epochs: number
  updated_at: string
  has_checkpoint: boolean
  args: Record<string, unknown>
}

export type TrainRunsResponse = {
  total: number
  items: TrainRunSummary[]
}

export type NeuralPytorchTrainRequest = {
  model_key: string
  merl_dir: string
  selected_materials: string[]
  epochs: number
  output_dir: string
  device: 'cpu' | 'cuda'
}

export type NeuralKerasTrainRequest = {
  model_key: string
  merl_dir: string
  selected_materials: string[]
  cuda_device: string
  h5_output_dir: string
  npy_output_dir: string
}

export type NeuralH5ConvertRequest = {
  model_key: string
  h5_dir: string
  selected_h5_files: string[]
  npy_output_dir: string
  conda_env: string
}

export type HyperTrainRunRequest = {
  model_key: string
  merl_dir: string
  output_dir: string
  conda_env: string
  dataset: TrainDataset
  epochs: number
  sparse_samples: number
  kl_weight: number
  fw_weight: number
  lr: number
  keepon: boolean
  train_subset: number
  train_seed: number
}

export type HyperExtractRequest = {
  model_key: string
  merl_dir: string
  selected_materials: string[]
  model_path: string
  output_dir: string
  conda_env: string
  dataset: TrainDataset
  sparse_samples: number
}

export type HyperDecodeRequest = {
  model_key: string
  pt_dir: string
  selected_pts: string[]
  output_dir: string
  conda_env: string
  dataset: TrainDataset
  cuda_device: string
}

export type ReconstructRequest = {
  model_key: string
  checkpoint_path: string
  merl_dir: string
  output_dir: string
  selected_materials: string[]
  conda_env: string
  dataset: TrainDataset
  sparse_samples: number
  cuda_device: string
  neural_device: 'cpu' | 'cuda'
  neural_epochs: number
  scene_path: string
  integrator_type: string
  sample_count: number
  auto_convert: boolean
  skip_existing: boolean
  custom_cmd: string | null
  render_after_reconstruct: boolean
}

export type ModelImportRequest = {
  source_dir: string
  model_key: string
  label: string
  description: string
  commands_doc_filename: string
  train_script: string
  train_args_template: string
  reconstruct_script: string
  reconstruct_args_template: string
  supports_training: boolean
  supports_reconstruction: boolean
  supports_extract: boolean
  supports_decode: boolean
  supports_runs: boolean
  render_modes: string[]
  parameters: ModelParameter[]
}

export type ModelImportResponse = {
  model_key: string
  model_dir: string
  requirements_path: string
  commands_doc: string
  conda_env: string
  status: string
}

export type ModelEnvStatusResponse = {
  model_key: string
  conda_env: string
  env_exists: boolean
  env_prefix: string
}
