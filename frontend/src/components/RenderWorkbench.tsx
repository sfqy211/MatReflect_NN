import { useEffect, useMemo, useRef, useState } from 'react'

import { useQueryClient } from '@tanstack/react-query'

import { useAnalysisImages, useDeleteAnalysisImage } from '../features/analysis/useAnalysisWorkbench'
import {
  useConvertOutputs,
  useRenderInputs,
  useRenderScenes,
  useRenderTaskDetail,
  useStartRender,
  useStopRender,
} from '../features/render/useRenderWorkbench'
import { BACKEND_ORIGIN } from '../lib/api'
import type { AnalysisImageSet, RenderMode, RenderSourceModel, TaskEvent } from '../types/api'
import { FeedbackPanel } from './FeedbackPanel'
import { GalleryPreview } from './GalleryPreview'
import { MaterialSelector } from './MaterialSelector'
import { TerminalDrawer } from './TerminalDrawer'
import { Button } from './ui/Button'
import { CheckboxField } from './ui/CheckboxField'
import { Field } from './ui/Field'
import { ConfirmDialog } from './ConfirmDialog'


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

function getRenderMode(model: RenderSourceModel): RenderMode {
  if (model === 'gt') return 'brdfs'
  if (model === 'neural') return 'npy'
  return 'fullbin'
}

function getAnalysisImageSet(model: RenderSourceModel): AnalysisImageSet {
  if (model === 'gt') return 'brdfs'
  if (model === 'neural') return 'npy'
  return 'fullbin'
}

function normalizeMaterialName(fileName: string) {
  return fileName.replace(/(_fc1)?\.(binary|fullbin|npy)$/i, '')
}


