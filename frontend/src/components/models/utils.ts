import type {
  BackendOperationDef,
  OperationDef,
  OperationField,
  OperationFieldType,
  TrainModelItem,
} from '../../types/api'

export const DEFAULT_FULLBIN_OUTPUT = 'data/render-input/hyperbrdf'

/** 转义字符串中的正则特殊字符 */
export function escapeRegex(str: string): string {
  return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

export function normalizeBinaryName(name: string) {
  return name.replace(/\.binary$/i, '')
}

export function getDefaultPath(model: TrainModelItem | null, field: string, fallback: string) {
  return model?.default_paths[field] ?? fallback
}

export function getRuntimeValue(model: TrainModelItem | null, field: string, fallback = '') {
  return model?.runtime[field] ?? fallback
}

// ── Helper: 从 request.* 变量名提取字段 key ──
function extractSourceKey(source: string): string {
  if (!source) return ''
  const m = source.match(/^request\.(.+)$/)
  if (m) {
    // 某些写法如 "request.neural_epochs" 保留原始 key
    return m[1]
  }
  // 也可能是 "item.path" 或其他来源，忽略
  return ''
}

function guessFieldType(key: string, defaultValue: unknown): OperationField['type'] {
  if (defaultValue !== undefined && defaultValue !== null) {
    if (typeof defaultValue === 'boolean') return 'bool'
    if (typeof defaultValue === 'number') return Number.isInteger(defaultValue) ? 'int' : 'float'
  }
  // 按命名规则猜测
  if (/epoch|count|subset|seed|samples|num$|epochs/i.test(key)) return 'int'
  if (/weight|lr|rate|kl|fw|k[0-9]|threshold/i.test(key)) return 'float'
  if (/device|mode|type|engine/i.test(key)) return 'select'
  if (/keepon|render|skip|auto|merge/.test(key)) return 'bool'
  if (/dir|path|folder|directory/i.test(key)) return 'path'
  return 'str'
}

function guessFieldLabel(key: string): string {
  const labels: Record<string, string> = {
    merl_dir: '材质目录',
    output_dir: '输出目录',
    h5_output_dir: 'H5 输出目录',
    nbrdf_render_dir: 'Neural-BRDF 渲染目录',
    checkpoint: 'Checkpoint 路径',
    model_path: '模型路径',
    conda_env: 'Conda 环境',
    cuda_device: 'CUDA 设备',
    neural_device: '训练设备',
    neural_epochs: '重建轮数',
    selected_materials: '材质选择',
    selected_h5_files: 'Keras 权重文件',
    selected_pts: '潜向量文件',
    epochs: '训练轮数',
    sparse_samples: '稀疏采样点数',
    kl_weight: 'KL 权重',
    fw_weight: 'FW 权重',
    lr: '学习率',
    train_subset: '训练材质数',
    train_seed: '随机种子',
    keepon: '继续训练',
    dataset: '数据集',
    pt_dir: '潜向量目录',
    extract_dir: '提取输出目录',
    extract_output_dir: 'PT 输出目录',
    hyperbrdf_render_dir: 'HyperBRDF 渲染目录',
    h5_dir: 'Keras 权重目录',
    device: '训练设备',
    h5_output_dir_path: 'H5 输出目录',
  }
  return labels[key] ?? (key.charAt(0).toUpperCase() + key.slice(1).replace(/_/g, ' '))
}

function guessFileSource(key: string): string | undefined {
  if (/selected_materials/.test(key)) return 'materials'
  if (/h5/.test(key)) return 'h5_files'
  if (/pt/.test(key)) return 'pt_files'
  return undefined
}

function guessFileFilter(key: string): string[] | undefined {
  if (/selected_materials/.test(key)) return ['.binary']
  if (/h5/.test(key)) return ['.h5']
  if (/pt/.test(key)) return ['.pt']
  return undefined
}

function guessDefault(key: string): unknown {
  const defaults: Record<string, unknown> = {
    epochs: 100,
    neural_epochs: 100,
    sparse_samples: 4000,
    kl_weight: 0.1,
    fw_weight: 0.1,
    lr: 0.00005,
    train_subset: 80,
    train_seed: 42,
    keepon: false,
    device: 'cpu',
    neural_device: 'cpu',
    cuda_device: '0',
    dataset: 'MERL',
    selected_materials: [],
    selected_h5_files: [],
    selected_pts: [],
    pt_dir: 'models/HyperBRDF/results/extracted_pts',
    merl_dir: 'data/materials',
    checkpoint_path: 'models/output/checkpoint',
  }
  return key in defaults ? defaults[key] : ''
}

/** 从后端 BackendOperationDef 推导出前端的 OperationField[] */
function deriveFieldsFromBackendOp(op: BackendOperationDef): OperationField[] {
  const fields: OperationField[] = []
  const seen = new Set<string>()

  // 辅助：去重添加
  function addField(f: OperationField) {
    if (!seen.has(f.key)) {
      seen.add(f.key)
      fields.push(f)
    }
  }

  // 1. loop_source → file_picker
  const loopKey = extractSourceKey(op.loop_source ?? '')
  if (loopKey && !seen.has(loopKey)) {
    addField({
      key: loopKey,
      label: guessFieldLabel(loopKey),
      type: 'file_picker',
      default: guessDefault(loopKey),
      file_source: guessFileSource(loopKey),
      file_filter: guessFileFilter(loopKey),
    })
  }

  // 2. input_dir_source → path
  const dirKey = extractSourceKey(op.input_dir_source ?? '')
  if (dirKey && !seen.has(dirKey)) {
    addField({
      key: dirKey,
      label: guessFieldLabel(dirKey),
      type: 'path',
      default: guessDefault(dirKey),
    })
  }

  // 3. working_dir / conda_env → path/str
  if (op.working_dir && !seen.has('working_dir')) {
    addField({ key: 'working_dir', label: '工作目录', type: 'path', default: op.working_dir })
  }
  if (op.conda_env && !seen.has('conda_env')) {
    addField({ key: 'conda_env', label: 'Conda 环境', type: 'str', default: op.conda_env })
  }

  // 4. cuda_visible_source → str
  const cudaKey = extractSourceKey(op.cuda_visible_source ?? '')
  if (cudaKey && !seen.has(cudaKey)) {
    addField({
      key: cudaKey,
      label: guessFieldLabel(cudaKey),
      type: 'str',
      default: guessDefault(cudaKey),
    })
  }

  // 5. args → field for each unique request.* source or condition_source
  for (const arg of op.args ?? []) {
    let srcKey: string
    let inferredType: OperationFieldType | null = null

    if (arg.source) {
      srcKey = extractSourceKey(arg.source)
    } else if (arg.raw_value) {
      // raw_value 不产生表单字段
      continue
    } else if (arg.condition_source) {
      // condition_source-only（如 keepon）→ boolean 字段
      srcKey = extractSourceKey(arg.condition_source)
      inferredType = 'bool'
    } else {
      continue
    }
    if (!srcKey || seen.has(srcKey)) continue

    const fType = inferredType ?? guessFieldType(srcKey, arg.default)
    const fDefault = arg.default !== undefined && arg.default !== null
      ? arg.default
      : (fType === 'bool' ? false : guessDefault(srcKey))
    addField({
      key: srcKey,
      label: guessFieldLabel(srcKey),
      type: fType,
      default: fDefault,
      options: fType === 'select'
        ? [typeof fDefault === 'string' ? fDefault : '', 'cpu', 'cuda'].filter(Boolean)
        : undefined,
    })
  }

  // 6. 如果没有任何 loop_source 但有 script，添加默认 file_picker
  if (!seen.has('selected_materials') && op.loop_source) {
    // already covered above in step 1
  }

  return fields
}

/** 应该隐藏的目录字段 key（这些路径由系统固定，不在 UI 显示） */
const HIDDEN_PATH_KEYS = new Set([
  'output_dir',
  'extract_output_dir',
  'hyperbrdf_render_dir', 'nbrdf_render_dir', 'npy_output_dir',
  'h5_output_dir', 'h5_dir',
])

/** 从后端 Dict 转换为前端 OperationDef[]，自动聚合 sub_operations 的字段 */
function convertBackendOperations(
  backendOps: Record<string, BackendOperationDef>,
): OperationDef[] {
  return Object.entries(backendOps).map(([key, backendOp]) => {
    const baseFields = deriveFieldsFromBackendOp(backendOp)

    // ── 解析 sub_operations，聚合子操作字段 ──
    const subList = backendOp.sub_operations ?? []
    if (subList.length > 0) {
      const seen = new Set(baseFields.map((f) => f.key))
      for (const subKey of subList) {
        const subOp = backendOps[subKey]
        if (!subOp) continue
        for (const subField of deriveFieldsFromBackendOp(subOp)) {
          if (!seen.has(subField.key)) {
            seen.add(subField.key)
            baseFields.push(subField)
          }
        }
      }
    }

    // ── 标记隐藏字段 ──
    for (const f of baseFields) {
      if (HIDDEN_PATH_KEYS.has(f.key)) {
        f.hidden = true
      }
    }

    return {
      key,
      label: backendOp.label ?? key,
      form: { fields: baseFields },
    }
  })
}

/** 从旧式 capability 标记派生 OperationDef 列表（过渡期 fallback） */
function fallbackOperations(model: TrainModelItem): OperationDef[] {
  const ops: OperationDef[] = []
  const defaults = model.default_paths ?? {}
  const runtime = model.runtime ?? {}

  const baseMaterialsField: OperationField = {
    key: 'selected_materials',
    label: '材质选择',
    type: 'file_picker',
    default: [],
    file_source: 'materials',
    file_filter: ['.binary'],
  }

  const pathFor = (key: string, fallback = ''): OperationField => ({
    key,
    label: guessFieldLabel(key),
    type: key === 'cuda_device' ? 'str'
      : key === 'dataset' ? 'select'
        : key === 'conda_env' ? 'str'
          : 'path',
    default: defaults[key] ?? fallback,
    options: key === 'dataset' ? ['MERL', 'EPFL'] : undefined,
  })

  /** 固定路径字段（隐藏，提交时自动注入） */
  const fixedPath = (key: string, value: string): OperationField => ({
    key,
    label: guessFieldLabel(key),
    type: 'path',
    default: value,
    hidden: true,
  })

  // ── Train ──
  if (model.supports_training) {
    const fields: OperationField[] = [
      fixedPath('merl_dir', 'data/materials'),
      { key: 'dataset', label: '数据集', type: 'select', default: 'MERL', options: ['MERL', 'EPFL'] },
      { key: 'epochs', label: '训练轮数', type: 'int', default: 100, min: 1, max: 100000 },
      baseMaterialsField,
    ]

    if (model.adapter === 'neural-pytorch') {
      fields.push(
        { key: 'device', label: '训练设备', type: 'select', default: 'cpu', options: ['cpu', 'cuda'] },
        fixedPath('output_dir', 'data/render-input/neural-brdf'),
      )
    }
    if (model.adapter === 'neural-keras') {
      fields.push(
        { key: 'cuda_device', label: 'CUDA 设备', type: 'str', default: '0' },
        fixedPath('h5_output_dir', 'models/Neural-BRDF/data/merl_nbrdf'),
        fixedPath('nbrdf_render_dir', 'data/render-input/neural-brdf'),
      )
    }
    if (model.adapter === 'hyper-family') {
      fields.push(
        fixedPath('output_dir', defaults.results_dir ?? 'models/HyperBRDF/results'),
        pathFor('conda_env', runtime.conda_env ?? ''),
        { key: 'sparse_samples', label: '稀疏采样点数', type: 'int', default: 4000, min: 1, max: 1000000 },
        { key: 'kl_weight', label: 'KL 权重', type: 'float', default: 0.1, min: 0, max: 100 },
        { key: 'fw_weight', label: 'FW 权重', type: 'float', default: 0.1, min: 0, max: 100 },
        { key: 'lr', label: '学习率', type: 'float', default: 0.00005, min: 0, max: 1 },
        { key: 'train_subset', label: '训练材质数', type: 'int', default: 80, min: 0, max: 100 },
        { key: 'train_seed', label: '随机种子', type: 'int', default: 42, min: 0, max: 999999 },
        { key: 'keepon', label: '继续训练', type: 'bool', default: false },
      )
    }
    if (model.adapter === 'hypersnbrdf') {
      fields.push(
        fixedPath('output_dir', 'models/HyperSNBRDF/../output'),
        pathFor('conda_env', runtime.conda_env ?? ''),
        { key: 'epochs', label: '训练轮数', type: 'int', default: 10000, min: 1, max: 100000 },
        { key: 'lr', label: '学习率', type: 'float', default: 0.00001, min: 0, max: 1 },
        { key: 'siren_hid_features', label: 'SIREN 隐藏层特征数', type: 'int', default: 21, min: 1, max: 256 },
        { key: 'train_sample_num', label: 'SetEncoder 采样数', type: 'int', default: 400000, min: 1, max: 5000000 },
        { key: 'siren_sample_num', label: 'SIREN 采样数', type: 'int', default: 400000, min: 1, max: 5000000 },
        { key: 'tonemap_num', label: 'Tone Mapping 参数', type: 'int', default: 1, min: 1, max: 10 },
        { key: 'k1', label: 'MAE 权重 (k1)', type: 'float', default: 1.0, min: 0, max: 100 },
        { key: 'kl', label: 'Latent 正则权重 (kl)', type: 'float', default: 0.01, min: 0, max: 100 },
        { key: 'kw', label: 'Weight 正则权重 (kw)', type: 'float', default: 0.1, min: 0, max: 100 },
        { key: 'seed', label: '随机种子', type: 'int', default: 1234794195, min: 0, max: 2147483647 },
        { key: 'keepon', label: '继续训练', type: 'bool', default: false },
      )
    }
    if (model.adapter === 'custom-cli') {
      for (const p of model.parameters ?? []) {
        fields.push({ key: p.key, label: p.label, type: p.type as OperationField['type'], default: p.default, min: p.min, max: p.max, options: p.options })
      }
    }

    ops.push({ key: 'train', label: '训练', form: { fields } })
  }

  // ── H5 Convert (neural-keras only) ──
  if (model.adapter === 'neural-keras' && runtime.convert_script) {
    ops.push({
      key: 'h5_convert',
      label: 'Keras→NPY 转换',
      form: {
        fields: [
          fixedPath('h5_dir', 'models/Neural-BRDF/data/merl_nbrdf'),
          fixedPath('nbrdf_render_dir', 'data/render-input/neural-brdf'),
          pathFor('conda_env', runtime.conda_env ?? ''),
          { key: 'selected_h5_files', label: 'Keras 权重文件', type: 'file_picker', default: [], file_source: 'h5_files', file_filter: ['.h5'] },
        ],
      },
    })
  }

  // ── Extract ──
  if (model.supports_extract) {
    const fields: OperationField[] = [
      fixedPath('merl_dir', 'data/materials'),
      fixedPath('checkpoint', defaults.checkpoint ?? 'models/HyperBRDF/results/MERL/checkpoint.pt'),
      fixedPath('extract_output_dir', defaults.extract_dir ?? 'models/HyperBRDF/results/extracted_pts'),
      pathFor('conda_env', runtime.conda_env ?? ''),
      { key: 'dataset', label: '数据集', type: 'select', default: 'MERL', options: ['MERL', 'EPFL'] },
      { key: 'sparse_samples', label: '稀疏采样点数', type: 'int', default: 4000, min: 1, max: 1000000 },
      { key: 'train_seed', label: '随机种子', type: 'int', default: 42, min: 0, max: 999999 },
      baseMaterialsField,
    ]
    ops.push({ key: 'extract', label: '参数提取', form: { fields } })
  }

  // ── Decode ──
  if (model.supports_decode) {
    if (model.adapter === 'hypersnbrdf') {
      const fields: OperationField[] = [
        { key: 'checkpoint_path', label: 'Checkpoint 目录', type: 'path', default: 'models/output/checkpoint' },
        fixedPath('merl_dir', 'data/materials'),
        fixedPath('output_dir', 'data/render-input/hypersnbrdf'),
        pathFor('conda_env', runtime.conda_env ?? ''),
        { key: 'gpu', label: 'GPU 设备', type: 'str', default: 'cuda:0' },
        { key: 'siren_hid_features', label: 'SIREN 隐藏层特征数', type: 'int', default: 21, min: 1, max: 256 },
        { key: 'tonemap_num', label: 'Tone Mapping 参数', type: 'int', default: 1, min: 1, max: 10 },
        { key: 'train_sample_num', label: 'SetEncoder 采样数', type: 'int', default: 400000, min: 1, max: 5000000 },
        { key: 'siren_sample_num', label: 'SIREN 采样数', type: 'int', default: 400000, min: 1, max: 5000000 },
      ]
      ops.push({ key: 'decode', label: '解码', form: { fields } })
    } else {
      const fields: OperationField[] = [
        { key: 'pt_dir', label: '潜向量目录', type: 'path', default: defaults.extract_dir ?? 'models/HyperBRDF/results/extracted_pts' },
        fixedPath('hyperbrdf_render_dir', DEFAULT_FULLBIN_OUTPUT),
        pathFor('conda_env', runtime.conda_env ?? ''),
        { key: 'cuda_device', label: 'CUDA 设备', type: 'str', default: '0' },
        { key: 'dataset', label: '数据集', type: 'select', default: 'MERL', options: ['MERL', 'EPFL'] },
        { key: 'selected_pts', label: '潜向量文件', type: 'file_picker', default: [], file_source: 'pt_files', file_filter: ['.pt'] },
      ]
      ops.push({ key: 'decode', label: '潜向量解码', form: { fields } })
    }
  }

  // ── Reconstruct ──
  if (model.supports_reconstruction) {
    const outputDir = model.adapter === 'neural-pytorch'
      ? 'data/render-input/neural-brdf'
      : 'data/render-input/hyperbrdf'
    const fields: OperationField[] = [
      fixedPath('merl_dir', 'data/materials'),
      { key: 'dataset', label: '数据集', type: 'select', default: 'MERL', options: ['MERL', 'EPFL'] },
      pathFor('conda_env', runtime.conda_env ?? ''),
      fixedPath('output_dir', outputDir),
      fixedPath('checkpoint', defaults.checkpoint ?? 'models/HyperBRDF/results/MERL/checkpoint.pt'),
      baseMaterialsField,
    ]
    if (model.adapter === 'neural-pytorch') {
      fields.push(
        { key: 'neural_device', label: '训练设备', type: 'select', default: 'cpu', options: ['cpu', 'cuda'] },
        { key: 'epochs', label: 'Epochs', type: 'int', default: 100, min: 1, max: 100000 },
      )
    }
    ops.push({ key: 'reconstruct', label: '重建', form: { fields } })
  }

  return ops
}

/** 主入口：优先使用后端下发的 operations（Dict 格式），否则 fallback */
export function deriveOperations(model: TrainModelItem): OperationDef[] {
  const backendOps = model.operations
  if (backendOps && typeof backendOps === 'object' && Object.keys(backendOps).length > 0) {
    return convertBackendOperations(backendOps)
  }
  return fallbackOperations(model)
}
