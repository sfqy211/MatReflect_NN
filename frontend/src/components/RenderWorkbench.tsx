import { useEffect, useMemo, useState } from 'react'

import { useQueryClient } from '@tanstack/react-query'

import { useMaterialsDirectory, useTrainRuns } from '../features/models/useModelsWorkbench'
import {
  useConvertOutputs,
  useRenderInputs,
  useRenderOutputs,
  useRenderScenes,
  useRenderTaskDetail,
  useStartReconstruct,
  useStartRender,
  useStopRender,
} from '../features/render/useRenderWorkbench'
import { BACKEND_ORIGIN } from '../lib/api'
import type { RenderMode, RenderSourceModel, TaskEvent, TrainProjectVariant } from '../types/api'
import { FeedbackPanel } from './FeedbackPanel'
import { GalleryPreview } from './GalleryPreview'


type WorkflowMode = 'render' | 'reconstruct'

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

const MODEL_LABELS: Record<RenderSourceModel, string> = {
  gt: 'GT / MERL 材质',
  neural: 'Neural-BRDF',
  hyperbrdf: 'HyperBRDF',
  decoupled: 'DecoupledHyperBRDF',
}

const INPUT_TYPE_LABELS: Record<RenderSourceModel, string> = {
  gt: '.binary / merl',
  neural: '.npy / nbrdf_npy',
  hyperbrdf: '.fullbin / fullmerl',
  decoupled: '.fullbin / fullmerl',
}

const RECONSTRUCT_NOTES: Record<RenderSourceModel, string> = {
  gt: 'GT 直接使用 MERL .binary，无需重建',
  neural: 'Neural-BRDF 一键重建会将 MERL .binary 转为 Mitsuba 可读的 .npy 权重组',
  hyperbrdf: 'HyperBRDF 一键重建会从 checkpoint 提取参数并解码为 .fullbin',
  decoupled: 'DecoupledHyperBRDF 一键重建会从 checkpoint 提取参数并解码为 .fullbin',
}

function getRenderMode(model: RenderSourceModel): RenderMode {
  if (model === 'gt') return 'brdfs'
  if (model === 'neural') return 'npy'
  return 'fullbin'
}

function normalizeMaterialName(fileName: string) {
  return fileName.replace(/(_fc1)?\.(binary|fullbin|npy)$/i, '')
}


