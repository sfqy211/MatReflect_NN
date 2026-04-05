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
}

export type FileListResponse = {
  path_key: string
  resolved_path: string
  page: number
  page_size: number
  total: number
  items: FileListItem[]
}
