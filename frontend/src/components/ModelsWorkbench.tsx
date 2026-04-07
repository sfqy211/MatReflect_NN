import { type MouseEvent, useEffect, useMemo, useState } from 'react'

import { useQueryClient } from '@tanstack/react-query'

import {
  useCreateTrainModel,
  useDeleteTrainModel,
  useMaterialsDirectory,
  useStartHyperDecode,
  useStartHyperExtract,
  useStartHyperRun,
  useStartNeuralKeras,
  useStartNeuralPytorch,
  useStopTrainTask,
  useTrainModels,
  useTrainRuns,
  useTrainTaskDetail,
  useWorkspaceFiles,
} from '../features/models/useModelsWorkbench'
import { BACKEND_ORIGIN } from '../lib/api'
import type {
  NeuralTrainEngine,
  TaskEvent,
  TrainModelAdapter,
  TrainModelCreateRequest,
  TrainModelItem,
  TrainRunSummary,
} from '../types/api'
import { FeedbackPanel } from './FeedbackPanel'


const TEST_SET_20 = [
  'alum-bronze',
  'beige-fabric',
  'black-obsidian',
  'blue-acrylic',
  'chrome',
  'chrome-steel',
  'dark-red-paint',
  'dark-specular-fabric',
  'delrin',
  'green-metallic-paint',
  'natural-209',
  'nylon',
  'polyethylene',
  'pure-rubber',
  'silicon-nitrade',
  'teflon',
  'violet-rubber',
  'white-diffuse-bball',
  'white-fabric',
  'yellow-paint',
]

const DEFAULT_FULLBIN_OUTPUT = 'data/inputs/fullbin'

function normalizeBinaryName(name: string) {
  return name.replace(/\.binary$/i, '')
}

function getDefaultPath(model: TrainModelItem | null, field: string, fallback: string) {
  return model?.default_paths[field] ?? fallback
}

function getRuntimeValue(model: TrainModelItem | null, field: string, fallback = '') {
  return model?.runtime[field] ?? fallback
}

function supportsDecoupledOptions(model: TrainModelItem | null) {
  return Boolean(model?.adapter_options?.supports_decoupled_options)
}

function buildDraft(adapter: TrainModelAdapter): TrainModelCreateRequest {
  const category = adapter === 'hyper-family' ? 'hyper' : 'neural'
  return {
    key: '',
    label: '',
    category,
    adapter,
    description: '',
    supports_training: true,
    supports_extract: adapter === 'hyper-family',
    supports_decode: adapter === 'hyper-family',
    supports_runs: adapter === 'hyper-family',
    default_paths:
      adapter === 'neural-pytorch'
        ? { materials_dir: 'data/inputs/binary', output_dir: 'data/inputs/npy' }
        : adapter === 'neural-keras'
          ? {
              materials_dir: 'data/inputs/binary',
              h5_output_dir: 'Neural-BRDF/data/merl_nbrdf',
              npy_output_dir: 'data/inputs/npy',
            }
          : {
              materials_dir: 'data/inputs/binary',
              results_dir: '',
              extract_dir: '',
              checkpoint: '',
            },
    runtime:
      adapter === 'neural-pytorch'
        ? { conda_env: '', working_dir: '', train_script: '' }
        : adapter === 'neural-keras'
          ? { conda_env: '', working_dir: '', train_script: '', convert_script: '' }
          : { conda_env: '', working_dir: '', train_script: '', extract_script: '', decode_script: '' },
    adapter_options: adapter === 'hyper-family' ? { supports_decoupled_options: false } : {},
  }
}

