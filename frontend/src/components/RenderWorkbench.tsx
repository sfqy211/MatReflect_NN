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
import type { RenderMode, RenderReconstructModel, RenderSourceModel, TaskEvent, TrainProjectVariant } from '../types/api'
import { GalleryPreview } from './GalleryPreview'
import { MaterialSelector } from './MaterialSelector'
import { TerminalDrawer } from './TerminalDrawer'
import { Badge } from './ui/Badge'
import { Button } from './ui/Button'
import { CheckboxField } from './ui/CheckboxField'
import { Field } from './ui/Field'


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
}

const INPUT_TYPE_LABELS: Record<RenderSourceModel, string> = {
  gt: '.binary / merl',
  neural: '.npy / nbrdf_npy',
  hyperbrdf: '.fullbin / fullmerl',
}

const RECONSTRUCT_NOTES: Record<RenderSourceModel, string> = {
  gt: 'GT 直接使用 MERL .binary，无需重建',
  neural: 'Neural-BRDF 一键重建会将 MERL .binary 转为 Mitsuba 可读的 .npy 权重组',
  hyperbrdf: 'HyperBRDF 一键重建会从 checkpoint 提取参数并解码为 .fullbin',
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
  const [search] = useState('')
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
  const needsCheckpoint = sourceModel === 'hyperbrdf'
  const projectVariant = needsCheckpoint ? (sourceModel as TrainProjectVariant) : null
  const isReconstructMode = canReconstruct && workflowMode === 'reconstruct'

  const scenesQuery = useRenderScenes(renderMode)
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
    if (scenesQuery.data?.default_scene) {
      setScenePath(scenesQuery.data.default_scene)
    }
  }, [renderMode, scenesQuery.data?.default_scene])

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
      model_key: (sourceModel === 'neural' ? 'neural' : sourceModel) as RenderReconstructModel,
      checkpoint_path: selectedRun?.checkpoint_path ?? '',
      merl_dir: materialsQuery.data?.resolved_path ?? 'data/inputs/binary',
      output_dir: sourceModel === 'neural' ? 'data/inputs/npy' : 'data/inputs/fullbin',
      selected_materials: selectedFiles,
      conda_env: sourceModel === 'hyperbrdf' ? 'hyperbrdf' : 'nbrdf-train',
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
      <div className="detail-pill-grid">
        {summaryChips.map((chip) => (
          <Badge key={chip} variant="detail">
            {chip}
          </Badge>
        ))}
      </div>

      <div className="render-layout">
        <section className="render-section">
          <div className="detail-board__lead">
            <h3>工作流面板</h3>
          </div>

          <div className="render-form-grid">
            <Field label="网络模型">
              <select value={sourceModel} onChange={(event) => setSourceModel(event.target.value as RenderSourceModel)}>
                <option value="gt">GT / MERL</option>
                <option value="neural">Neural-BRDF</option>
                <option value="hyperbrdf">HyperBRDF</option>
              </select>
            </Field>

            {canReconstruct ? (
              <Field label="工作模式">
                <select value={workflowMode} onChange={(event) => setWorkflowMode(event.target.value as WorkflowMode)}>
                  <option value="render">仅渲染</option>
                  <option value="reconstruct">仅重建</option>
                </select>
              </Field>
            ) : null}

            <Field label="场景">
              <select value={scenePath} onChange={(event) => setScenePath(event.target.value)}>
                {(scenesQuery.data?.items ?? []).map((scene) => (
                  <option key={scene.path} value={scene.path}>
                    {scene.label}
                  </option>
                ))}
              </select>
            </Field>

            <Field label="Integrator">
              <select value={integratorType} onChange={(event) => setIntegratorType(event.target.value)}>
                <option value="bdpt">bdpt</option>
                <option value="path">path</option>
                <option value="direct">direct</option>
              </select>
            </Field>

            <Field label="Sample Count">
              <input type="number" min={1} max={8192} value={sampleCount} onChange={(event) => setSampleCount(Number(event.target.value) || 1)} />
            </Field>
          </div>

          {isReconstructMode && needsCheckpoint ? (
            <div className="render-form-grid">
              <Field label="训练结果 / Checkpoint">
                <select value={selectedRunKey} onChange={(event) => setSelectedRunKey(event.target.value)}>
                  {availableRuns.map((run) => (
                    <option key={run.run_dir} value={run.run_dir}>
                      {run.run_name} / {run.completed_epochs} epochs
                    </option>
                  ))}
                </select>
              </Field>
            </div>
          ) : null}

          <div className="render-toggle-row">
            <CheckboxField label="自动转 PNG" checked={autoConvert} onChange={(event) => setAutoConvert(event.target.checked)} />
            <CheckboxField label="跳过已有结果" checked={skipExisting} onChange={(event) => setSkipExisting(event.target.checked)} />
            <CheckboxField label="自定义命令" checked={showCustomCmd} onChange={(event) => setShowCustomCmd(event.target.checked)} />
          </div>

          {showCustomCmd ? (
            <Field label="自定义命令">
              <input type="text" value={customCmd} onChange={(event) => setCustomCmd(event.target.value)} placeholder="{mitsuba} -o {output} {input}" />
            </Field>
          ) : null}

          <div className="render-form-grid">
            <Field label="渲染输入文件">
              <MaterialSelector
                title={isReconstructMode ? '选择待重建材质' : '选择渲染输入'}
                items={availableFiles}
                selectedItems={selectedFiles}
                onSelectionChange={setSelectedFiles}
                error={currentListError as Error | null}
                emptyMessage={isReconstructMode ? '请先准备 MERL .binary 材质。' : '请检查当前模型对应的渲染输入目录。'}
                searchPlaceholder={isReconstructMode ? '搜索待重建的 MERL 材质' : '搜索可渲染输入'}
                formatName={(name) => sourceModel === 'neural' && !isReconstructMode ? normalizeMaterialName(name) : name}
                presets={[
                  {
                    label: '预设20',
                    filter: (items) =>
                      items
                        .filter((item) => TEST_SET_20.includes(normalizeMaterialName(item.name)))
                        .map((item) => item.name)
                  }
                ]}
              />
            </Field>
          </div>

          <div className="render-actions">
            {isReconstructMode ? (
              <Button type="button" variant="primary" onClick={startReconstructAction} disabled={selectedFiles.length === 0 || (needsCheckpoint && !selectedRun)}>
                一键重建
              </Button>
            ) : (
              <Button type="button" variant="primary" onClick={startRenderAction} disabled={selectedFiles.length === 0}>
                开始渲染
              </Button>
            )}
            <Button type="button" variant="danger" onClick={stopRender} disabled={!activeTaskId}>
              停止任务
            </Button>
            {!isReconstructMode ? (
              <Button type="button" onClick={convertOutputs}>
                转换 EXR
              </Button>
            ) : null}
          </div>
        </section>

        <section className="render-section render-section--wide">
          <GalleryPreview items={outputsQuery.data?.items ?? []} isLoading={outputsQuery.isLoading} />
        </section>
      </div>
      <TerminalDrawer 
        taskId={activeTaskId} 
        status={currentStatus} 
        progress={progressValue} 
        logs={logs} 
        error={mutationError}
        onStop={stopRender}
        taskStateMessage={taskRecord?.status === 'failed' ? taskRecord.message : null}
      />
    </section>
  )
}
