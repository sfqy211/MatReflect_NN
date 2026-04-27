import { useEffect, useMemo, useState } from 'react'

import { useQueryClient } from '@tanstack/react-query'

import {
  useMaterialsDirectory,
  useStartHyperDecode,
  useStartHyperExtract,
  useStartHyperRun,
  useStartNeuralH5Convert,
  useStartNeuralKeras,
  useStartNeuralPytorch,
  useStartReconstruct,
  useStopTrainTask,
  useTrainModels,
  useTrainRuns,
  useTrainTaskDetail,
  useWorkspaceFiles,
  useImportModel,
  useDeleteModel,
  useModelEnvStatus,
  useSetupModelEnv,
} from '../features/models/useModelsWorkbench'
import { BACKEND_ORIGIN } from '../lib/api'
import type {
  NeuralTrainEngine,
  TaskEvent,
  TrainModelItem,
  TrainRunSummary,
} from '../types/api'
import { CommandsDocPanel } from './CommandsDocPanel'
import { ConfirmDialog } from './ConfirmDialog'
import { FeedbackPanel } from './FeedbackPanel'
import { ModelImportWizard } from './ModelImportWizard'
import { ModelParameterForm, initParameterValues } from './ModelParameterForm'
import { MaterialSelector } from './MaterialSelector'
import { TerminalDrawer } from './TerminalDrawer'
import { TerminalPanel } from './TerminalPanel'
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

type ModelTab = 'train' | 'reconstruct' | 'extract' | 'decode'

import type { ModelsSubView } from '../App'

