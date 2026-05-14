import type { TrainModelItem } from '../../types/api'

export const DEFAULT_FULLBIN_OUTPUT = 'data/inputs/fullbin'

export function normalizeBinaryName(name: string) {
  return name.replace(/\.binary$/i, '')
}

export function getDefaultPath(model: TrainModelItem | null, field: string, fallback: string) {
  return model?.default_paths[field] ?? fallback
}

export function getRuntimeValue(model: TrainModelItem | null, field: string, fallback = '') {
  return model?.runtime[field] ?? fallback
}