export function ModelsWorkbench() {
  const queryClient = useQueryClient()

  const [activeModelKey, setActiveModelKey] = useState('')
  const [draft, setDraft] = useState<TrainModelCreateRequest>(() => buildDraft('hyper-family'))
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [search, setSearch] = useState('')
  const [ptSearch, setPtSearch] = useState('')
  const [selectedMaterials, setSelectedMaterials] = useState<string[]>([])
  const [selectedPts, setSelectedPts] = useState<string[]>([])
  const [dataset, setDataset] = useState<'MERL' | 'EPFL'>('MERL')
  const [activeTaskId, setActiveTaskId] = useState<string | null>(null)
  const [liveLogs, setLiveLogs] = useState<string[]>([])
  const [neuralEngine, setNeuralEngine] = useState<NeuralTrainEngine>('pytorch')

  const [merlDir, setMerlDir] = useState('')
  const [neuralOutputDir, setNeuralOutputDir] = useState('')
  const [kerasH5Dir, setKerasH5Dir] = useState('')
  const [kerasNpyDir, setKerasNpyDir] = useState('')
  const [neuralDevice, setNeuralDevice] = useState<'cpu' | 'cuda'>('cpu')
  const [cudaDevice, setCudaDevice] = useState('0')
  const [condaEnv, setCondaEnv] = useState('')
  const [checkpointPath, setCheckpointPath] = useState('')
  const [trainOutputDir, setTrainOutputDir] = useState('')
  const [extractOutputDir, setExtractOutputDir] = useState('')
  const [ptDir, setPtDir] = useState('')
  const [fullbinOutputDir, setFullbinOutputDir] = useState(DEFAULT_FULLBIN_OUTPUT)
  const [teacherDir, setTeacherDir] = useState('')
  const [baselineCheckpoint, setBaselineCheckpoint] = useState('')
  const [epochs, setEpochs] = useState(100)
  const [sparseSamples, setSparseSamples] = useState(4000)
  const [klWeight, setKlWeight] = useState(0.1)
  const [fwWeight, setFwWeight] = useState(0.1)
  const [lr, setLr] = useState(0.00005)
  const [trainSubset, setTrainSubset] = useState(80)
  const [trainSeed, setTrainSeed] = useState(42)
  const [keepon, setKeepon] = useState(false)
  const [modelType, setModelType] = useState<'baseline' | 'decoupled'>('decoupled')
  const [samplingMode, setSamplingMode] = useState<'random' | 'hybrid'>('hybrid')
  const [analyticLobes, setAnalyticLobes] = useState<1 | 2>(1)
  const [analyticLossWeight, setAnalyticLossWeight] = useState(0.1)
  const [residualLossWeight, setResidualLossWeight] = useState(0.1)
  const [specLossWeight, setSpecLossWeight] = useState(0.2)
  const [gateRegWeight, setGateRegWeight] = useState(0.05)
  const [specPercentile, setSpecPercentile] = useState(0.9)
  const [gateBiasInit, setGateBiasInit] = useState(-2)
  const [stageAEpochs, setStageAEpochs] = useState(10)
  const [stageBRampEpochs, setStageBRampEpochs] = useState(20)

  const modelQuery = useTrainModels()
  const materialsQuery = useMaterialsDirectory(search)
  const activeModel = useMemo(
    () => modelQuery.data?.items.find((item) => item.key === activeModelKey) ?? null,
    [activeModelKey, modelQuery.data?.items],
  )
  const runsQuery = useTrainRuns(activeModel?.supports_runs ? activeModel.key : null, Boolean(activeModel?.supports_runs))
  const ptFilesQuery = useWorkspaceFiles(ptDir, ['.pt'], ptSearch, Boolean(activeModel?.supports_decode))
  const taskDetailQuery = useTrainTaskDetail(activeTaskId)

  const createTrainModel = useCreateTrainModel()
  const deleteTrainModel = useDeleteTrainModel()
  const startNeuralPytorch = useStartNeuralPytorch()
  const startNeuralKeras = useStartNeuralKeras()
  const startHyperRun = useStartHyperRun()
  const startHyperExtract = useStartHyperExtract()
  const startHyperDecode = useStartHyperDecode()
  const stopTrainTask = useStopTrainTask()

  const materialItems = materialsQuery.data?.items ?? []
  const ptItems = ptFilesQuery.data?.items ?? []
  const runs = activeModel?.supports_runs ? runsQuery.data?.items ?? [] : []
  const taskDetail = taskDetailQuery.data
  const taskRecord = taskDetail?.record

  useEffect(() => {
    const firstModel = modelQuery.data?.items[0]?.key ?? ''
    if (!activeModelKey && firstModel) {
      setActiveModelKey(firstModel)
    }
  }, [activeModelKey, modelQuery.data?.items])

  useEffect(() => {
    if (!activeModel) {
      return
    }
    setNeuralEngine(activeModel.adapter === 'neural-keras' ? 'keras' : 'pytorch')
    setMerlDir(getDefaultPath(activeModel, 'materials_dir', 'data/inputs/binary'))
    setNeuralOutputDir(getDefaultPath(activeModel, 'output_dir', 'data/inputs/npy'))
    setKerasH5Dir(getDefaultPath(activeModel, 'h5_output_dir', 'Neural-BRDF/data/merl_nbrdf'))
    setKerasNpyDir(getDefaultPath(activeModel, 'npy_output_dir', 'data/inputs/npy'))
    setCondaEnv(getRuntimeValue(activeModel, 'conda_env'))
    setTrainOutputDir(getDefaultPath(activeModel, 'results_dir', ''))
    setExtractOutputDir(getDefaultPath(activeModel, 'extract_dir', ''))
    setPtDir(getDefaultPath(activeModel, 'extract_dir', ''))
    setCheckpointPath(getDefaultPath(activeModel, 'checkpoint', ''))
    setTeacherDir(getDefaultPath(activeModel, 'teacher_dir', ''))
    setBaselineCheckpoint('')
    setFullbinOutputDir(DEFAULT_FULLBIN_OUTPUT)
    setDataset('MERL')
  }, [activeModel?.key])

  useEffect(() => {
    const available = new Set(materialItems.map((item) => item.name))
    setSelectedMaterials((current) => current.filter((name) => available.has(name)))
  }, [materialItems])

  useEffect(() => {
    const available = new Set(ptItems.map((item) => item.name))
    setSelectedPts((current) => current.filter((name) => available.has(name)))
  }, [ptItems])

  useEffect(() => {
    if (!taskDetail) {
      return
    }
    setLiveLogs(taskDetail.logs.slice(-160))
  }, [taskDetail?.record.task_id, taskDetail?.logs])

  useEffect(() => {
    if (!activeTaskId) {
      return
    }
    const wsProtocol = BACKEND_ORIGIN.startsWith('https') ? 'wss' : 'ws'
    const socket = new WebSocket(`${wsProtocol}://${new URL(BACKEND_ORIGIN).host}/ws/tasks/${activeTaskId}`)

    socket.onmessage = (event) => {
      const payload = JSON.parse(event.data) as TaskEvent
      if (payload.message) {
        setLiveLogs((current) => {
          if (current[current.length - 1] === payload.message) {
            return current
          }
          return [...current, payload.message].slice(-160)
        })
      }
      queryClient.invalidateQueries({ queryKey: ['train-task-detail', activeTaskId] })
      queryClient.invalidateQueries({ queryKey: ['train-runs'] })
      queryClient.invalidateQueries({ queryKey: ['workspace-files'] })
    }

    return () => {
      socket.close()
    }
  }, [activeTaskId, queryClient])

  const summaryChips = useMemo(
    () => [
      `当前模型: ${activeModel?.label ?? '-'}`,
      `适配器: ${activeModel?.adapter ?? '-'}`,
      `固定材质库: ${materialItems.length}`,
      `已选材质: ${selectedMaterials.length}`,
      `运行记录: ${runs.length}`,
      `PT 文件: ${ptItems.length}`,
    ],
    [activeModel?.adapter, activeModel?.label, materialItems.length, ptItems.length, runs.length, selectedMaterials.length],
  )

  const logs = liveLogs.length > 0 ? liveLogs : taskDetail?.logs ?? []
  const currentStatus = taskRecord?.status ?? 'idle'
  const progressValue = taskRecord?.progress ?? 0
  const taskError =
    createTrainModel.error ??
    deleteTrainModel.error ??
    startNeuralPytorch.error ??
    startNeuralKeras.error ??
    startHyperRun.error ??
    startHyperExtract.error ??
    startHyperDecode.error ??
    stopTrainTask.error
  const taskStateMessage =
    taskRecord?.status === 'failed'
      ? taskRecord.message || '任务执行失败，请检查环境、路径和日志输出。'
      : taskRecord?.status === 'cancelled'
        ? taskRecord.message || '任务已取消。'
        : null

  const toggleMaterial = (name: string, event?: MouseEvent) => {
    setSelectedMaterials((current) => {
      const currentIndex = materialItems.findIndex((item) => item.name === name)
      if (event?.shiftKey && current.length > 0 && currentIndex !== -1) {
        const lastSelectedName = current[current.length - 1]
        const lastSelectedIndex = materialItems.findIndex((item) => item.name === lastSelectedName)
        if (lastSelectedIndex !== -1) {
          const start = Math.min(lastSelectedIndex, currentIndex)
          const end = Math.max(lastSelectedIndex, currentIndex)
          const rangeNames = materialItems.slice(start, end + 1).map((item) => item.name)
          return Array.from(new Set([...current, ...rangeNames]))
        }
      }
      return current.includes(name) ? current.filter((item) => item !== name) : [...current, name]
    })
  }

  const togglePt = (name: string, event?: MouseEvent) => {
    setSelectedPts((current) => {
      const currentIndex = ptItems.findIndex((item) => item.name === name)
      if (event?.shiftKey && current.length > 0 && currentIndex !== -1) {
        const lastSelectedName = current[current.length - 1]
        const lastSelectedIndex = ptItems.findIndex((item) => item.name === lastSelectedName)
        if (lastSelectedIndex !== -1) {
          const start = Math.min(lastSelectedIndex, currentIndex)
          const end = Math.max(lastSelectedIndex, currentIndex)
          const rangeNames = ptItems.slice(start, end + 1).map((item) => item.name)
          return Array.from(new Set([...current, ...rangeNames]))
        }
      }
      return current.includes(name) ? current.filter((item) => item !== name) : [...current, name]
    })
  }

  const applyPreset = () => {
    const selected = materialItems
      .filter((item) => TEST_SET_20.includes(normalizeBinaryName(item.name)))
      .map((item) => item.name)
    setSelectedMaterials(selected)
  }

  const applyRun = (run: TrainRunSummary) => {
    setActiveModelKey(run.model_key)
    setCheckpointPath(run.checkpoint_path)
    setDataset(run.dataset === 'EPFL' ? 'EPFL' : 'MERL')
  }

  const updateDraft = (updater: (current: TrainModelCreateRequest) => TrainModelCreateRequest) => {
    setDraft((current) => updater(current))
  }

  const changeDraftAdapter = (adapter: TrainModelAdapter) => {
    setDraft((current) => {
      const next = buildDraft(adapter)
      return {
        ...next,
        key: current.key,
        label: current.label,
        description: current.description,
      }
    })
  }

  const submitCreateModel = async () => {
    const response = await createTrainModel.mutateAsync(draft)
    await queryClient.invalidateQueries({ queryKey: ['train-models'] })
    setActiveModelKey(response.item.key)
    setShowCreateForm(false)
    setDraft(buildDraft(draft.adapter))
  }

  const removeModel = async (model: TrainModelItem) => {
    if (model.built_in) {
      return
    }
    if (!window.confirm(`确认删除模型 ${model.label} (${model.key}) 吗？`)) {
      return
    }
    await deleteTrainModel.mutateAsync(model.key)
    await queryClient.invalidateQueries({ queryKey: ['train-models'] })
    if (activeModelKey === model.key) {
      const fallback = modelQuery.data?.items.find((item) => item.key !== model.key)?.key ?? ''
      setActiveModelKey(fallback)
    }
  }

  const startTraining = async () => {
    if (!activeModel) {
      return
    }
    setLiveLogs([])
    if (activeModel.adapter === 'neural-pytorch') {
      const response = await startNeuralPytorch.mutateAsync({
        model_key: activeModel.key,
        merl_dir: merlDir,
        selected_materials: selectedMaterials,
        epochs,
        output_dir: neuralOutputDir,
        device: neuralDevice,
      })
      setActiveTaskId(response.task_id)
      return
    }
    if (activeModel.adapter === 'neural-keras') {
      const response = await startNeuralKeras.mutateAsync({
        model_key: activeModel.key,
        merl_dir: merlDir,
        selected_materials: selectedMaterials,
        cuda_device: cudaDevice,
        h5_output_dir: kerasH5Dir,
        npy_output_dir: kerasNpyDir,
      })
      setActiveTaskId(response.task_id)
      return
    }
    const response = await startHyperRun.mutateAsync({
      model_key: activeModel.key,
      merl_dir: merlDir,
      output_dir: trainOutputDir,
      conda_env: condaEnv,
      dataset,
      epochs,
      sparse_samples: sparseSamples,
      kl_weight: klWeight,
      fw_weight: fwWeight,
      lr,
      keepon,
      train_subset: trainSubset,
      train_seed: trainSeed,
      model_type: modelType,
      sampling_mode: samplingMode,
      teacher_dir: teacherDir,
      analytic_lobes: analyticLobes,
      baseline_checkpoint: baselineCheckpoint.trim(),
      analytic_loss_weight: analyticLossWeight,
      residual_loss_weight: residualLossWeight,
      spec_loss_weight: specLossWeight,
      gate_reg_weight: gateRegWeight,
      spec_percentile: specPercentile,
      gate_bias_init: gateBiasInit,
      stage_a_epochs: stageAEpochs,
      stage_b_ramp_epochs: stageBRampEpochs,
    })
    setActiveTaskId(response.task_id)
  }

  const startExtract = async () => {
    if (!activeModel || activeModel.adapter !== 'hyper-family' || !activeModel.supports_extract) {
      return
    }
    setLiveLogs([])
    const response = await startHyperExtract.mutateAsync({
      model_key: activeModel.key,
      merl_dir: merlDir,
      selected_materials: selectedMaterials,
      model_path: checkpointPath,
      output_dir: extractOutputDir,
      conda_env: condaEnv,
      dataset,
      sparse_samples: sparseSamples,
    })
    setActiveTaskId(response.task_id)
  }

  const startDecode = async () => {
    if (!activeModel || activeModel.adapter !== 'hyper-family' || !activeModel.supports_decode) {
      return
    }
    setLiveLogs([])
    const response = await startHyperDecode.mutateAsync({
      model_key: activeModel.key,
      pt_dir: ptDir,
      selected_pts: selectedPts,
      output_dir: fullbinOutputDir,
      conda_env: condaEnv,
      dataset,
      cuda_device: cudaDevice,
    })
    setActiveTaskId(response.task_id)
  }

  const stopTask = async () => {
    if (!activeTaskId) {
      return
    }
    await stopTrainTask.mutateAsync(activeTaskId)
    queryClient.invalidateQueries({ queryKey: ['train-task-detail', activeTaskId] })
  }

  return (
    <section className="workspace-canvas">
      <div className="workspace-hero">
        <div>
          <h2>网络模型管理</h2>
        </div>
      </div>

      <div className="detail-pill-grid">
        {summaryChips.map((chip) => (
          <span key={chip} className="detail-pill">
            {chip}
          </span>
        ))}
      </div>

      <div className="models-layout">
        <section className="models-section">
          <div className="detail-board__lead">
            <h3>模型注册表</h3>
          </div>
          <div className="render-actions">
            <button type="button" className="theme-toggle" onClick={() => setShowCreateForm((current) => !current)}>
              {showCreateForm ? '收起新增表单' : '添加自研模型'}
            </button>
            {activeModel && !activeModel.built_in ? (
              <button
                type="button"
                className="theme-toggle render-actions--danger"
                onClick={() => void removeModel(activeModel)}
              >
                删除当前模型
              </button>
            ) : null}
          </div>
          {activeModel?.built_in ? (
            <FeedbackPanel
              title="当前模型为内建模型"
              message="内建模型仅支持使用与兼容，不提供删除操作。切换到自定义模型后可执行删除。"
              tone="info"
              compact
            />
          ) : null}
          <div className="runs-list">
            {(modelQuery.data?.items ?? []).map((model) => (
              <article
                key={model.key}
                className={activeModelKey === model.key ? 'run-card run-card--selected' : 'run-card'}
              >
                <strong>{model.label}</strong>
                <span>{model.key}</span>
                <div className="detail-pill-grid">
                  <span className="detail-pill">{model.adapter}</span>
                  <span className="detail-pill">{model.category}</span>
                  <span className="detail-pill">{model.built_in ? '内建' : '自定义'}</span>
                </div>
                {model.description ? <span>{model.description}</span> : null}
                <div className="render-actions">
                  <button type="button" className="theme-toggle" onClick={() => setActiveModelKey(model.key)}>
                    切换到此模型
                  </button>
                  {!model.built_in ? (
                    <button type="button" className="theme-toggle render-actions--danger" onClick={() => void removeModel(model)}>
                      删除模型
                    </button>
                  ) : null}
                </div>
              </article>
            ))}
          </div>
        </section>

        <section className="models-section">
          <div className="detail-board__lead">
            <h3>固定材质选择</h3>
          </div>
          <div className="file-toolbar">
            <input
              type="search"
              className="search-input"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="搜索 binary 材质"
            />
            <div className="file-toolbar__actions">
              <button type="button" className="theme-toggle" onClick={() => setSelectedMaterials(materialItems.map((item) => item.name))}>
                全选
              </button>
              <button type="button" className="theme-toggle" onClick={applyPreset}>
                预设 20
              </button>
              <button type="button" className="theme-toggle" onClick={() => setSelectedMaterials([])}>
                清空
              </button>
            </div>
          </div>
          <div className="file-list">
            {materialsQuery.error instanceof Error ? (
              <FeedbackPanel title="材质目录读取失败" message={materialsQuery.error.message} tone="error" compact />
            ) : null}
            {materialItems.map((item) => (
              <label
                key={item.path}
                className="file-item"
                onClick={(event) => {
                  event.preventDefault()
                  toggleMaterial(item.name, event)
                }}
              >
                <input type="checkbox" checked={selectedMaterials.includes(item.name)} readOnly />
                <span>{item.name}</span>
              </label>
            ))}
            {!materialsQuery.error && materialItems.length === 0 ? (
              <FeedbackPanel title="当前没有可训练材质" message="请检查 data/inputs/binary 下是否存在 .binary 文件。" tone="empty" compact />
            ) : null}
          </div>
        </section>

        {showCreateForm ? (
          <section className="models-section models-section--wide">
            <div className="detail-board__lead">
              <h3>新增模型</h3>
            </div>
            <div className="render-form-grid">
              <label className="field">
                <span>模型 key</span>
                <input value={draft.key} onChange={(event) => updateDraft((current) => ({ ...current, key: event.target.value }))} />
              </label>
              <label className="field">
                <span>显示名称</span>
                <input value={draft.label} onChange={(event) => updateDraft((current) => ({ ...current, label: event.target.value }))} />
              </label>
              <label className="field">
                <span>适配器</span>
                <select value={draft.adapter} onChange={(event) => changeDraftAdapter(event.target.value as TrainModelAdapter)}>
                  <option value="hyper-family">hyper-family</option>
                  <option value="neural-pytorch">neural-pytorch</option>
                  <option value="neural-keras">neural-keras</option>
                </select>
              </label>
              <label className="field">
                <span>说明</span>
                <input value={draft.description} onChange={(event) => updateDraft((current) => ({ ...current, description: event.target.value }))} />
              </label>
            </div>

            <div className="render-form-grid">
              <label className="field">
                <span>Conda 环境</span>
                <input
                  value={draft.runtime.conda_env ?? ''}
                  onChange={(event) =>
                    updateDraft((current) => ({
                      ...current,
                      runtime: { ...current.runtime, conda_env: event.target.value },
                    }))
                  }
                />
              </label>
              <label className="field">
                <span>工作目录</span>
                <input
                  value={draft.runtime.working_dir ?? ''}
                  onChange={(event) =>
                    updateDraft((current) => ({
                      ...current,
                      runtime: { ...current.runtime, working_dir: event.target.value },
                    }))
                  }
                />
              </label>
              <label className="field">
                <span>训练脚本</span>
                <input
                  value={draft.runtime.train_script ?? ''}
                  onChange={(event) =>
                    updateDraft((current) => ({
                      ...current,
                      runtime: { ...current.runtime, train_script: event.target.value },
                    }))
                  }
                />
              </label>
              {draft.adapter === 'neural-keras' ? (
                <label className="field">
                  <span>转换脚本</span>
                  <input
                    value={draft.runtime.convert_script ?? ''}
                    onChange={(event) =>
                      updateDraft((current) => ({
                        ...current,
                        runtime: { ...current.runtime, convert_script: event.target.value },
                      }))
                    }
                  />
                </label>
              ) : null}
              {draft.adapter === 'hyper-family' ? (
                <>
                  <label className="field">
                    <span>提取脚本</span>
                    <input
                      value={draft.runtime.extract_script ?? ''}
                      onChange={(event) =>
                        updateDraft((current) => ({
                          ...current,
                          runtime: { ...current.runtime, extract_script: event.target.value },
                        }))
                      }
                    />
                  </label>
                  <label className="field">
                    <span>解码脚本</span>
                    <input
                      value={draft.runtime.decode_script ?? ''}
                      onChange={(event) =>
                        updateDraft((current) => ({
                          ...current,
                          runtime: { ...current.runtime, decode_script: event.target.value },
                        }))
                      }
                    />
                  </label>
                </>
              ) : null}
            </div>

            <div className="render-form-grid">
              <label className="field">
                <span>材质目录</span>
                <input
                  value={draft.default_paths.materials_dir ?? ''}
                  onChange={(event) =>
                    updateDraft((current) => ({
                      ...current,
                      default_paths: { ...current.default_paths, materials_dir: event.target.value },
                    }))
                  }
                />
              </label>
              {draft.adapter === 'neural-pytorch' ? (
                <label className="field">
                  <span>输出目录</span>
                  <input
                    value={draft.default_paths.output_dir ?? ''}
                    onChange={(event) =>
                      updateDraft((current) => ({
                        ...current,
                        default_paths: { ...current.default_paths, output_dir: event.target.value },
                      }))
                    }
                  />
                </label>
              ) : null}
              {draft.adapter === 'neural-keras' ? (
                <>
                  <label className="field">
                    <span>H5 输出目录</span>
                    <input
                      value={draft.default_paths.h5_output_dir ?? ''}
                      onChange={(event) =>
                        updateDraft((current) => ({
                          ...current,
                          default_paths: { ...current.default_paths, h5_output_dir: event.target.value },
                        }))
                      }
                    />
                  </label>
                  <label className="field">
                    <span>NPY 输出目录</span>
                    <input
                      value={draft.default_paths.npy_output_dir ?? ''}
                      onChange={(event) =>
                        updateDraft((current) => ({
                          ...current,
                          default_paths: { ...current.default_paths, npy_output_dir: event.target.value },
                        }))
                      }
                    />
                  </label>
                </>
              ) : null}
              {draft.adapter === 'hyper-family' ? (
                <>
                  <label className="field">
                    <span>结果目录</span>
                    <input
                      value={draft.default_paths.results_dir ?? ''}
                      onChange={(event) =>
                        updateDraft((current) => ({
                          ...current,
                          default_paths: { ...current.default_paths, results_dir: event.target.value },
                        }))
                      }
                    />
                  </label>
                  <label className="field">
                    <span>PT 目录</span>
                    <input
                      value={draft.default_paths.extract_dir ?? ''}
                      onChange={(event) =>
                        updateDraft((current) => ({
                          ...current,
                          default_paths: { ...current.default_paths, extract_dir: event.target.value },
                        }))
                      }
                    />
                  </label>
                  <label className="field">
                    <span>默认 Checkpoint</span>
                    <input
                      value={draft.default_paths.checkpoint ?? ''}
                      onChange={(event) =>
                        updateDraft((current) => ({
                          ...current,
                          default_paths: { ...current.default_paths, checkpoint: event.target.value },
                        }))
                      }
                    />
                  </label>
                </>
              ) : null}
            </div>

            {draft.adapter === 'hyper-family' ? (
              <div className="render-toggle-row">
                <label className="toggle-field">
                  <input type="checkbox" checked={draft.supports_extract} onChange={(event) => updateDraft((current) => ({ ...current, supports_extract: event.target.checked }))} />
                  <span>支持参数提取</span>
                </label>
                <label className="toggle-field">
                  <input type="checkbox" checked={draft.supports_decode} onChange={(event) => updateDraft((current) => ({ ...current, supports_decode: event.target.checked }))} />
                  <span>支持 fullbin 解码</span>
                </label>
                <label className="toggle-field">
                  <input type="checkbox" checked={draft.supports_runs} onChange={(event) => updateDraft((current) => ({ ...current, supports_runs: event.target.checked }))} />
                  <span>支持运行记录扫描</span>
                </label>
                <label className="toggle-field">
                  <input
                    type="checkbox"
                    checked={Boolean(draft.adapter_options.supports_decoupled_options)}
                    onChange={(event) =>
                      updateDraft((current) => ({
                        ...current,
                        adapter_options: { ...current.adapter_options, supports_decoupled_options: event.target.checked },
                      }))
                    }
                  />
                  <span>支持解耦扩展参数</span>
                </label>
              </div>
            ) : null}

            <div className="render-actions">
              <button type="button" className="theme-toggle render-actions--primary" onClick={() => void submitCreateModel()}>
                保存模型
              </button>
              <button type="button" className="theme-toggle" onClick={() => setDraft(buildDraft(draft.adapter))}>
                重置表单
              </button>
            </div>
          </section>
        ) : null}

        <section className="models-section">
          <div className="detail-board__lead">
            <h3>训练入口</h3>
          </div>
          <div className="render-form-grid">
            <label className="field">
              <span>材质目录</span>
              <input value={merlDir} onChange={(event) => setMerlDir(event.target.value)} />
            </label>
            <label className="field">
              <span>数据集</span>
              <select value={dataset} onChange={(event) => setDataset(event.target.value as 'MERL' | 'EPFL')} disabled={activeModel?.category === 'neural'}>
                <option value="MERL">MERL</option>
                <option value="EPFL">EPFL</option>
              </select>
            </label>
            <label className="field">
              <span>Epochs</span>
              <input type="number" value={epochs} onChange={(event) => setEpochs(Number(event.target.value) || 1)} />
            </label>
            <label className="field">
              <span>{activeModel?.category === 'neural' && neuralEngine === 'pytorch' ? '训练设备' : 'Conda 环境'}</span>
              {activeModel?.adapter === 'neural-pytorch' ? (
                <select value={neuralDevice} onChange={(event) => setNeuralDevice(event.target.value as 'cpu' | 'cuda')}>
                  <option value="cpu">cpu</option>
                  <option value="cuda">cuda</option>
                </select>
              ) : (
                <input value={condaEnv} onChange={(event) => setCondaEnv(event.target.value)} />
              )}
            </label>
          </div>
          {activeModel?.adapter === 'neural-pytorch' ? (
            <div className="render-form-grid">
              <label className="field">
                <span>NPY 输出目录</span>
                <input value={neuralOutputDir} onChange={(event) => setNeuralOutputDir(event.target.value)} />
              </label>
            </div>
          ) : null}
          {activeModel?.adapter === 'neural-keras' ? (
            <div className="render-form-grid">
              <label className="field">
                <span>CUDA 设备</span>
                <input value={cudaDevice} onChange={(event) => setCudaDevice(event.target.value)} />
              </label>
              <label className="field">
                <span>H5 输出目录</span>
                <input value={kerasH5Dir} onChange={(event) => setKerasH5Dir(event.target.value)} />
              </label>
              <label className="field">
                <span>NPY 输出目录</span>
                <input value={kerasNpyDir} onChange={(event) => setKerasNpyDir(event.target.value)} />
              </label>
            </div>
          ) : null}
          {activeModel?.adapter === 'hyper-family' ? (
            <>
              <div className="render-form-grid">
                <label className="field">
                  <span>训练结果目录</span>
                  <input value={trainOutputDir} onChange={(event) => setTrainOutputDir(event.target.value)} />
                </label>
                <label className="field">
                  <span>稀疏采样点数</span>
                  <input type="number" value={sparseSamples} onChange={(event) => setSparseSamples(Number(event.target.value) || 1)} />
                </label>
                <label className="field">
                  <span>KL 权重</span>
                  <input type="number" step="0.01" value={klWeight} onChange={(event) => setKlWeight(Number(event.target.value) || 0)} />
                </label>
                <label className="field">
                  <span>FW 权重</span>
                  <input type="number" step="0.01" value={fwWeight} onChange={(event) => setFwWeight(Number(event.target.value) || 0)} />
                </label>
                <label className="field">
                  <span>学习率</span>
                  <input type="number" step="0.00001" value={lr} onChange={(event) => setLr(Number(event.target.value) || 0.00001)} />
                </label>
                <label className="field">
                  <span>训练材质数</span>
                  <input type="number" value={trainSubset} onChange={(event) => setTrainSubset(Number(event.target.value) || 0)} />
                </label>
              </div>
              <div className="render-toggle-row">
                <label className="toggle-field">
                  <input type="checkbox" checked={keepon} onChange={(event) => setKeepon(event.target.checked)} />
                  <span>继续训练</span>
                </label>
              </div>
              {supportsDecoupledOptions(activeModel) ? (
                <div className="render-form-grid">
                  <label className="field">
                    <span>模型类型</span>
                    <select value={modelType} onChange={(event) => setModelType(event.target.value as 'baseline' | 'decoupled')}>
                      <option value="decoupled">decoupled</option>
                      <option value="baseline">baseline</option>
                    </select>
                  </label>
                  <label className="field">
                    <span>采样策略</span>
                    <select value={samplingMode} onChange={(event) => setSamplingMode(event.target.value as 'random' | 'hybrid')}>
                      <option value="hybrid">hybrid</option>
                      <option value="random">random</option>
                    </select>
                  </label>
                  <label className="field">
                    <span>Teacher 目录</span>
                    <input value={teacherDir} onChange={(event) => setTeacherDir(event.target.value)} />
                  </label>
                  <label className="field">
                    <span>Baseline Checkpoint</span>
                    <input value={baselineCheckpoint} onChange={(event) => setBaselineCheckpoint(event.target.value)} />
                  </label>
                  <label className="field">
                    <span>解析 lobes</span>
                    <select value={analyticLobes} onChange={(event) => setAnalyticLobes(Number(event.target.value) as 1 | 2)}>
                      <option value={1}>1</option>
                      <option value={2}>2</option>
                    </select>
                  </label>
                  <label className="field">
                    <span>高光分位数</span>
                    <input type="number" step="0.01" value={specPercentile} onChange={(event) => setSpecPercentile(Number(event.target.value) || 0.9)} />
                  </label>
                  <label className="field">
                    <span>解析损失权重</span>
                    <input type="number" step="0.01" value={analyticLossWeight} onChange={(event) => setAnalyticLossWeight(Number(event.target.value) || 0)} />
                  </label>
                  <label className="field">
                    <span>残差损失权重</span>
                    <input type="number" step="0.01" value={residualLossWeight} onChange={(event) => setResidualLossWeight(Number(event.target.value) || 0)} />
                  </label>
                  <label className="field">
                    <span>高光损失权重</span>
                    <input type="number" step="0.01" value={specLossWeight} onChange={(event) => setSpecLossWeight(Number(event.target.value) || 0)} />
                  </label>
                  <label className="field">
                    <span>门控正则权重</span>
                    <input type="number" step="0.01" value={gateRegWeight} onChange={(event) => setGateRegWeight(Number(event.target.value) || 0)} />
                  </label>
                  <label className="field">
                    <span>门控 Bias 初值</span>
                    <input type="number" step="0.1" value={gateBiasInit} onChange={(event) => setGateBiasInit(Number(event.target.value) || 0)} />
                  </label>
                  <label className="field">
                    <span>阶段 A Epochs</span>
                    <input type="number" value={stageAEpochs} onChange={(event) => setStageAEpochs(Number(event.target.value) || 0)} />
                  </label>
                  <label className="field">
                    <span>阶段 B Ramp Epochs</span>
                    <input type="number" value={stageBRampEpochs} onChange={(event) => setStageBRampEpochs(Number(event.target.value) || 0)} />
                  </label>
                </div>
              ) : null}
            </>
          ) : null}
          <div className="render-actions">
            <button
              type="button"
              className="theme-toggle render-actions--primary"
              onClick={() => void startTraining()}
              disabled={!activeModel || (activeModel.category === 'neural' && selectedMaterials.length === 0)}
            >
              启动训练
            </button>
          </div>
        </section>

        <section className="models-section">
          <div className="detail-board__lead">
            <h3>运行记录</h3>
          </div>
          <div className="runs-list">
            {!activeModel?.supports_runs ? (
              <FeedbackPanel title="当前模型无运行记录" message="该模型未启用 supports_runs，因此不会显示其它模型的训练记录。" tone="empty" compact />
            ) : null}
            {runsQuery.error instanceof Error ? (
              <FeedbackPanel title="运行记录读取失败" message={runsQuery.error.message} tone="error" compact />
            ) : null}
            {runs.map((run) => (
              <article key={`${run.model_key}-${run.run_dir}`} className="run-card">
                <strong>{run.label}</strong>
                <span>{run.run_name}</span>
                <span>{run.dataset} / 已训练 {run.completed_epochs} epochs</span>
                <div className="render-actions">
                  <button type="button" className="theme-toggle" onClick={() => applyRun(run)} disabled={!run.has_checkpoint}>
                    应用 Checkpoint
                  </button>
                </div>
              </article>
            ))}
            {!runsQuery.error && activeModel?.supports_runs && runs.length === 0 ? (
              <FeedbackPanel title="当前没有运行记录" message="该模型尚未产出可扫描的结果目录，或未启用 supports_runs。" tone="empty" compact />
            ) : null}
          </div>
        </section>
        {activeModel?.adapter === 'hyper-family' ? (
          <>
            {activeModel.supports_extract ? (
              <section className="models-section">
                <div className="detail-board__lead">
                  <h3>参数提取</h3>
                </div>
                <div className="render-form-grid">
                  <label className="field">
                    <span>Checkpoint</span>
                    <input value={checkpointPath} onChange={(event) => setCheckpointPath(event.target.value)} />
                  </label>
                  <label className="field">
                    <span>PT 输出目录</span>
                    <input
                      value={extractOutputDir}
                      onChange={(event) => {
                        setExtractOutputDir(event.target.value)
                        setPtDir(event.target.value)
                      }}
                    />
                  </label>
                  <label className="field">
                    <span>随机种子</span>
                    <input type="number" value={trainSeed} onChange={(event) => setTrainSeed(Number(event.target.value) || 0)} />
                  </label>
                </div>
                <div className="render-actions">
                  <button
                    type="button"
                    className="theme-toggle render-actions--primary"
                    onClick={() => void startExtract()}
                    disabled={dataset === 'MERL' && selectedMaterials.length === 0}
                  >
                    启动参数提取
                  </button>
                </div>
              </section>
            ) : null}
            {activeModel.supports_decode ? (
              <section className="models-section">
                <div className="detail-board__lead">
                  <h3>PT 解码</h3>
                </div>
                <div className="render-form-grid">
                  <label className="field">
                    <span>PT 目录</span>
                    <input value={ptDir} onChange={(event) => setPtDir(event.target.value)} />
                  </label>
                  <label className="field">
                    <span>FullBin 输出目录</span>
                    <input value={fullbinOutputDir} onChange={(event) => setFullbinOutputDir(event.target.value)} />
                  </label>
                  <label className="field">
                    <span>CUDA 设备</span>
                    <input value={cudaDevice} onChange={(event) => setCudaDevice(event.target.value)} />
                  </label>
                </div>
                <div className="file-toolbar">
                  <input
                    type="search"
                    className="search-input"
                    value={ptSearch}
                    onChange={(event) => setPtSearch(event.target.value)}
                    placeholder="搜索已提取的 .pt 文件"
                  />
                  <div className="file-toolbar__actions">
                    <button type="button" className="theme-toggle" onClick={() => setSelectedPts(ptItems.map((item) => item.name))}>
                      全选
                    </button>
                    <button type="button" className="theme-toggle" onClick={() => setSelectedPts([])}>
                      清空
                    </button>
                  </div>
                </div>
                <div className="file-list">
                  {ptFilesQuery.error instanceof Error ? (
                    <FeedbackPanel title="PT 列表读取失败" message={ptFilesQuery.error.message} tone="error" compact />
                  ) : null}
                  {ptItems.map((item) => (
                    <label
                      key={item.path}
                      className="file-item"
                      onClick={(event) => {
                        event.preventDefault()
                        togglePt(item.name, event)
                      }}
                    >
                      <input type="checkbox" checked={selectedPts.includes(item.name)} readOnly />
                      <span>{item.name}</span>
                    </label>
                  ))}
                  {!ptFilesQuery.error && ptItems.length === 0 ? (
                    <FeedbackPanel title="当前没有可解码的 PT 文件" message="请先完成参数提取，或检查 PT 目录是否正确。" tone="empty" compact />
                  ) : null}
                </div>
                <div className="render-actions">
                  <button type="button" className="theme-toggle render-actions--primary" onClick={() => void startDecode()} disabled={selectedPts.length === 0}>
                    执行 fullbin 解码
                  </button>
                </div>
              </section>
            ) : null}
          </>
        ) : null}

        <section className="models-section models-section--wide">
          <div className="detail-board__lead">
            <h3>任务状态 / 日志</h3>
          </div>
          <div className="task-summary">
            <div className="settings-row">
              <span>Task ID</span>
              <strong>{activeTaskId ?? '-'}</strong>
            </div>
            <div className="settings-row">
              <span>Status</span>
              <strong>{currentStatus}</strong>
            </div>
            <div className="settings-row">
              <span>Progress</span>
              <strong>{progressValue}%</strong>
            </div>
          </div>
          <div className="progress-bar">
            <div className="progress-bar__fill" style={{ width: `${progressValue}%` }} />
          </div>
          {taskStateMessage ? (
            <FeedbackPanel
              title={taskRecord?.status === 'failed' ? '任务失败' : '任务已取消'}
              message={taskStateMessage}
              tone={taskRecord?.status === 'failed' ? 'error' : 'info'}
              compact
            />
          ) : null}
          <div className="render-actions">
            <button type="button" className="theme-toggle render-actions--danger" onClick={() => void stopTask()} disabled={!activeTaskId}>
              停止任务
            </button>
          </div>
          <div className="log-panel">
            {logs.length > 0 ? (
              logs.map((line, index) => (
                <div key={`${index}-${line.slice(0, 16)}`} className="log-line">
                  {line}
                </div>
              ))
            ) : (
              <FeedbackPanel title="等待任务日志" message="启动训练、提取或解码后，这里会持续显示执行输出。" tone="empty" compact />
            )}
          </div>
          {taskError instanceof Error ? <FeedbackPanel title="操作提交失败" message={taskError.message} tone="error" compact /> : null}
        </section>
      </div>
    </section>
  )
}
