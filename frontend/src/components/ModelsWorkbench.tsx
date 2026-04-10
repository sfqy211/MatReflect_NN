import { useEffect, useMemo, useState } from 'react'

import { useQueryClient } from '@tanstack/react-query'

import {
  useCreateTrainModel,
  useDeleteTrainModel,
  useMaterialsDirectory,
  useStartHyperDecode,
  useStartHyperExtract,
  useStartHyperRun,
  useStartNeuralH5Convert,
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
import { MaterialSelector } from './MaterialSelector'
import { TerminalDrawer } from './TerminalDrawer'
import { Badge } from './ui/Badge'
import { Button } from './ui/Button'
import { CheckboxField } from './ui/CheckboxField'
import { Field } from './ui/Field'


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
    adapter_options: {},
  }
}

import type { ModelsSubView } from '../App'

export function ModelsWorkbench({ activeSubView, onSubViewChange }: { activeSubView: ModelsSubView; onSubViewChange: (view: ModelsSubView) => void }) {
  const queryClient = useQueryClient()

  const activeModelKey = activeSubView === '__create__' ? '' : activeSubView
  const showCreateForm = activeSubView === '__create__'

  const [draft, setDraft] = useState<TrainModelCreateRequest>(() => buildDraft('hyper-family'))
  const [selectedMaterials, setSelectedMaterials] = useState<string[]>([])
  const [selectedH5Files, setSelectedH5Files] = useState<string[]>([])
  const [selectedPts, setSelectedPts] = useState<string[]>([])
  const [dataset, setDataset] = useState<'MERL' | 'EPFL'>('MERL')
  const [activeTaskId, setActiveTaskId] = useState<string | null>(null)
  const [liveLogs, setLiveLogs] = useState<string[]>([])
  const [, setNeuralEngine] = useState<NeuralTrainEngine>('pytorch')

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
  const [epochs, setEpochs] = useState(100)
  const [sparseSamples, setSparseSamples] = useState(4000)
  const [klWeight, setKlWeight] = useState(0.1)
  const [fwWeight, setFwWeight] = useState(0.1)
  const [lr, setLr] = useState(0.00005)
  const [trainSubset, setTrainSubset] = useState(80)
  const [trainSeed, setTrainSeed] = useState(42)
  const [keepon, setKeepon] = useState(false)



  const modelQuery = useTrainModels()
  const materialsQuery = useMaterialsDirectory('')
  const activeModel = useMemo(
    () => modelQuery.data?.items.find((item) => item.key === activeModelKey) ?? null,
    [activeModelKey, modelQuery.data?.items],
  )
  const runsQuery = useTrainRuns(activeModel?.supports_runs ? activeModel.key : null, Boolean(activeModel?.supports_runs))
  const h5FilesQuery = useWorkspaceFiles(kerasH5Dir, ['.h5'], '', activeModel?.adapter === 'neural-keras')
  const ptFilesQuery = useWorkspaceFiles(ptDir, ['.pt'], '', Boolean(activeModel?.supports_decode))
  const taskDetailQuery = useTrainTaskDetail(activeTaskId)

  const createTrainModel = useCreateTrainModel()
  const deleteTrainModel = useDeleteTrainModel()
  const startNeuralPytorch = useStartNeuralPytorch()
  const startNeuralKeras = useStartNeuralKeras()
  const startNeuralH5Convert = useStartNeuralH5Convert()
  const startHyperRun = useStartHyperRun()
  const startHyperExtract = useStartHyperExtract()
  const startHyperDecode = useStartHyperDecode()
  const stopTrainTask = useStopTrainTask()

  const materialItems = materialsQuery.data?.items ?? []
  const h5Items = h5FilesQuery.data?.items ?? []
  const ptItems = ptFilesQuery.data?.items ?? []
  const runs = activeModel?.supports_runs ? runsQuery.data?.items ?? [] : []
  const taskDetail = taskDetailQuery.data
  const taskRecord = taskDetail?.record

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
    setFullbinOutputDir(DEFAULT_FULLBIN_OUTPUT)
    setDataset('MERL')
  }, [activeModel?.key])

  useEffect(() => {
    const available = new Set(materialItems.map((item) => item.name))
    setSelectedMaterials((current) => current.filter((name) => available.has(name)))
  }, [materialItems])

  useEffect(() => {
    const available = new Set(h5Items.map((item) => item.name))
    setSelectedH5Files((current) => current.filter((name) => available.has(name)))
  }, [h5Items])

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
      `分类: ${activeModel?.category ?? '-'}`,
      `类型: ${activeModel?.built_in ? '内建' : '自定义'}`,
      `固定材质库: ${materialItems.length}`,
      `已选材质: ${selectedMaterials.length}`,
      `H5 文件: ${h5Items.length}`,
      `运行记录: ${runs.length}`,
      `PT 文件: ${ptItems.length}`,
    ],
    [activeModel?.adapter, activeModel?.label, activeModel?.category, activeModel?.built_in, h5Items.length, materialItems.length, ptItems.length, runs.length, selectedMaterials.length],
  )

  const logs = liveLogs.length > 0 ? liveLogs : taskDetail?.logs ?? []
  const currentStatus = taskRecord?.status ?? 'idle'
  const progressValue = taskRecord?.progress ?? 0
  const taskError =
    createTrainModel.error ??
    deleteTrainModel.error ??
    startNeuralPytorch.error ??
    startNeuralKeras.error ??
    startNeuralH5Convert.error ??
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



  const applyRun = (run: TrainRunSummary) => {
    onSubViewChange(run.model_key)
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
    onSubViewChange(response.item.key)
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
      onSubViewChange(fallback)
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

  const startH5Convert = async () => {
    if (!activeModel || activeModel.adapter !== 'neural-keras') {
      return
    }
    setLiveLogs([])
    const response = await startNeuralH5Convert.mutateAsync({
      model_key: activeModel.key,
      h5_dir: kerasH5Dir,
      selected_h5_files: selectedH5Files,
      npy_output_dir: kerasNpyDir,
      conda_env: condaEnv,
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
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '24px' }}>
        <div className="detail-pill-grid" style={{ marginBottom: 0, flex: 1 }}>
          {summaryChips.map((chip) => (
            <Badge key={chip} variant="detail">
              {chip}
            </Badge>
          ))}
        </div>
        {activeModel && !activeModel.built_in ? (
          <Button
            type="button"
            variant="danger"
            onClick={() => void removeModel(activeModel)}
            style={{ marginLeft: '16px', flexShrink: 0 }}
          >
            删除当前模型
          </Button>
        ) : null}
      </div>

      <div className="models-layout">

        {activeModel?.adapter === 'neural-keras' ? (
          <section className="models-section">
            <div className="detail-board__lead">
              <h3>H5 -&gt; NPY 转换</h3>
            </div>
            <div className="render-form-grid">
              <Field label="H5 目录">
              <input value={kerasH5Dir} onChange={(event) => setKerasH5Dir(event.target.value)} />
            </Field>
              <Field label="NPY 输出目录">
              <input value={kerasNpyDir} onChange={(event) => setKerasNpyDir(event.target.value)} />
            </Field>
              <Field label="Conda 环境">
              <input value={condaEnv} onChange={(event) => setCondaEnv(event.target.value)} />
            </Field>
            </div>
            <div className="render-form-grid" style={{ marginTop: '16px' }}>
              <Field label="H5 文件选择">
              <MaterialSelector
                  title="选择 H5 文件"
                  items={h5Items}
                  selectedItems={selectedH5Files}
                  onSelectionChange={setSelectedH5Files}
                  error={h5FilesQuery.error as Error | null}
                  emptyMessage="请先完成 Keras 训练，或检查 H5 目录是否正确。"
                  searchPlaceholder="搜索 .h5 文件"
                  formatName={(name) => name.replace(/\.h5$/i, '')}
                />
            </Field>
            </div>
            <div className="render-actions">
              <Button type="button" variant="primary" onClick={() => void startH5Convert()} disabled={selectedH5Files.length === 0}>
                执行 H5 -&gt; NPY 转换
              </Button>
            </div>
          </section>
        ) : null}

        <section className="models-section">
          <div className="detail-board__lead">
            <h3>固定材质选择</h3>
          </div>
          <div className="render-form-grid" style={{ marginTop: '16px' }}>
            <Field label="材质选择">
              <MaterialSelector
                title="选择固定材质"
                items={materialItems}
                selectedItems={selectedMaterials}
                onSelectionChange={setSelectedMaterials}
                error={materialsQuery.error as Error | null}
                emptyMessage="请检查 data/inputs/binary 下是否存在 .binary 文件。"
                searchPlaceholder="搜索 binary 材质"
                formatName={normalizeBinaryName}
                presets={[
                  {
                    label: '预设 20',
                    filter: (items) =>
                      items
                        .filter((item) => TEST_SET_20.includes(normalizeBinaryName(item.name)))
                        .map((item) => item.name)
                  }
                ]}
              />
            </Field>
          </div>
        </section>

        {showCreateForm ? (
          <section className="models-section models-section--wide">
            <div className="detail-board__lead">
              <h3>添加自建模型</h3>
              <p>基于现有适配器结构配置你的模型运行参数。</p>
            </div>
            <div className="render-form-grid">
              <Field label="模型 key">
              <input value={draft.key} onChange={(event) => updateDraft((current) => ({ ...current, key: event.target.value }))} />
            </Field>
              <Field label="显示名称">
              <input value={draft.label} onChange={(event) => updateDraft((current) => ({ ...current, label: event.target.value }))} />
            </Field>
              <Field label="适配器">
              <select value={draft.adapter} onChange={(event) => changeDraftAdapter(event.target.value as TrainModelAdapter)}>
                  <option value="hyper-family">hyper-family</option>
                  <option value="neural-pytorch">neural-pytorch</option>
                  <option value="neural-keras">neural-keras</option>
                </select>
            </Field>
              <Field label="说明">
              <input value={draft.description} onChange={(event) => updateDraft((current) => ({ ...current, description: event.target.value }))} />
            </Field>
            </div>

            <div className="render-form-grid">
              <Field label="Conda 环境">
              <input
                  value={draft.runtime.conda_env ?? ''}
                  onChange={(event) =>
                    updateDraft((current) => ({
                      ...current,
                      runtime: { ...current.runtime, conda_env: event.target.value },
                    }))
                  }
                />
            </Field>
              <Field label="工作目录">
              <input
                  value={draft.runtime.working_dir ?? ''}
                  onChange={(event) =>
                    updateDraft((current) => ({
                      ...current,
                      runtime: { ...current.runtime, working_dir: event.target.value },
                    }))
                  }
                />
            </Field>
              <Field label="训练脚本">
              <input
                  value={draft.runtime.train_script ?? ''}
                  onChange={(event) =>
                    updateDraft((current) => ({
                      ...current,
                      runtime: { ...current.runtime, train_script: event.target.value },
                    }))
                  }
                />
            </Field>
              {draft.adapter === 'neural-keras' ? (
                <Field label="转换脚本">
              <input
                    value={draft.runtime.convert_script ?? ''}
                    onChange={(event) =>
                      updateDraft((current) => ({
                        ...current,
                        runtime: { ...current.runtime, convert_script: event.target.value },
                      }))
                    }
                  />
            </Field>
              ) : null}
              {draft.adapter === 'hyper-family' ? (
                <>
                  <Field label="提取脚本">
              <input
                      value={draft.runtime.extract_script ?? ''}
                      onChange={(event) =>
                        updateDraft((current) => ({
                          ...current,
                          runtime: { ...current.runtime, extract_script: event.target.value },
                        }))
                      }
                    />
            </Field>
                  <Field label="解码脚本">
              <input
                      value={draft.runtime.decode_script ?? ''}
                      onChange={(event) =>
                        updateDraft((current) => ({
                          ...current,
                          runtime: { ...current.runtime, decode_script: event.target.value },
                        }))
                      }
                    />
            </Field>
                </>
              ) : null}
            </div>

            <div className="render-form-grid">
              <Field label="材质目录">
              <input
                  value={draft.default_paths.materials_dir ?? ''}
                  onChange={(event) =>
                    updateDraft((current) => ({
                      ...current,
                      default_paths: { ...current.default_paths, materials_dir: event.target.value },
                    }))
                  }
                />
            </Field>
              {draft.adapter === 'neural-pytorch' ? (
                <Field label="输出目录">
              <input
                    value={draft.default_paths.output_dir ?? ''}
                    onChange={(event) =>
                      updateDraft((current) => ({
                        ...current,
                        default_paths: { ...current.default_paths, output_dir: event.target.value },
                      }))
                    }
                  />
            </Field>
              ) : null}
              {draft.adapter === 'neural-keras' ? (
                <>
                  <Field label="H5 输出目录">
              <input
                      value={draft.default_paths.h5_output_dir ?? ''}
                      onChange={(event) =>
                        updateDraft((current) => ({
                          ...current,
                          default_paths: { ...current.default_paths, h5_output_dir: event.target.value },
                        }))
                      }
                    />
            </Field>
                  <Field label="NPY 输出目录">
              <input
                      value={draft.default_paths.npy_output_dir ?? ''}
                      onChange={(event) =>
                        updateDraft((current) => ({
                          ...current,
                          default_paths: { ...current.default_paths, npy_output_dir: event.target.value },
                        }))
                      }
                    />
            </Field>
                </>
              ) : null}
              {draft.adapter === 'hyper-family' ? (
                <>
                  <Field label="结果目录">
              <input
                      value={draft.default_paths.results_dir ?? ''}
                      onChange={(event) =>
                        updateDraft((current) => ({
                          ...current,
                          default_paths: { ...current.default_paths, results_dir: event.target.value },
                        }))
                      }
                    />
            </Field>
                  <Field label="PT 目录">
              <input
                      value={draft.default_paths.extract_dir ?? ''}
                      onChange={(event) =>
                        updateDraft((current) => ({
                          ...current,
                          default_paths: { ...current.default_paths, extract_dir: event.target.value },
                        }))
                      }
                    />
            </Field>
                  <Field label="默认 Checkpoint">
              <input
                      value={draft.default_paths.checkpoint ?? ''}
                      onChange={(event) =>
                        updateDraft((current) => ({
                          ...current,
                          default_paths: { ...current.default_paths, checkpoint: event.target.value },
                        }))
                      }
                    />
            </Field>
                </>
              ) : null}
            </div>

            {draft.adapter === 'hyper-family' ? (
              <div className="render-toggle-row" style={{ marginTop: '8px' }}>
                <CheckboxField label="支持参数提取" checked={draft.supports_extract} onChange={(event) => updateDraft((current) => ({ ...current, supports_extract: event.target.checked }))} />
                <CheckboxField label="支持 fullbin 解码" checked={draft.supports_decode} onChange={(event) => updateDraft((current) => ({ ...current, supports_decode: event.target.checked }))} />
                <CheckboxField label="支持运行记录扫描" checked={draft.supports_runs} onChange={(event) => updateDraft((current) => ({ ...current, supports_runs: event.target.checked }))} />
              </div>
            ) : null}

            <div className="render-actions">
              <Button type="button" variant="primary" onClick={() => void submitCreateModel()}>
                保存模型
              </Button>
              <Button type="button"  onClick={() => setDraft(buildDraft(draft.adapter))}>
                重置表单
              </Button>
            </div>
          </section>
        ) : null}

        <section className="models-section">
          <div className="detail-board__lead">
            <h3>训练入口</h3>
          </div>
          <div className="render-form-grid">
            <Field label="材质目录">
              <input value={merlDir} onChange={(event) => setMerlDir(event.target.value)} />
            </Field>
            <Field label="数据集">
              <select value={dataset} onChange={(event) => setDataset(event.target.value as 'MERL' | 'EPFL')} disabled={activeModel?.category === 'neural'}>
                <option value="MERL">MERL</option>
                <option value="EPFL">EPFL</option>
              </select>
            </Field>
            <Field label="Epochs">
              <input type="number" value={epochs} onChange={(event) => setEpochs(Number(event.target.value) || 1)} />
            </Field>
            <Field label="{activeModel?.category === 'neural' && neuralEngine === 'pytorch' ? '训练设备' : 'Conda 环境'}">
              {activeModel?.adapter === 'neural-pytorch' ? (
                <select value={neuralDevice} onChange={(event) => setNeuralDevice(event.target.value as 'cpu' | 'cuda')}>
                  <option value="cpu">cpu</option>
                  <option value="cuda">cuda</option>
                </select>
              ) : (
                <input value={condaEnv} onChange={(event) => setCondaEnv(event.target.value)} />
              )}
            </Field>
          </div>
          {activeModel?.adapter === 'neural-pytorch' ? (
            <div className="render-form-grid">
              <Field label="NPY 输出目录">
              <input value={neuralOutputDir} onChange={(event) => setNeuralOutputDir(event.target.value)} />
            </Field>
            </div>
          ) : null}
          {activeModel?.adapter === 'neural-keras' ? (
            <div className="render-form-grid">
              <Field label="CUDA 设备">
              <input value={cudaDevice} onChange={(event) => setCudaDevice(event.target.value)} />
            </Field>
              <Field label="H5 输出目录">
              <input value={kerasH5Dir} onChange={(event) => setKerasH5Dir(event.target.value)} />
            </Field>
              <Field label="NPY 输出目录">
              <input value={kerasNpyDir} onChange={(event) => setKerasNpyDir(event.target.value)} />
            </Field>
            </div>
          ) : null}
          {activeModel?.adapter === 'hyper-family' ? (
            <>
              <div className="render-form-grid">
                <Field label="训练结果目录">
              <input value={trainOutputDir} onChange={(event) => setTrainOutputDir(event.target.value)} />
            </Field>
                <Field label="稀疏采样点数">
              <input type="number" value={sparseSamples} onChange={(event) => setSparseSamples(Number(event.target.value) || 1)} />
            </Field>
                <Field label="KL 权重">
              <input type="number" step="0.01" value={klWeight} onChange={(event) => setKlWeight(Number(event.target.value) || 0)} />
            </Field>
                <Field label="FW 权重">
              <input type="number" step="0.01" value={fwWeight} onChange={(event) => setFwWeight(Number(event.target.value) || 0)} />
            </Field>
                <Field label="学习率">
              <input type="number" step="0.00001" value={lr} onChange={(event) => setLr(Number(event.target.value) || 0.00001)} />
            </Field>
                <Field label="训练材质数">
              <input type="number" value={trainSubset} onChange={(event) => setTrainSubset(Number(event.target.value) || 0)} />
            </Field>
              </div>
              <div className="render-toggle-row" style={{ marginTop: '8px' }}>
                <CheckboxField label="继续训练" checked={keepon} onChange={(event) => setKeepon(event.target.checked)} />
              </div>
            <div className="render-actions" style={{ marginTop: '12px' }}>
                <Button
                  type="button"
                  variant="primary"
                  onClick={() => void startTraining()}
                  disabled={!activeModel || (activeModel.category === 'neural' && selectedMaterials.length === 0)}
                >
                  启动训练
                </Button>
              </div>
            </>
          ) : (
            <div className="render-actions" style={{ marginTop: '12px' }}>
              <Button
                type="button"
                variant="primary"
                onClick={() => void startTraining()}
                disabled={!activeModel || (activeModel.category === 'neural' && selectedMaterials.length === 0)}
              >
                启动训练
              </Button>
            </div>
          )}
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
                  <Button type="button"  onClick={() => applyRun(run)} disabled={!run.has_checkpoint}>
                    应用 Checkpoint
                  </Button>
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
                  <Field label="Checkpoint">
              <input value={checkpointPath} onChange={(event) => setCheckpointPath(event.target.value)} />
            </Field>
                  <Field label="PT 输出目录">
              <input
                      value={extractOutputDir}
                      onChange={(event) => {
                        setExtractOutputDir(event.target.value)
                        setPtDir(event.target.value)
                      }}
                    />
            </Field>
                  <Field label="随机种子">
              <input type="number" value={trainSeed} onChange={(event) => setTrainSeed(Number(event.target.value) || 0)} />
            </Field>
                </div>
                <div className="render-actions">
                  <Button
                    type="button"
                    variant="primary"
                    onClick={() => void startExtract()}
                    disabled={dataset === 'MERL' && selectedMaterials.length === 0}
                  >
                    启动参数提取
                  </Button>
                </div>
              </section>
            ) : null}
            {activeModel.supports_decode ? (
              <section className="models-section">
                <div className="detail-board__lead">
                  <h3>PT 解码</h3>
                </div>
                <div className="render-form-grid">
                  <Field label="PT 目录">
              <input value={ptDir} onChange={(event) => setPtDir(event.target.value)} />
            </Field>
                  <Field label="FullBin 输出目录">
              <input value={fullbinOutputDir} onChange={(event) => setFullbinOutputDir(event.target.value)} />
            </Field>
                  <Field label="CUDA 设备">
              <input value={cudaDevice} onChange={(event) => setCudaDevice(event.target.value)} />
            </Field>
                </div>
                <div className="render-form-grid" style={{ marginTop: '16px' }}>
                  <Field label="PT 文件选择">
              <MaterialSelector
                      title="选择 PT 文件"
                      items={ptItems}
                      selectedItems={selectedPts}
                      onSelectionChange={setSelectedPts}
                      error={ptFilesQuery.error as Error | null}
                      emptyMessage="请先完成参数提取，或检查 PT 目录是否正确。"
                      searchPlaceholder="搜索已提取的 .pt 文件"
                      formatName={(name) => name.replace(/\.pt$/i, '')}
                    />
            </Field>
                </div>
                <div className="render-actions">
                  <Button type="button" variant="primary" onClick={() => void startDecode()} disabled={selectedPts.length === 0}>
                    执行 fullbin 解码
                  </Button>
                </div>
              </section>
            ) : null}
          </>
        ) : null}
      </div>
      <TerminalDrawer 
        taskId={activeTaskId} 
        status={currentStatus} 
        progress={progressValue} 
        logs={logs} 
        error={taskError}
        onStop={() => void stopTask()}
        taskStateMessage={taskStateMessage}
      />
    </section>
  )
}