export function ModelsWorkbench({ activeSubView, onSubViewChange }: { activeSubView: ModelsSubView; onSubViewChange: (view: ModelsSubView) => void }) {
  const queryClient = useQueryClient()

  const activeModelKey = activeSubView

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

  // Reconstruction, import, terminal states
  const [reconstructSelectedMaterials, setReconstructSelectedMaterials] = useState<string[]>([])
  const [reconstructCheckpoint, setReconstructCheckpoint] = useState('')
  const [reconstructCondaEnv, setReconstructCondaEnv] = useState('')
  const [reconstructOutputDir, setReconstructOutputDir] = useState('')
  const [showImportWizard, setShowImportWizard] = useState(false)
  const [deleteConfirmKey, setDeleteConfirmKey] = useState<string | null>(null)
  const [showTerminal, setShowTerminal] = useState(false)
  const [terminalSessionId, setTerminalSessionId] = useState<string | null>(null)
  const [parameterValues, setParameterValues] = useState<Record<string, unknown>>({})
  const [activeModelTab, setActiveModelTab] = useState<ModelTab>('train')
  const [showCommandsDoc, setShowCommandsDoc] = useState(false)

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

  const startNeuralPytorch = useStartNeuralPytorch()
  const startNeuralKeras = useStartNeuralKeras()
  const startNeuralH5Convert = useStartNeuralH5Convert()
  const startHyperRun = useStartHyperRun()
  const startHyperExtract = useStartHyperExtract()
  const startHyperDecode = useStartHyperDecode()
  const stopTrainTask = useStopTrainTask()
  const startReconstructMutation = useStartReconstruct()
  const importModelMutation = useImportModel()
  const deleteModelMutation = useDeleteModel()
  const setupEnvMutation = useSetupModelEnv()

  const envStatusQuery = useModelEnvStatus(activeModel?.supports_reconstruction ? activeModel.key : null)

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
    setReconstructCheckpoint(getDefaultPath(activeModel, 'checkpoint', ''))
    setReconstructCondaEnv(getRuntimeValue(activeModel, 'conda_env'))
    setReconstructOutputDir(getDefaultPath(activeModel, 'output_dir', ''))
    setDataset('MERL')
    setParameterValues(initParameterValues(activeModel.parameters ?? []))
    // Reset tab to train if current tab is not applicable
    if (activeModelTab === 'reconstruct' && !activeModel.supports_reconstruction) {
      setActiveModelTab('train')
    }
  }, [activeModel?.key])

  useEffect(() => {
    const available = new Set(materialItems.map((item) => item.name))
    setSelectedMaterials((current) => current.filter((name) => available.has(name)))
    setReconstructSelectedMaterials((current) => current.filter((name) => available.has(name)))
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
      `固定材质库: ${materialItems.length}`,
      `已选材质: ${selectedMaterials.length}`,
      `Keras 权重: ${h5Items.length}`,
      `运行记录: ${runs.length}`,
      `潜向量文件: ${ptItems.length}`,
    ],
    [activeModel?.adapter, activeModel?.label, activeModel?.category, h5Items.length, materialItems.length, ptItems.length, runs.length, selectedMaterials.length],
  )

  const logs = liveLogs.length > 0 ? liveLogs : taskDetail?.logs ?? []
  const currentStatus = taskRecord?.status ?? 'idle'
  const progressValue = taskRecord?.progress ?? 0
  const taskError =
    startNeuralPytorch.error ??
    startNeuralKeras.error ??
    startNeuralH5Convert.error ??
    startHyperRun.error ??
    startHyperExtract.error ??
    startHyperDecode.error ??
    startReconstructMutation.error ??
    stopTrainTask.error
  const taskStateMessage =
    taskRecord?.status === 'failed'
      ? taskRecord.message || '任务执行失败，请检查环境、路径和日志输出。'
      : taskRecord?.status === 'cancelled'
        ? taskRecord.message || '任务已取消。'
        : null

  const availableTabs = useMemo(() => {
    if (!activeModel) return ['train'] as ModelTab[]
    const tabs: ModelTab[] = ['train']
    if (activeModel.supports_reconstruction) tabs.push('reconstruct')
    if (activeModel.adapter === 'hyper-family' && activeModel.supports_extract) tabs.push('extract')
    if (activeModel.adapter === 'hyper-family' && activeModel.supports_decode) tabs.push('decode')
    return tabs
  }, [activeModel])

  const applyRun = (run: TrainRunSummary) => {
    onSubViewChange(run.model_key)
    setCheckpointPath(run.checkpoint_path)
    setReconstructCheckpoint(run.checkpoint_path)
    setDataset(run.dataset === 'EPFL' ? 'EPFL' : 'MERL')
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

  const startReconstruct = async () => {
    if (!activeModel) return
    setLiveLogs([])
    const response = await startReconstructMutation.mutateAsync({
      model_key: activeModel.key,
      checkpoint_path: reconstructCheckpoint,
      merl_dir: merlDir,
      output_dir: reconstructOutputDir,
      selected_materials: reconstructSelectedMaterials,
      conda_env: reconstructCondaEnv || condaEnv,
      dataset,
      sparse_samples: sparseSamples,
      cuda_device: cudaDevice,
      neural_device: neuralDevice,
      neural_epochs: epochs,
      scene_path: '',
      integrator_type: 'path',
      sample_count: 32,
      auto_convert: true,
      skip_existing: false,
      custom_cmd: null,
      render_after_reconstruct: false,
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

  const handleImportModel = async (request: Parameters<typeof importModelMutation.mutateAsync>[0]) => {
    await importModelMutation.mutateAsync(request)
    setShowImportWizard(false)
    queryClient.invalidateQueries({ queryKey: ['train-models'] })
  }

  const handleDeleteModel = async () => {
    if (!deleteConfirmKey) return
    await deleteModelMutation.mutateAsync(deleteConfirmKey)
    setDeleteConfirmKey(null)
    queryClient.invalidateQueries({ queryKey: ['train-models'] })
  }

  const handleSetupEnv = async () => {
    if (!activeModel) return
    await setupEnvMutation.mutateAsync(activeModel.key)
    queryClient.invalidateQueries({ queryKey: ['model-env-status'] })
  }

  const toggleTerminal = () => {
    if (showTerminal) {
      setShowTerminal(false)
      setTerminalSessionId(null)
    } else {
      const id = `pty-${Date.now()}`
      setTerminalSessionId(id)
      setShowTerminal(true)
    }
  }

  const tabLabels: Record<ModelTab, string> = {
    train: '训练',
    reconstruct: '重建',
    extract: '参数提取',
    decode: '潜向量解码',
  }

  return (
    <section className="workspace-canvas" style={{ position: 'relative' }}>
      <div style={{ marginBottom: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 8 }}>
          <div className="detail-pill-grid" style={{ marginBottom: 0, flex: 1 }}>
            {summaryChips.map((chip) => (
              <Badge key={chip} variant="detail">
                {chip}
              </Badge>
            ))}
          </div>
          <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
            <Button type="button" variant="primary" onClick={() => setShowImportWizard(true)} style={{ fontSize: '0.8rem' }}>
              + 导入模型
            </Button>
            {activeModel && !activeModel.built_in && (
              <Button type="button" onClick={() => setDeleteConfirmKey(activeModel.key)} style={{ fontSize: '0.8rem' }}>
                删除模型
              </Button>
            )}
            {activeModel && !activeModel.built_in && envStatusQuery.data && !envStatusQuery.data.env_exists && (
              <Button type="button" onClick={() => void handleSetupEnv()} disabled={setupEnvMutation.isPending} style={{ fontSize: '0.8rem' }}>
                {setupEnvMutation.isPending ? '创建环境中...' : '创建虚拟环境'}
              </Button>
            )}
            <Button type="button" onClick={toggleTerminal} style={{ fontSize: '0.8rem' }}>
              {showTerminal ? '关闭终端' : '终端'}
            </Button>
            {activeModel?.commands_doc && (
              <Button type="button" onClick={() => setShowCommandsDoc(!showCommandsDoc)} style={{ fontSize: '0.8rem' }}>
                {showCommandsDoc ? '关闭文档' : '命令文档'}
              </Button>
            )}
          </div>
        </div>
      </div>

      {/* Tab bar */}
      {availableTabs.length > 1 && (
        <div style={{ display: 'flex', gap: 0, marginBottom: 16, borderBottom: '1px solid var(--border)' }}>
          {availableTabs.map((tab) => (
            <button
              key={tab}
              type="button"
              onClick={() => setActiveModelTab(tab)}
              style={{
                padding: '8px 16px',
                border: 'none',
                borderBottom: activeModelTab === tab ? '2px solid var(--accent)' : '2px solid transparent',
                background: 'transparent',
                color: activeModelTab === tab ? 'var(--text-primary)' : 'var(--text-muted)',
                cursor: 'pointer',
                fontSize: '0.85rem',
                fontWeight: activeModelTab === tab ? 600 : 400,
              }}
            >
              {tabLabels[tab]}
            </button>
          ))}
        </div>
      )}

      <div className="models-layout">
        {/* ===================== TRAIN TAB ===================== */}
        {activeModelTab === 'train' && (
          <>
            {activeModel?.adapter === 'neural-keras' ? (
              <section className="models-section">
                <div className="detail-board__lead">
                  <h3>Keras 中间格式转换</h3>
                </div>
                <div className="render-form-grid">
                  <Field label="Keras 权重目录">
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
                  <Field label="Keras 权重文件">
                    <MaterialSelector
                      title="选择 Keras 权重文件"
                      items={h5Items}
                      selectedItems={selectedH5Files}
                      onSelectionChange={setSelectedH5Files}
                      error={h5FilesQuery.error as Error | null}
                      emptyMessage="请先完成 Keras 训练，或检查权重目录是否正确。"
                      searchPlaceholder="搜索 .h5 文件"
                      formatName={(name) => name.replace(/\.h5$/i, '')}
                    />
                  </Field>
                </div>
                <div className="render-actions">
                  <Button type="button" variant="primary" onClick={() => void startH5Convert()} disabled={selectedH5Files.length === 0}>
                    执行 Keras→NPY 转换
                  </Button>
                </div>
              </section>
            ) : null}

            <section className="models-section">
              <div className="detail-board__lead">
                <h3>MERL 材质库</h3>
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
                    searchPlaceholder="搜索 MERL 材质"
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
                <Field label={activeModel?.category === 'neural' && activeModel?.adapter === 'neural-pytorch' ? '训练设备' : 'Conda 环境'}>
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
              {/* Custom model parameters */}
              {activeModel?.adapter === 'custom-cli' && activeModel.parameters && activeModel.parameters.length > 0 && (
                <div style={{ marginTop: 12 }}>
                  <ModelParameterForm
                    parameters={activeModel.parameters}
                    values={parameterValues}
                    onChange={(key, value) => setParameterValues((prev) => ({ ...prev, [key]: value }))}
                  />
                </div>
              )}
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
                      <Button type="button" onClick={() => applyRun(run)} disabled={!run.has_checkpoint}>
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

            {/* Hyper-family extract/decode sections only in train tab */}
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
                      <h3>潜向量解码</h3>
                    </div>
                    <div className="render-form-grid">
                      <Field label="潜向量目录">
                        <input value={ptDir} onChange={(event) => setPtDir(event.target.value)} />
                      </Field>
                      <Field label="HyperBRDF 输出目录">
                        <input value={fullbinOutputDir} onChange={(event) => setFullbinOutputDir(event.target.value)} />
                      </Field>
                      <Field label="CUDA 设备">
                        <input value={cudaDevice} onChange={(event) => setCudaDevice(event.target.value)} />
                      </Field>
                    </div>
                    <div className="render-form-grid" style={{ marginTop: '16px' }}>
                      <Field label="潜向量文件">
                        <MaterialSelector
                          title="选择潜向量文件"
                          items={ptItems}
                          selectedItems={selectedPts}
                          onSelectionChange={setSelectedPts}
                          error={ptFilesQuery.error as Error | null}
                          emptyMessage="请先完成参数提取，或检查潜向量目录是否正确。"
                          searchPlaceholder="搜索已提取的 .pt 文件"
                          formatName={(name) => name.replace(/\.pt$/i, '')}
                        />
                      </Field>
                    </div>
                    <div className="render-actions">
                      <Button type="button" variant="primary" onClick={() => void startDecode()} disabled={selectedPts.length === 0}>
                        执行 HyperBRDF 解码
                      </Button>
                    </div>
                  </section>
                ) : null}
              </>
            ) : null}
          </>
        )}

        {/* ===================== RECONSTRUCT TAB ===================== */}
        {activeModelTab === 'reconstruct' && activeModel?.supports_reconstruction && (
          <section className="models-section">
            <div className="detail-board__lead">
              <h3>重建</h3>
            </div>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', margin: '0 0 12px' }}>
              从训练 Checkpoint 重建材质输出文件，重建完成后可前往渲染模块进行可视化。
            </p>
            <div className="render-form-grid">
              <Field label="材质目录">
                <input value={merlDir} onChange={(e) => setMerlDir(e.target.value)} />
              </Field>
              <Field label="数据集">
                <select value={dataset} onChange={(e) => setDataset(e.target.value as 'MERL' | 'EPFL')}>
                  <option value="MERL">MERL</option>
                  <option value="EPFL">EPFL</option>
                </select>
              </Field>
              <Field label="Conda 环境">
                <input value={reconstructCondaEnv} onChange={(e) => setReconstructCondaEnv(e.target.value)} placeholder={condaEnv || '自动检测'} />
              </Field>
              <Field label="输出目录">
                <input value={reconstructOutputDir} onChange={(e) => setReconstructOutputDir(e.target.value)} placeholder="默认由模型配置决定" />
              </Field>
            </div>

            {/* Adapter-specific fields */}
            {activeModel.adapter === 'neural-pytorch' && (
              <div className="render-form-grid" style={{ marginTop: 12 }}>
                <Field label="训练设备">
                  <select value={neuralDevice} onChange={(e) => setNeuralDevice(e.target.value as 'cpu' | 'cuda')}>
                    <option value="cpu">cpu</option>
                    <option value="cuda">cuda</option>
                  </select>
                </Field>
                <Field label="Epochs">
                  <input type="number" value={epochs} onChange={(e) => setEpochs(Number(e.target.value) || 1)} />
                </Field>
              </div>
            )}
            {activeModel.adapter === 'hyper-family' && (
              <div className="render-form-grid" style={{ marginTop: 12 }}>
                <Field label="Checkpoint">
                  <input value={reconstructCheckpoint} onChange={(e) => setReconstructCheckpoint(e.target.value)} />
                </Field>
                <Field label="CUDA 设备">
                  <input value={cudaDevice} onChange={(e) => setCudaDevice(e.target.value)} />
                </Field>
                <Field label="稀疏采样点数">
                  <input type="number" value={sparseSamples} onChange={(e) => setSparseSamples(Number(e.target.value) || 1)} />
                </Field>
              </div>
            )}
            {activeModel.adapter === 'custom-cli' && (
              <div className="render-form-grid" style={{ marginTop: 12 }}>
                <Field label="Checkpoint">
                  <input value={reconstructCheckpoint} onChange={(e) => setReconstructCheckpoint(e.target.value)} />
                </Field>
                {activeModel.parameters && activeModel.parameters.length > 0 && (
                  <ModelParameterForm
                    parameters={activeModel.parameters}
                    values={parameterValues}
                    onChange={(key, value) => setParameterValues((prev) => ({ ...prev, [key]: value }))}
                  />
                )}
              </div>
            )}

            {/* Material selection */}
            <div style={{ marginTop: 16 }}>
              <Field label="重建材质">
                <MaterialSelector
                  title="选择需要重建的材质"
                  items={materialItems}
                  selectedItems={reconstructSelectedMaterials}
                  onSelectionChange={setReconstructSelectedMaterials}
                  error={materialsQuery.error as Error | null}
                  emptyMessage="请检查 data/inputs/binary 下是否存在 .binary 文件。"
                  searchPlaceholder="搜索 MERL 材质"
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

            <div className="render-actions" style={{ marginTop: 12 }}>
              <Button
                type="button"
                variant="primary"
                onClick={() => void startReconstruct()}
                disabled={reconstructSelectedMaterials.length === 0 || startReconstructMutation.isPending}
              >
                {startReconstructMutation.isPending ? '重建中...' : '启动重建'}
              </Button>
            </div>
          </section>
        )}

        {/* ===================== EXTRACT TAB ===================== */}
        {activeModelTab === 'extract' && activeModel?.adapter === 'hyper-family' && activeModel.supports_extract && (
          <section className="models-section">
            <div className="detail-board__lead">
              <h3>参数提取</h3>
            </div>
            <div className="render-form-grid">
              <Field label="材质目录">
                <input value={merlDir} onChange={(event) => setMerlDir(event.target.value)} />
              </Field>
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
              <Field label="Conda 环境">
                <input value={condaEnv} onChange={(event) => setCondaEnv(event.target.value)} />
              </Field>
              <Field label="数据集">
                <select value={dataset} onChange={(event) => setDataset(event.target.value as 'MERL' | 'EPFL')}>
                  <option value="MERL">MERL</option>
                  <option value="EPFL">EPFL</option>
                </select>
              </Field>
              <Field label="稀疏采样点数">
                <input type="number" value={sparseSamples} onChange={(event) => setSparseSamples(Number(event.target.value) || 1)} />
              </Field>
              <Field label="随机种子">
                <input type="number" value={trainSeed} onChange={(event) => setTrainSeed(Number(event.target.value) || 0)} />
              </Field>
            </div>
            <div style={{ marginTop: 16 }}>
              <Field label="材质选择">
                <MaterialSelector
                  title="选择固定材质"
                  items={materialItems}
                  selectedItems={selectedMaterials}
                  onSelectionChange={setSelectedMaterials}
                  error={materialsQuery.error as Error | null}
                  emptyMessage="请检查 data/inputs/binary 下是否存在 .binary 文件。"
                  searchPlaceholder="搜索 MERL 材质"
                  formatName={normalizeBinaryName}
                />
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
        )}

        {/* ===================== DECODE TAB ===================== */}
        {activeModelTab === 'decode' && activeModel?.adapter === 'hyper-family' && activeModel.supports_decode && (
          <section className="models-section">
            <div className="detail-board__lead">
              <h3>潜向量解码</h3>
            </div>
            <div className="render-form-grid">
              <Field label="潜向量目录">
                <input value={ptDir} onChange={(event) => setPtDir(event.target.value)} />
              </Field>
              <Field label="HyperBRDF 输出目录">
                <input value={fullbinOutputDir} onChange={(event) => setFullbinOutputDir(event.target.value)} />
              </Field>
              <Field label="Conda 环境">
                <input value={condaEnv} onChange={(event) => setCondaEnv(event.target.value)} />
              </Field>
              <Field label="CUDA 设备">
                <input value={cudaDevice} onChange={(event) => setCudaDevice(event.target.value)} />
              </Field>
              <Field label="数据集">
                <select value={dataset} onChange={(event) => setDataset(event.target.value as 'MERL' | 'EPFL')}>
                  <option value="MERL">MERL</option>
                  <option value="EPFL">EPFL</option>
                </select>
              </Field>
            </div>
            <div style={{ marginTop: 16 }}>
              <Field label="潜向量文件">
                <MaterialSelector
                  title="选择潜向量文件"
                  items={ptItems}
                  selectedItems={selectedPts}
                  onSelectionChange={setSelectedPts}
                  error={ptFilesQuery.error as Error | null}
                  emptyMessage="请先完成参数提取，或检查潜向量目录是否正确。"
                  searchPlaceholder="搜索已提取的 .pt 文件"
                  formatName={(name) => name.replace(/\.pt$/i, '')}
                />
              </Field>
            </div>
            <div className="render-actions">
              <Button type="button" variant="primary" onClick={() => void startDecode()} disabled={selectedPts.length === 0}>
                执行 HyperBRDF 解码
              </Button>
            </div>
          </section>
        )}
      </div>

      {/* PTY Terminal panel */}
      {showTerminal && (
        <div style={{
          marginTop: 16,
          border: '1px solid var(--border)',
          borderRadius: 6,
          overflow: 'hidden',
          height: 260,
        }}>
          <TerminalPanel
            sessionId={terminalSessionId}
            onClose={() => { setShowTerminal(false); setTerminalSessionId(null) }}
          />
        </div>
      )}

      <TerminalDrawer 
        taskId={activeTaskId} 
        status={currentStatus} 
        progress={progressValue} 
        logs={logs} 
        error={taskError}
        onStop={() => void stopTask()}
        taskStateMessage={taskStateMessage}
      />

      {/* Model Import Wizard */}
      {showImportWizard && (
        <div style={{
          position: 'fixed', inset: 0, zIndex: 900,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          background: 'rgba(0,0,0,0.5)',
        }} onClick={(e) => { if (e.target === e.currentTarget) setShowImportWizard(false) }}>
          <div style={{
            background: 'var(--surface-strong)',
            border: '1px solid var(--border)',
            borderRadius: 8,
            padding: 24,
            maxWidth: 720,
            width: '90%',
            maxHeight: '80vh',
            overflow: 'auto',
          }}>
            <ModelImportWizard
              onImport={(request) => void handleImportModel(request)}
              onCancel={() => setShowImportWizard(false)}
              isPending={importModelMutation.isPending}
            />
          </div>
        </div>
      )}

      {/* Delete Confirm Dialog */}
      {deleteConfirmKey && (
        <ConfirmDialog
          title="确认删除模型"
          message={`即将删除自定义模型 "${deleteConfirmKey}"，该操作将移除模型目录和注册信息，且不可恢复。`}
          confirmLabel="确认删除"
          variant="danger"
          onConfirm={() => void handleDeleteModel()}
          onCancel={() => setDeleteConfirmKey(null)}
        />
      )}

      {/* Commands Documentation Panel */}
      {showCommandsDoc && activeModel?.commands_doc && (
        <CommandsDocPanel
          docPath={activeModel.commands_doc}
          onClose={() => setShowCommandsDoc(false)}
        />
      )}
    </section>
  )
}
