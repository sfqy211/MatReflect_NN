import { useEffect, useMemo, useState } from 'react'

import { useQueryClient } from '@tanstack/react-query'

import { BACKEND_ORIGIN } from '../lib/api'
import type { RenderMode, TaskEvent } from '../types/api'
import { FeedbackPanel } from './FeedbackPanel'
import { GalleryPreview } from './GalleryPreview'
import {
  useConvertOutputs,
  useRenderInputs,
  useRenderOutputs,
  useRenderScenes,
  useRenderTaskDetail,
  useStartRender,
  useStopRender,
} from '../features/render/useRenderWorkbench'


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

const MODE_LABELS: Record<RenderMode, string> = {
  brdfs: 'BRDF Binary',
  fullbin: 'FullBin',
  npy: 'NPY',
}


function normalizeMaterialName(fileName: string) {
  return fileName.replace(/(_fc1)?\.(binary|fullbin|npy)$/i, '')
}


export function RenderWorkbench() {
  const queryClient = useQueryClient()
  const [renderMode, setRenderMode] = useState<RenderMode>('brdfs')
  const [scenePath, setScenePath] = useState('')
  const [search, setSearch] = useState('')
  const [selectedFiles, setSelectedFiles] = useState<string[]>([])
  const [integratorType, setIntegratorType] = useState('bdpt')
  const [sampleCount, setSampleCount] = useState(256)
  const [autoConvert, setAutoConvert] = useState(true)
  const [skipExisting, setSkipExisting] = useState(false)
  const [customCmd, setCustomCmd] = useState('')
  const [activeTaskId, setActiveTaskId] = useState<string | null>(null)
  const [liveLogs, setLiveLogs] = useState<string[]>([])
  const [showLogs, setShowLogs] = useState(false)
  const [showCustomCmd, setShowCustomCmd] = useState(false)

  const scenesQuery = useRenderScenes()
  const inputsQuery = useRenderInputs(renderMode, search)
  const outputsQuery = useRenderOutputs(renderMode)
  const taskDetailQuery = useRenderTaskDetail(activeTaskId)
  const startRenderMutation = useStartRender()
  const stopRenderMutation = useStopRender()
  const convertMutation = useConvertOutputs()

  const availableFiles = inputsQuery.data?.items ?? []
  const taskDetail = taskDetailQuery.data
  const taskRecord = taskDetail?.record

  useEffect(() => {
    if (!scenePath && scenesQuery.data?.default_scene) {
      setScenePath(scenesQuery.data.default_scene)
    }
  }, [scenePath, scenesQuery.data])

  useEffect(() => {
    if (availableFiles.length === 0) {
      setSelectedFiles([])
      return
    }
    const availableNames = new Set(availableFiles.map((item) => item.name))
    setSelectedFiles((current) => current.filter((name) => availableNames.has(name)))
  }, [availableFiles])

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
        setLiveLogs((current) => {
          if (current[current.length - 1] === payload.message) {
            return current
          }
          return [...current, payload.message].slice(-120)
        })
      }
      queryClient.invalidateQueries({ queryKey: ['render-task-detail', activeTaskId] })
      if (payload.event === 'done') {
        queryClient.invalidateQueries({ queryKey: ['render-outputs', renderMode] })
      }
    }

    return () => {
      socket.close()
    }
  }, [activeTaskId, queryClient, renderMode])

  const selectedCount = selectedFiles.length
  const logs = liveLogs.length > 0 ? liveLogs : taskDetail?.logs ?? []
  const currentStatus = taskRecord?.status ?? (startRenderMutation.isPending || convertMutation.isPending ? 'pending' : 'idle')
  const progressValue = taskRecord?.progress ?? 0
  const mutationError = startRenderMutation.error ?? stopRenderMutation.error ?? convertMutation.error
  const taskStateMessage =
    taskRecord?.status === 'failed'
      ? taskRecord.message || '渲染任务执行失败，请检查日志和 Mitsuba 路径配置。'
      : taskRecord?.status === 'cancelled'
        ? taskRecord.message || '渲染任务已取消。'
        : null

  const startRender = async () => {
    if (!scenePath || selectedFiles.length === 0) {
      return
    }
    setLiveLogs([])
    setShowLogs(true)
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
    if (!activeTaskId) {
      return
    }
    await stopRenderMutation.mutateAsync(activeTaskId)
    queryClient.invalidateQueries({ queryKey: ['render-task-detail', activeTaskId] })
  }

  const convertOutputs = async () => {
    setLiveLogs([])
    setShowLogs(true)
    const response = await convertMutation.mutateAsync(renderMode)
    setActiveTaskId(response.task_id)
  }

  const applyPreset = () => {
    const presetSelection = availableFiles
      .filter((item) => TEST_SET_20.includes(normalizeMaterialName(item.name)))
      .map((item) => item.name)
    setSelectedFiles(presetSelection)
  }

  const toggleFile = (name: string, event?: React.MouseEvent) => {
    setSelectedFiles((current) => {
      const currentIndex = availableFiles.findIndex(f => f.name === name);
      
      if (event?.shiftKey && current.length > 0) {
        // Find the last clicked item in the current selection
        // Since we don't store the exact last clicked index reliably across renders without a ref,
        // we'll just use the last item in the current selection array as a heuristic
        const lastSelectedName = current[current.length - 1];
        const lastSelectedIndex = availableFiles.findIndex(f => f.name === lastSelectedName);
        
        if (lastSelectedIndex !== -1 && currentIndex !== -1) {
          const start = Math.min(lastSelectedIndex, currentIndex);
          const end = Math.max(lastSelectedIndex, currentIndex);
          
          const namesToSelect = availableFiles.slice(start, end + 1).map(f => f.name);
          
          // Add all names in range that aren't already selected
          const newSelection = [...current];
          for (const n of namesToSelect) {
            if (!newSelection.includes(n)) {
              newSelection.push(n);
            }
          }
          return newSelection;
        }
      }
      
      return current.includes(name) ? current.filter((item) => item !== name) : [...current, name];
    })
  }

  const summaryChips = useMemo(
    () => [
      `模式: ${MODE_LABELS[renderMode]}`,
      `文件数: ${availableFiles.length}`,
      `已选: ${selectedCount}`,
      `输出: ${outputsQuery.data?.total ?? 0}`,
    ],
    [availableFiles.length, outputsQuery.data?.total, renderMode, selectedCount],
  )

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
        <button
          type="button"
          className="detail-pill"
          onClick={() => setShowLogs((s) => !s)}
          style={{ cursor: 'pointer', background: showLogs ? 'var(--surface-strong)' : '' }}
        >
          {showLogs ? '隐藏日志面板' : '显示日志面板'}
        </button>
      </div>

      <div className={`render-layout ${showLogs ? '' : 'render-layout--no-logs'}`}>
        <section className="render-section">
          <div className="detail-board__lead">
            <h3>工作流面板</h3>
          </div>

          <div className="render-form-grid">
            <label className="field">
              <span>输入类型</span>
              <select value={renderMode} onChange={(event) => setRenderMode(event.target.value as RenderMode)}>
                <option value="brdfs">BRDF Binary</option>
                <option value="fullbin">FullBin</option>
                <option value="npy">NPY</option>
              </select>
            </label>

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
              <input
                type="number"
                min={1}
                max={8192}
                value={sampleCount}
                onChange={(event) => setSampleCount(Number(event.target.value) || 1)}
              />
            </label>
          </div>

          <div className="render-toggle-row">
            <label className="toggle-field">
              <input type="checkbox" checked={autoConvert} onChange={(event) => setAutoConvert(event.target.checked)} />
              <span>自动转 PNG</span>
            </label>
            <label className="toggle-field">
              <input type="checkbox" checked={skipExisting} onChange={(event) => setSkipExisting(event.target.checked)} />
              <span>跳过已存在结果</span>
            </label>
            <label className="toggle-field">
              <input type="checkbox" checked={showCustomCmd} onChange={(event) => setShowCustomCmd(event.target.checked)} />
              <span>开启自定义命令</span>
            </label>
          </div>

          {showCustomCmd && (
            <label className="field" style={{ animation: 'fadeIn 0.2s ease' }}>
              <span>自定义命令</span>
              <input
                type="text"
                value={customCmd}
                onChange={(event) => setCustomCmd(event.target.value)}
                placeholder="{mitsuba} -o {output} {input}"
              />
            </label>
          )}

          <div className="file-toolbar">
            <input
              type="search"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="搜索材质文件"
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
            <button
              type="button"
              className="theme-toggle render-actions--primary"
              onClick={startRender}
              disabled={selectedFiles.length === 0 || startRenderMutation.isPending}
            >
              启动渲染
            </button>
            <button type="button" className="theme-toggle render-actions--danger" onClick={stopRender} disabled={!activeTaskId || stopRenderMutation.isPending}>
              停止渲染
            </button>
            <button type="button" className="theme-toggle" onClick={convertOutputs} disabled={convertMutation.isPending}>
              转换EXR
            </button>
          </div>

          <div className="file-list">
            {inputsQuery.error instanceof Error ? (
              <FeedbackPanel
                title="输入列表读取失败"
                message={inputsQuery.error.message}
                tone="error"
                actionLabel="重新加载"
                onAction={() => {
                  void inputsQuery.refetch()
                }}
                compact
              />
            ) : null}
            {availableFiles.map((item) => (
              <label key={item.path} className="file-item" onClick={(e) => {
                e.preventDefault(); // Prevent default label behavior to handle shift click manually
                toggleFile(item.name, e);
              }}>
                <input type="checkbox" checked={selectedFiles.includes(item.name)} readOnly />
                <span>{item.name}</span>
              </label>
            ))}
            {!inputsQuery.error && availableFiles.length === 0 ? (
              <FeedbackPanel title="当前模式下没有可用输入文件" message="请检查输入目录是否已有对应格式的材质文件。" tone="empty" compact />
            ) : null}
          </div>
        </section>

        <section className="render-section render-section--wide">
          <GalleryPreview items={outputsQuery.data?.items ?? []} isLoading={outputsQuery.isLoading} />
        </section>

        {showLogs && (
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

            {taskStateMessage ? (
              <FeedbackPanel
                title={taskRecord?.status === 'failed' ? '渲染任务失败' : '渲染任务已取消'}
                message={taskStateMessage}
                tone={taskRecord?.status === 'failed' ? 'error' : 'info'}
                compact
              />
            ) : null}

            <div className="log-panel">
              {logs.length > 0 ? (
                logs.map((line, index) => (
                  <div key={`${index}-${line.slice(0, 16)}`} className="log-line">
                    {line}
                  </div>
                ))
              ) : (
                <FeedbackPanel title="等待任务日志" message="启动任务后会在这里持续推送执行日志。" tone="empty" compact />
              )}
            </div>

            {mutationError instanceof Error ? <FeedbackPanel title="操作提交失败" message={mutationError.message} tone="error" compact /> : null}
          </aside>
        )}
      </div>
    </section>
  )
}
