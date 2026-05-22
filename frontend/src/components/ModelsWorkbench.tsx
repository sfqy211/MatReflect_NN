import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

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
import { ModelImportWizard } from './ModelImportWizard'
import { initParameterValues } from './ModelParameterForm'
import { TerminalDrawer } from './TerminalDrawer'
import { TerminalPanel } from './TerminalPanel'
import { DEFAULT_FULLBIN_OUTPUT } from './models/utils'
import { ModelGrid } from './models/ModelGrid'
import { ModelDetailHeader } from './models/ModelDetailHeader'
import { TrainTab } from './models/TrainTab'
import { ReconstructTab } from './models/ReconstructTab'
import { ExtractTab } from './models/ExtractTab'
import { DecodeTab } from './models/DecodeTab'

function getDefaultPath(model: TrainModelItem | null, field: string, fallback: string) {
  return model?.default_paths[field] ?? fallback
}

function getRuntimeValue(model: TrainModelItem | null, field: string, fallback = '') {
  return model?.runtime[field] ?? fallback
}

type ModelTab = 'train' | 'reconstruct' | 'extract' | 'decode'

export function ModelsWorkbench() {
  const queryClient = useQueryClient()

  // Grid / detail view state
  const [view, setView] = useState<'grid' | 'detail'>('grid')
  const [selectedModelKey, setSelectedModelKey] = useState('')

  // Form state
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
  const [terminalSessionId, setTerminalSessionId] = useState<string | null>(null)
  const [parameterValues, setParameterValues] = useState<Record<string, unknown>>({})
  const [showCommandsDoc, setShowCommandsDoc] = useState(false)

  // Split layout state — terminal left, operation panels right
  const [splitRatio, setSplitRatio] = useState(0.6)
  const [collapsedCards, setCollapsedCards] = useState<Set<ModelTab>>(new Set())
  const splitLayoutRef = useRef<HTMLDivElement>(null)

  const toggleCardCollapse = (tab: ModelTab) => {
    setCollapsedCards((prev) => {
      const next = new Set(prev)
      if (next.has(tab)) next.delete(tab)
      else next.add(tab)
      return next
    })
  }

  const modelQuery = useTrainModels()
  const materialsQuery = useMaterialsDirectory('')
  const activeModel = useMemo(
    () => modelQuery.data?.items.find((item) => item.key === selectedModelKey) ?? null,
    [selectedModelKey, modelQuery.data?.items],
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

  const materialItems = useMemo(() => materialsQuery.data?.items ?? [], [materialsQuery.data?.items])
  const h5Items = useMemo(() => h5FilesQuery.data?.items ?? [], [h5FilesQuery.data?.items])
  const ptItems = useMemo(() => ptFilesQuery.data?.items ?? [], [ptFilesQuery.data?.items])
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

  const tabLabels: Record<ModelTab, string> = {
    train: '训练',
    reconstruct: '重建',
    extract: '参数提取',
    decode: '潜向量解码',
  }

  // Splitter drag — terminal on left, panels on right
  const handleSplitterMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    const layout = splitLayoutRef.current
    if (!layout) return
    const rect = layout.getBoundingClientRect()
    const onMove = (ev: MouseEvent) => {
      const pos = ev.clientX - rect.left
      setSplitRatio(Math.min(0.75, Math.max(0.25, pos / rect.width)))
    }
    const onUp = () => {
      document.removeEventListener('mousemove', onMove)
      document.removeEventListener('mouseup', onUp)
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
    }
    document.addEventListener('mousemove', onMove)
    document.addEventListener('mouseup', onUp)
    document.body.style.cursor = 'col-resize'
    document.body.style.userSelect = 'none'
  }, [])

  const handleSelectModel = (key: string) => {
    setSelectedModelKey(key)
    setView('detail')
    setTerminalSessionId(`pty-${Date.now()}`)
  }

  const handleBackToGrid = () => {
    setView('grid')
    setSelectedModelKey('')
    setTerminalSessionId(null)
    setShowCommandsDoc(false)
    setSplitRatio(0.6)
    setCollapsedCards(new Set())
  }

  const applyRun = (run: TrainRunSummary) => {
    setSelectedModelKey(run.model_key)
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

  // ── Grid view ──
  if (view === 'grid') {
    const models = modelQuery.data?.items ?? []
    return (
      <section className="workspace-canvas" style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
        <ModelGrid
          models={models}
          onSelectModel={handleSelectModel}
          onDeleteModel={(key) => setDeleteConfirmKey(key)}
          onImport={() => setShowImportWizard(true)}
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
      </section>
    )
  }

  // ── Detail view ──
  if (!activeModel) {
    setView('grid')
    return null
  }

  const renderTabComponent = (tab: ModelTab) => {
    switch (tab) {
      case 'train':
        return (
          <TrainTab
            activeModel={activeModel}
            merlDir={merlDir}
            setMerlDir={setMerlDir}
            dataset={dataset}
            setDataset={setDataset}
            epochs={epochs}
            setEpochs={setEpochs}
            neuralDevice={neuralDevice}
            setNeuralDevice={setNeuralDevice}
            cudaDevice={cudaDevice}
            setCudaDevice={setCudaDevice}
            condaEnv={condaEnv}
            setCondaEnv={setCondaEnv}
            neuralOutputDir={neuralOutputDir}
            setNeuralOutputDir={setNeuralOutputDir}
            kerasH5Dir={kerasH5Dir}
            setKerasH5Dir={setKerasH5Dir}
            kerasNpyDir={kerasNpyDir}
            setKerasNpyDir={setKerasNpyDir}
            trainOutputDir={trainOutputDir}
            setTrainOutputDir={setTrainOutputDir}
            extractOutputDir={extractOutputDir}
            setExtractOutputDir={setExtractOutputDir}
            ptDir={ptDir}
            setPtDir={setPtDir}
            checkpointPath={checkpointPath}
            setCheckpointPath={setCheckpointPath}
            fullbinOutputDir={fullbinOutputDir}
            setFullbinOutputDir={setFullbinOutputDir}
            sparseSamples={sparseSamples}
            setSparseSamples={setSparseSamples}
            klWeight={klWeight}
            setKlWeight={setKlWeight}
            fwWeight={fwWeight}
            setFwWeight={setFwWeight}
            lr={lr}
            setLr={setLr}
            trainSubset={trainSubset}
            setTrainSubset={setTrainSubset}
            trainSeed={trainSeed}
            setTrainSeed={setTrainSeed}
            keepon={keepon}
            setKeepon={setKeepon}
            parameterValues={parameterValues}
            setParameterValues={setParameterValues}
            selectedMaterials={selectedMaterials}
            setSelectedMaterials={setSelectedMaterials}
            selectedH5Files={selectedH5Files}
            setSelectedH5Files={setSelectedH5Files}
            selectedPts={selectedPts}
            setSelectedPts={setSelectedPts}
            materialItems={materialItems}
            h5Items={h5Items}
            ptItems={ptItems}
            runs={runs}
            materialsQueryError={materialsQuery.error as Error | null}
            h5FilesQueryError={h5FilesQuery.error as Error | null}
            ptFilesQueryError={ptFilesQuery.error as Error | null}
            runsQueryError={runsQuery.error as Error | null}
            startTraining={() => void startTraining()}
            startH5Convert={() => void startH5Convert()}
            startExtract={() => void startExtract()}
            startDecode={() => void startDecode()}
            applyRun={applyRun}
          />
        )
      case 'reconstruct':
        return activeModel.supports_reconstruction ? (
          <ReconstructTab
            activeModel={activeModel}
            merlDir={merlDir}
            setMerlDir={setMerlDir}
            dataset={dataset}
            setDataset={setDataset}
            condaEnv={condaEnv}
            reconstructCondaEnv={reconstructCondaEnv}
            setReconstructCondaEnv={setReconstructCondaEnv}
            reconstructOutputDir={reconstructOutputDir}
            setReconstructOutputDir={setReconstructOutputDir}
            reconstructCheckpoint={reconstructCheckpoint}
            setReconstructCheckpoint={setReconstructCheckpoint}
            neuralDevice={neuralDevice}
            setNeuralDevice={setNeuralDevice}
            epochs={epochs}
            setEpochs={setEpochs}
            cudaDevice={cudaDevice}
            setCudaDevice={setCudaDevice}
            sparseSamples={sparseSamples}
            setSparseSamples={setSparseSamples}
            parameterValues={parameterValues}
            setParameterValues={setParameterValues}
            reconstructSelectedMaterials={reconstructSelectedMaterials}
            setReconstructSelectedMaterials={setReconstructSelectedMaterials}
            materialItems={materialItems}
            materialsQueryError={materialsQuery.error as Error | null}
            startReconstruct={() => void startReconstruct()}
            isReconstructPending={startReconstructMutation.isPending}
          />
        ) : null
      case 'extract':
        return activeModel.adapter === 'hyper-family' && activeModel.supports_extract ? (
          <ExtractTab
            activeModel={activeModel}
            merlDir={merlDir}
            setMerlDir={setMerlDir}
            checkpointPath={checkpointPath}
            setCheckpointPath={setCheckpointPath}
            extractOutputDir={extractOutputDir}
            setExtractOutputDir={setExtractOutputDir}
            setPtDir={setPtDir}
            condaEnv={condaEnv}
            setCondaEnv={setCondaEnv}
            dataset={dataset}
            setDataset={setDataset}
            sparseSamples={sparseSamples}
            setSparseSamples={setSparseSamples}
            trainSeed={trainSeed}
            setTrainSeed={setTrainSeed}
            selectedMaterials={selectedMaterials}
            setSelectedMaterials={setSelectedMaterials}
            materialItems={materialItems}
            materialsQueryError={materialsQuery.error as Error | null}
            startExtract={() => void startExtract()}
          />
        ) : null
      case 'decode':
        return activeModel.adapter === 'hyper-family' && activeModel.supports_decode ? (
          <DecodeTab
            activeModel={activeModel}
            ptDir={ptDir}
            setPtDir={setPtDir}
            fullbinOutputDir={fullbinOutputDir}
            setFullbinOutputDir={setFullbinOutputDir}
            condaEnv={condaEnv}
            setCondaEnv={setCondaEnv}
            cudaDevice={cudaDevice}
            setCudaDevice={setCudaDevice}
            dataset={dataset}
            setDataset={setDataset}
            selectedPts={selectedPts}
            setSelectedPts={setSelectedPts}
            ptItems={ptItems}
            ptFilesQueryError={ptFilesQuery.error as Error | null}
            startDecode={() => void startDecode()}
          />
        ) : null
    }
  }

  return (
    <section className="workspace-canvas" style={{ position: 'relative' }}>
      <ModelDetailHeader
        model={activeModel}
        onBack={handleBackToGrid}
        showCommandsDoc={showCommandsDoc}
        onToggleCommandsDoc={() => setShowCommandsDoc(!showCommandsDoc)}
        onSetupEnv={() => void handleSetupEnv()}
        setupEnvPending={setupEnvMutation.isPending}
        envStatus={envStatusQuery.data}
      />

      {/* Split layout: terminal left + operation panels right */}
      <div className="model-split-layout" ref={splitLayoutRef}>
        <div className="model-split-pane model-split-pane--terminal" style={{ width: `${splitRatio * 100}%` }}>
          <TerminalPanel
            sessionId={terminalSessionId}
            condaEnv={getRuntimeValue(activeModel, 'conda_env')}
            workingDir={getRuntimeValue(activeModel, 'working_dir')}
          />
        </div>
        <div className="model-splitter" onMouseDown={handleSplitterMouseDown} />
        <div className="model-split-pane model-split-pane--panels">
          {availableTabs.map((tab) => {
            const collapsed = collapsedCards.has(tab)
            return (
              <div key={tab} className={`model-floating-card${collapsed ? ' model-floating-card--collapsed' : ''}`}>
                <button
                  type="button"
                  className="model-floating-card__header"
                  onClick={() => toggleCardCollapse(tab)}
                >
                  <span className="model-floating-card__chevron">{collapsed ? '▸' : '▾'}</span>
                  <span className="model-floating-card__title">{tabLabels[tab]}</span>
                </button>
                {!collapsed && (
                  <div className="model-floating-card__body">
                    {renderTabComponent(tab)}
                  </div>
                )}
              </div>
            )
          })}
        </div>
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

      {/* Commands Documentation Panel */}
      {showCommandsDoc && activeModel.commands_doc && (
        <CommandsDocPanel
          docPath={activeModel.commands_doc}
          onClose={() => setShowCommandsDoc(false)}
        />
      )}
    </section>
  )
}