export function RenderWorkbench() {
  const queryClient = useQueryClient()
  const [sourceModel, setSourceModel] = useState<RenderSourceModel>('gt')
  const [workflowMode, setWorkflowMode] = useState<WorkflowMode>('render')
  const [scenePath, setScenePath] = useState('')
  const [search, setSearch] = useState('')
  const [selectedFiles, setSelectedFiles] = useState<string[]>([])
  const [selectedRunKey, setSelectedRunKey] = useState('')
  const [integratorType, setIntegratorType] = useState('bdpt')
  const [sampleCount, setSampleCount] = useState(256)
  const [autoConvert, setAutoConvert] = useState(true)
  const [skipExisting, setSkipExisting] = useState(false)
  const [customCmd, setCustomCmd] = useState('')
  const [showCustomCmd, setShowCustomCmd] = useState(false)
  const [activeTaskId, setActiveTaskId] = useState<string | null>(null)
  const [liveLogs, setLiveLogs] = useState<string[]>([])

  const renderMode = useMemo(() => getRenderMode(sourceModel), [sourceModel])
  const canReconstruct = sourceModel !== 'gt'
  const needsCheckpoint = sourceModel === 'hyperbrdf' || sourceModel === 'decoupled'
  const projectVariant = needsCheckpoint ? (sourceModel as TrainProjectVariant) : null
  const isReconstructMode = canReconstruct && workflowMode === 'reconstruct'

  const scenesQuery = useRenderScenes()
  const renderInputsQuery = useRenderInputs(renderMode, search)
  const materialsQuery = useMaterialsDirectory(search)
  const runsQuery = useTrainRuns(projectVariant)
  const outputsQuery = useRenderOutputs(renderMode)
  const taskDetailQuery = useRenderTaskDetail(activeTaskId)
  const startRenderMutation = useStartRender()
  const startReconstructMutation = useStartReconstruct()
  const stopRenderMutation = useStopRender()
  const convertMutation = useConvertOutputs()

  const availableRuns = useMemo(
    () => (runsQuery.data?.items ?? []).filter((run) => run.has_checkpoint && run.dataset === 'MERL'),
    [runsQuery.data?.items],
  )
  const selectedRun = useMemo(
    () => availableRuns.find((run) => run.run_dir === selectedRunKey) ?? null,
    [availableRuns, selectedRunKey],
  )
  const availableFiles = isReconstructMode ? materialsQuery.data?.items ?? [] : renderInputsQuery.data?.items ?? []
  const currentListError = isReconstructMode ? materialsQuery.error : renderInputsQuery.error
  const taskDetail = taskDetailQuery.data
  const taskRecord = taskDetail?.record

  useEffect(() => {
    if (!scenePath && scenesQuery.data?.default_scene) {
      setScenePath(scenesQuery.data.default_scene)
    }
  }, [scenePath, scenesQuery.data])

  useEffect(() => {
    if (sourceModel === 'gt') {
      setWorkflowMode('render')
    }
  }, [sourceModel])

  useEffect(() => {
    const availableNames = new Set(availableFiles.map((item) => item.name))
    setSelectedFiles((current) => current.filter((name) => availableNames.has(name)))
  }, [availableFiles])

  useEffect(() => {
    if (!needsCheckpoint) {
      setSelectedRunKey('')
      return
    }
    if (selectedRunKey && availableRuns.some((run) => run.run_dir === selectedRunKey)) {
      return
    }
    setSelectedRunKey(availableRuns[0]?.run_dir ?? '')
  }, [availableRuns, needsCheckpoint, selectedRunKey])

  useEffect(() => {
    if (!taskDetail) {
      return
    }
    setLiveLogs(taskDetail.logs.slice(-120))
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
        setLiveLogs((current) => (current[current.length - 1] === payload.message ? current : [...current, payload.message].slice(-120)))
      }
      queryClient.invalidateQueries({ queryKey: ['render-task-detail', activeTaskId] })
      if (payload.event === 'done') {
        queryClient.invalidateQueries({ queryKey: ['render-outputs', renderMode] })
        queryClient.invalidateQueries({ queryKey: ['render-inputs', renderMode] })
      }
    }

    return () => socket.close()
  }, [activeTaskId, queryClient, renderMode])

  const selectedCount = selectedFiles.length
  const logs = liveLogs.length > 0 ? liveLogs : taskDetail?.logs ?? []
  const currentStatus =
    taskRecord?.status ??
    (startRenderMutation.isPending || startReconstructMutation.isPending || convertMutation.isPending ? 'pending' : 'idle')
  const progressValue = taskRecord?.progress ?? 0
  const mutationError =
    startRenderMutation.error ??
    startReconstructMutation.error ??
    stopRenderMutation.error ??
    convertMutation.error

  const summaryChips = useMemo(
    () => [
      `模型: ${MODEL_LABELS[sourceModel]}`,
      `Mitsuba 输入: ${INPUT_TYPE_LABELS[sourceModel]}`,
      `候选: ${availableFiles.length}`,
      `已选: ${selectedCount}`,
      `输出: ${outputsQuery.data?.total ?? 0}`,
      `重建说明: ${RECONSTRUCT_NOTES[sourceModel]}`,
    ],
    [availableFiles.length, outputsQuery.data?.total, selectedCount, sourceModel],
  )

  const toggleFile = (name: string) => {
    setSelectedFiles((current) => (current.includes(name) ? current.filter((item) => item !== name) : [...current, name]))
  }

  const applyPreset = () => {
    const presetSelection = availableFiles
      .filter((item) => TEST_SET_20.includes(normalizeMaterialName(item.name)))
      .map((item) => item.name)
    setSelectedFiles(presetSelection)
  }

  const startRenderAction = async () => {
    if (!scenePath || selectedFiles.length === 0) return
    setLiveLogs([])
    const response = await startRenderMutation.mutateAsync({
      render_mode: renderMode,
      scene_path: scenePath,
      selected_files: selectedFiles,
      integrator_type: integratorType,
      sample_count: sampleCount,
      auto_convert: autoConvert,
      skip_existing: skipExisting,
      custom_cmd: customCmd.trim() ? customCmd.trim() : null,
    })
    setActiveTaskId(response.task_id)
  }

  const startReconstructAction = async () => {
    if (selectedFiles.length === 0) return
    if (needsCheckpoint && !selectedRun) return
    setLiveLogs([])
    const response = await startReconstructMutation.mutateAsync({
      model_key: sourceModel === 'neural' ? 'neural' : (sourceModel as TrainProjectVariant),
      checkpoint_path: selectedRun?.checkpoint_path ?? '',
      merl_dir: materialsQuery.data?.resolved_path ?? 'data/inputs/binary',
      output_dir: sourceModel === 'neural' ? 'data/inputs/npy' : 'data/inputs/fullbin',
      selected_materials: selectedFiles,
      conda_env: sourceModel === 'decoupled' ? 'decoupledhyperbrdf' : sourceModel === 'hyperbrdf' ? 'hyperbrdf' : 'nbrdf-train',
      dataset: 'MERL',
      sparse_samples: Number(selectedRun?.args.sparse_samples ?? 4000),
      cuda_device: '0',
      neural_device: 'cpu',
      neural_epochs: 100,
      scene_path: scenePath,
      integrator_type: integratorType,
      sample_count: sampleCount,
      auto_convert: autoConvert,
      skip_existing: skipExisting,
      custom_cmd: customCmd.trim() ? customCmd.trim() : null,
      render_after_reconstruct: false,
    })
    setActiveTaskId(response.task_id)
  }

  const stopRender = async () => {
    if (!activeTaskId) return
    await stopRenderMutation.mutateAsync(activeTaskId)
    queryClient.invalidateQueries({ queryKey: ['render-task-detail', activeTaskId] })
  }

  const convertOutputs = async () => {
    setLiveLogs([])
    const response = await convertMutation.mutateAsync(renderMode)
    setActiveTaskId(response.task_id)
  }

  return (
    <section className="workspace-canvas">
      <div className="workspace-hero">
        <div>
          <h2>渲染可视化工作台</h2>
        </div>
      </div>

      <div className="detail-pill-grid">
        {summaryChips.map((chip) => (
          <span key={chip} className="detail-pill">
            {chip}
          </span>
        ))}
      </div>

      <div className="render-layout">
        <section className="render-section">
          <div className="detail-board__lead">
            <h3>工作流面板</h3>
          </div>

          <div className="render-form-grid">
            <label className="field">
              <span>网络模型</span>
              <select value={sourceModel} onChange={(event) => setSourceModel(event.target.value as RenderSourceModel)}>
                <option value="gt">GT / MERL</option>
                <option value="neural">Neural-BRDF</option>
                <option value="hyperbrdf">HyperBRDF</option>
                <option value="decoupled">DecoupledHyperBRDF</option>
              </select>
            </label>

            {canReconstruct ? (
              <label className="field">
                <span>工作模式</span>
                <select value={workflowMode} onChange={(event) => setWorkflowMode(event.target.value as WorkflowMode)}>
                  <option value="render">仅渲染</option>
                  <option value="reconstruct">仅重建</option>
                </select>
              </label>
            ) : null}

            <label className="field">
              <span>场景</span>
              <select value={scenePath} onChange={(event) => setScenePath(event.target.value)}>
                {(scenesQuery.data?.items ?? []).map((scene) => (
                  <option key={scene.path} value={scene.path}>
                    {scene.label}
                  </option>
                ))}
              </select>
            </label>

            <label className="field">
              <span>Integrator</span>
              <select value={integratorType} onChange={(event) => setIntegratorType(event.target.value)}>
                <option value="bdpt">bdpt</option>
                <option value="path">path</option>
                <option value="direct">direct</option>
              </select>
            </label>

            <label className="field">
              <span>Sample Count</span>
              <input type="number" min={1} max={8192} value={sampleCount} onChange={(event) => setSampleCount(Number(event.target.value) || 1)} />
            </label>
          </div>

          {isReconstructMode && needsCheckpoint ? (
            <div className="render-form-grid">
              <label className="field">
                <span>训练结果 / Checkpoint</span>
                <select value={selectedRunKey} onChange={(event) => setSelectedRunKey(event.target.value)}>
                  {availableRuns.map((run) => (
                    <option key={run.run_dir} value={run.run_dir}>
                      {run.run_name} / {run.completed_epochs} epochs
                    </option>
                  ))}
                </select>
              </label>
            </div>
          ) : null}

          <div className="render-toggle-row">
            <label className="toggle-field">
              <input type="checkbox" checked={autoConvert} onChange={(event) => setAutoConvert(event.target.checked)} />
              <span>自动转 PNG</span>
            </label>
            <label className="toggle-field">
              <input type="checkbox" checked={skipExisting} onChange={(event) => setSkipExisting(event.target.checked)} />
              <span>跳过已有结果</span>
            </label>
            <label className="toggle-field">
              <input type="checkbox" checked={showCustomCmd} onChange={(event) => setShowCustomCmd(event.target.checked)} />
              <span>自定义命令</span>
            </label>
          </div>

          {showCustomCmd ? (
            <label className="field">
              <span>自定义命令</span>
              <input type="text" value={customCmd} onChange={(event) => setCustomCmd(event.target.value)} placeholder="{mitsuba} -o {output} {input}" />
            </label>
          ) : null}

          <div className="file-toolbar">
            <input
              type="search"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder={isReconstructMode ? '搜索待重建的 MERL 材质' : '搜索可渲染输入'}
              className="search-input"
            />
            <div className="file-toolbar__actions">
              <button type="button" className="theme-toggle" onClick={() => setSelectedFiles(availableFiles.map((item) => item.name))}>
                全选
              </button>
              <button type="button" className="theme-toggle" onClick={applyPreset}>
                预设20
              </button>
              <button type="button" className="theme-toggle" onClick={() => setSelectedFiles([])}>
                清空
              </button>
            </div>
          </div>

          <div className="render-actions">
            {isReconstructMode ? (
              <button type="button" className="theme-toggle render-actions--primary" onClick={startReconstructAction} disabled={selectedFiles.length === 0 || (needsCheckpoint && !selectedRun)}>
                一键重建
              </button>
            ) : (
              <button type="button" className="theme-toggle render-actions--primary" onClick={startRenderAction} disabled={selectedFiles.length === 0}>
                开始渲染
              </button>
            )}
            <button type="button" className="theme-toggle render-actions--danger" onClick={stopRender} disabled={!activeTaskId}>
              停止任务
            </button>
            {!isReconstructMode ? (
              <button type="button" className="theme-toggle" onClick={convertOutputs}>
                转换 EXR
              </button>
            ) : null}
          </div>

          <div className="file-list">
            {currentListError instanceof Error ? (
              <FeedbackPanel
                title="输入列表读取失败"
                message={currentListError.message}
                tone="error"
                actionLabel="重新加载"
                onAction={() => {
                  void (isReconstructMode ? materialsQuery.refetch() : renderInputsQuery.refetch())
                }}
                compact
              />
            ) : null}

            {availableFiles.map((item) => (
              <label key={item.path} className="file-item">
                <input type="checkbox" checked={selectedFiles.includes(item.name)} onChange={() => toggleFile(item.name)} />
                <span>{sourceModel === 'neural' && !isReconstructMode ? normalizeMaterialName(item.name) : item.name}</span>
              </label>
            ))}

            {!currentListError && availableFiles.length === 0 ? (
              <FeedbackPanel title="当前没有可用输入" message={isReconstructMode ? '请先准备 MERL .binary 材质。' : '请检查当前模型对应的渲染输入目录。'} tone="empty" compact />
            ) : null}
          </div>
        </section>

        <section className="render-section render-section--wide">
          <GalleryPreview items={outputsQuery.data?.items ?? []} isLoading={outputsQuery.isLoading} />
        </section>

        <aside className="render-section">
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

          <div className="log-panel">
            {logs.length > 0 ? (
              logs.map((line, index) => (
                <div key={`${index}-${line.slice(0, 16)}`} className="log-line">
                  {line}
                </div>
              ))
            ) : (
              <FeedbackPanel title="等待任务日志" message="启动任务后，这里会持续显示执行输出。" tone="empty" compact />
            )}
          </div>

          {mutationError instanceof Error ? <FeedbackPanel title="操作提交失败" message={mutationError.message} tone="error" compact /> : null}
        </aside>
      </div>
    </section>
  )
}