export function RenderWorkbench() {
  const queryClient = useQueryClient()
  const resizableContainerRef = useRef<HTMLDivElement>(null)
  const [sourceModel, setSourceModel] = useState<RenderSourceModel>('gt')
  const [scenePath, setScenePath] = useState('')
  const [search] = useState('')
  const [selectedFiles, setSelectedFiles] = useState<string[]>([])
  const [integratorType, setIntegratorType] = useState('bdpt')
  const [sampleCount, setSampleCount] = useState(256)
  const [autoConvert, setAutoConvert] = useState(true)
  const [skipExisting, setSkipExisting] = useState(false)
  const [customCmd, setCustomCmd] = useState('')
  const [showCustomCmd, setShowCustomCmd] = useState(false)
  const [activeTaskId, setActiveTaskId] = useState<string | null>(null)
  const [liveLogs, setLiveLogs] = useState<string[]>([])
  const [outputSearch, setOutputSearch] = useState('')
  const [selectedOutputPaths, setSelectedOutputPaths] = useState<string[]>([])
  const [leftPaneWidth, setLeftPaneWidth] = useState(380)
  const [isDraggingSplitter, setIsDraggingSplitter] = useState(false)
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)

  const renderMode = useMemo(() => getRenderMode(sourceModel), [sourceModel])
  const analysisImageSet = useMemo(() => getAnalysisImageSet(sourceModel), [sourceModel])

  const scenesQuery = useRenderScenes(renderMode)
  const renderInputsQuery = useRenderInputs(renderMode, search)
  const outputGalleryQuery = useAnalysisImages(analysisImageSet, outputSearch)
  const taskDetailQuery = useRenderTaskDetail(activeTaskId)
  const startRenderMutation = useStartRender()
  const stopRenderMutation = useStopRender()
  const convertMutation = useConvertOutputs()
  const deleteImageMutation = useDeleteAnalysisImage()

  const availableFiles = renderInputsQuery.data?.items ?? []
  const outputItems = outputGalleryQuery.data?.items ?? []
  const taskDetail = taskDetailQuery.data
  const taskRecord = taskDetail?.record

  useEffect(() => {
    if (scenesQuery.data?.default_scene) {
      setScenePath(scenesQuery.data.default_scene)
    }
  }, [renderMode, scenesQuery.data?.default_scene])

  useEffect(() => {
    const availableNames = new Set(availableFiles.map((item) => item.name))
    setSelectedFiles((current) => current.filter((name) => availableNames.has(name)))
  }, [availableFiles])

  useEffect(() => {
    const availablePaths = new Set(outputItems.map((item) => item.path))
    setSelectedOutputPaths((current) => current.filter((path) => availablePaths.has(path)))
  }, [outputItems])

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
        queryClient.invalidateQueries({ queryKey: ['render-inputs', renderMode] })
        queryClient.invalidateQueries({ queryKey: ['analysis-images'] })
      }
    }

    return () => socket.close()
  }, [activeTaskId, queryClient, renderMode])

  useEffect(() => {
    if (!isDraggingSplitter) return

    const handleMouseMove = (e: MouseEvent) => {
      if (!resizableContainerRef.current) return
      const rect = resizableContainerRef.current.getBoundingClientRect()
      const newWidth = e.clientX - rect.left
      if (newWidth > 320 && newWidth < rect.width - 320) {
        setLeftPaneWidth(newWidth)
      }
    }

    const handleMouseUp = () => {
      setIsDraggingSplitter(false)
    }

    document.addEventListener('mousemove', handleMouseMove)
    document.addEventListener('mouseup', handleMouseUp)
    return () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
    }
  }, [isDraggingSplitter])

  const selectedCount = selectedFiles.length
  const selectedOutputNames = selectedOutputPaths
    .map((path) => outputItems.find((item) => item.path === path)?.name)
    .filter(Boolean) as string[]
  const logs = liveLogs.length > 0 ? liveLogs : taskDetail?.logs ?? []
  const currentStatus =
    taskRecord?.status ??
    (startRenderMutation.isPending || convertMutation.isPending ? 'pending' : 'idle')
  const progressValue = taskRecord?.progress ?? 0
  const mutationError =
    startRenderMutation.error ??
    stopRenderMutation.error ??
    convertMutation.error




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

  const stopRender = async () => {
    if (!activeTaskId) return
    await stopRenderMutation.mutateAsync(activeTaskId)
    queryClient.invalidateQueries({ queryKey: ['render-task-detail', activeTaskId] })
  }

  const convertOutputs = async () => {
    setLiveLogs([])
    const response = await convertMutation.mutateAsync(renderMode)
    setActiveTaskId(response.task_id)
    queryClient.invalidateQueries({ queryKey: ['analysis-images'] })
  }

  const deleteOutputs = async () => {
    if (selectedOutputPaths.length === 0) return
    setShowDeleteConfirm(false)
    await deleteImageMutation.mutateAsync({
      image_paths: selectedOutputPaths,
      delete_matching_exr: true,
    })
    setSelectedOutputPaths([])
    await queryClient.invalidateQueries({ queryKey: ['analysis-images'] })
  }

  return (
    <section className="workspace-canvas">
      <div className="render-layout">
        <div className="resizable-container render-resizable-container" ref={resizableContainerRef}>
          <section className="render-section render-resizable-pane render-resizable-pane--left" style={{ width: leftPaneWidth }}>
            <div className="render-form-grid" style={{ marginBottom: 16 }}>
              <div className="detail-board__lead" style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                <span className="eyebrow">当前状态</span>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px 12px', fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                  <span>就绪: <strong style={{ color: 'var(--text-strong)' }}>{availableFiles.length}</strong></span>
                  <span>已选: <strong style={{ color: 'var(--text-strong)' }}>{selectedCount}</strong></span>
                  <span>输出: <strong style={{ color: 'var(--text-strong)' }}>{outputGalleryQuery.data?.total ?? 0}</strong></span>
                </div>
              </div>
            </div>

          <div className="render-form-grid">
            <Field label="网络模型">
              <select value={sourceModel} onChange={(event) => setSourceModel(event.target.value as RenderSourceModel)}>
                <option value="gt">GT / 参考值</option>
                <option value="neural">Neural-BRDF 输出</option>
                <option value="hyperbrdf">HyperBRDF 输出</option>
              </select>
            </Field>

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
                title="选择渲染输入"
                items={availableFiles}
                selectedItems={selectedFiles}
                onSelectionChange={setSelectedFiles}
                error={renderInputsQuery.error as Error | null}
                emptyMessage="请检查当前模型对应的渲染输入目录。"
                searchPlaceholder="搜索可渲染输入"
                formatName={(name) => sourceModel === 'neural' ? normalizeMaterialName(name) : name}
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

          <div className="render-form-grid" style={{ marginTop: 24, borderTop: '1px solid var(--border)', paddingTop: 20 }}>
            <span className="eyebrow" style={{ marginBottom: 4 }}>输出图片过滤与管理</span>
            <Field label="输出搜索">
              <input
                type="text"
                value={outputSearch}
                onChange={(event) => setOutputSearch(event.target.value)}
                placeholder="搜索输出图片名"
              />
            </Field>
          </div>

          <div className="render-form-grid">
            <Field label="删除目标">
              <MaterialSelector
                title="选择要删除的输出图片"
                items={outputItems}
                selectedItems={selectedOutputNames}
                onSelectionChange={(selected) => {
                  const selectedPaths = selected
                    .map((name) => outputItems.find((item) => item.name === name)?.path)
                    .filter(Boolean) as string[]
                  setSelectedOutputPaths(selectedPaths)
                }}
                error={outputGalleryQuery.error as Error | null}
                emptyMessage="当前默认输出目录下没有图片，请检查设置页中的输出路径。"
                searchPlaceholder="搜索待删除图片"
              />
            </Field>
          </div>

          {deleteImageMutation.data ? (
            <p className="muted" style={{ marginBottom: 16 }}>
              已删除 {deleteImageMutation.data.deleted.length} 个文件
              {deleteImageMutation.data.missing.length > 0 ? `，未找到 ${deleteImageMutation.data.missing.length} 个文件` : ''}
            </p>
          ) : null}
          {deleteImageMutation.error instanceof Error ? <FeedbackPanel title="输出删除失败" message={deleteImageMutation.error.message} tone="error" compact /> : null}

          <div className="render-actions">
            <Button type="button" variant="primary" onClick={startRenderAction} disabled={selectedFiles.length === 0}>
              开始渲染
            </Button>
            <Button type="button" variant="danger" onClick={stopRender} disabled={!activeTaskId}>
              停止任务
            </Button>
            <Button type="button" onClick={convertOutputs}>
              转换 EXR
            </Button>
            <Button type="button" variant="danger" onClick={() => setShowDeleteConfirm(true)} disabled={selectedOutputPaths.length === 0 || deleteImageMutation.isPending}>
              删除选中
            </Button>
          </div>
          {showDeleteConfirm ? (
            <ConfirmDialog
              title="确认删除"
              message={`即将删除 ${selectedOutputPaths.length} 个文件，此操作不可撤销。`}
              onConfirm={deleteOutputs}
              onCancel={() => setShowDeleteConfirm(false)}
            />
          ) : null}
          </section>

          <div
            className={`splitter ${isDraggingSplitter ? 'splitter--dragging' : ''}`}
            onMouseDown={(e) => {
              e.preventDefault()
              setIsDraggingSplitter(true)
            }}
          />

          <section className="render-section render-section--wide render-resizable-pane render-resizable-pane--right">
            <GalleryPreview items={outputItems} isLoading={outputGalleryQuery.isLoading} />
          </section>
        </div>
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
