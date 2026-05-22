import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

import { useQueryClient } from '@tanstack/react-query'

import {
  useMaterialsDirectory,
  useStopTrainTask,
  useTrainModels,
  useTrainRuns,
  useTrainTaskDetail,
  useWorkspaceFiles,
  useImportModel,
  useDeleteModel,
  useModelEnvStatus,
  useSetupModelEnv,
  useExecuteOperation,
  usePreviewCommand,
} from '../features/models/useModelsWorkbench'
import { BACKEND_ORIGIN } from '../lib/api'
import type {
  OperationDef,
  TaskEvent,
  TrainRunSummary,
} from '../types/api'
import { CommandsDocPanel } from './CommandsDocPanel'
import { ConfirmDialog } from './ConfirmDialog'
import { ModelImportWizard } from './ModelImportWizard'
import { TerminalDrawer } from './TerminalDrawer'
import { TerminalPanel, type TerminalPanelHandle } from './TerminalPanel'
import { deriveOperations, getRuntimeValue } from './models/utils'
import { ModelGrid } from './models/ModelGrid'
import { ModelDetailHeader } from './models/ModelDetailHeader'
import { OperationForm } from './models/OperationForm'

/** 从操作定义初始化默认值 */
function initOperationValues(ops: OperationDef[]): Record<string, Record<string, unknown>> {
  const result: Record<string, Record<string, unknown>> = {}
  for (const op of ops) {
    const values: Record<string, unknown> = {}
    for (const field of op.form?.fields ?? []) {
      values[field.key] = field.default
    }
    result[op.key] = values
  }
  return result
}

/** 仅清除指定 file_source 对应的数组字段
 *  @param values    操作级 value 对象
 *  @param available 当前文件列表中的可用文件名
 *  @param sourceKey 要清洗的字段 key 集合 — 只清洗这些 key 的数组值
 */
function sanitizeFilePickerFields(
  values: Record<string, unknown>,
  available: Set<string>,
  sourceKeys: Set<string>,
): Record<string, unknown> {
  const next: Record<string, unknown> = {}
  for (const [key, val] of Object.entries(values)) {
    if (Array.isArray(val) && sourceKeys.has(key)) {
      next[key] = (val as string[]).filter((name) => available.has(name))
    } else {
      next[key] = val
    }
  }
  return next
}

/** 从一组 operation 定义中收集所有指定 file_source 对应的字段 key */
function collectFieldKeysForSource(ops: OperationDef[], source: string): Set<string> {
  const keys = new Set<string>()
  for (const op of ops) {
    for (const f of op.form?.fields ?? []) {
      if (f.type === 'file_picker' && f.file_source === source) {
        keys.add(f.key)
      }
    }
  }
  return keys
}

export function ModelsWorkbench() {
  const queryClient = useQueryClient()

  // ── Grid / detail view state ──
  const [view, setView] = useState<'grid' | 'detail'>('grid')
  const [selectedModelKey, setSelectedModelKey] = useState('')

  // ── Operation form state (keyed by operation key) ──
  const [operationValues, setOperationValues] = useState<Record<string, Record<string, unknown>>>({})

  // ── Task & terminal state ──
  const [activeTaskId, setActiveTaskId] = useState<string | null>(null)
  const [liveLogs, setLiveLogs] = useState<string[]>([])
  const [showImportWizard, setShowImportWizard] = useState(false)
  const [deleteConfirmKey, setDeleteConfirmKey] = useState<string | null>(null)
  const [terminalSessionId, setTerminalSessionId] = useState<string | null>(null)
  const [showCommandsDoc, setShowCommandsDoc] = useState(false)

  // ── Terminal ref for programmatic command dispatch ──
  const terminalRef = useRef<TerminalPanelHandle>(null)

  // ── Split layout state ──
  const [splitRatio, setSplitRatio] = useState(0.6)
  const [collapsedCards, setCollapsedCards] = useState<Set<string>>(new Set())
  const splitLayoutRef = useRef<HTMLDivElement>(null)

  const toggleCardCollapse = (tab: string) => {
    setCollapsedCards((prev) => {
      const next = new Set(prev)
      if (next.has(tab)) next.delete(tab)
      else next.add(tab)
      return next
    })
  }

  // ── Data queries ──
  const modelQuery = useTrainModels()
  const materialsQuery = useMaterialsDirectory('')

  const activeModel = useMemo(
    () => modelQuery.data?.items.find((item) => item.key === selectedModelKey) ?? null,
    [selectedModelKey, modelQuery.data?.items],
  )

  /** 当前模型的操作定义（优先使用 model.operations，否则从旧式标记派生） */
  const operations = useMemo(() => activeModel ? deriveOperations(activeModel) : [], [activeModel])

  const runsQuery = useTrainRuns(
    activeModel?.supports_runs ? activeModel.key : null,
    Boolean(activeModel?.supports_runs),
  )

  // Workspace file queries — only for operations that reference the respective file_source
  const needsH5 = useMemo(
    () => operations.some((op) => op.form?.fields?.some((f) => f.type === 'file_picker' && f.file_source === 'h5_files')),
    [operations],
  )
  const needsPt = useMemo(
    () => operations.some((op) => op.form?.fields?.some((f) => f.type === 'file_picker' && f.file_source === 'pt_files')),
    [operations],
  )
  const h5Dir = useMemo(
    () => {
      for (const op of operations) {
        for (const f of op.form?.fields ?? []) {
          if (f.key === 'h5_dir' || f.key === 'h5_output_dir') {
            const v = operationValues[op.key]?.[f.key]
            if (typeof v === 'string' && v.trim()) return v.trim()
          }
        }
      }
      return ''
    },
    [operations, operationValues],
  )
  const ptDir = useMemo(
    () => {
      for (const op of operations) {
        for (const f of op.form?.fields ?? []) {
          if (f.key === 'pt_dir' || f.key === 'extract_output_dir') {
            const v = operationValues[op.key]?.[f.key]
            if (typeof v === 'string' && v.trim()) return v.trim()
          }
        }
      }
      return ''
    },
    [operations, operationValues],
  )

  const h5FilesQuery = useWorkspaceFiles(h5Dir, ['.h5'], '', needsH5)
  const ptFilesQuery = useWorkspaceFiles(ptDir, ['.pt'], '', needsPt)
  const taskDetailQuery = useTrainTaskDetail(activeTaskId)

  // ── Mutations ──
  const executeOperation = useExecuteOperation()
  const previewCommand = usePreviewCommand()
  const stopTrainTask = useStopTrainTask()
  const importModelMutation = useImportModel()
  const deleteModelMutation = useDeleteModel()
  const setupEnvMutation = useSetupModelEnv()
  const envStatusQuery = useModelEnvStatus(activeModel ? activeModel.key : null)

  // ── Derived data ──
  const materialItems = useMemo(() => materialsQuery.data?.items ?? [], [materialsQuery.data?.items])
  const h5Items = useMemo(() => h5FilesQuery.data?.items ?? [], [h5FilesQuery.data?.items])
  const ptItems = useMemo(() => ptFilesQuery.data?.items ?? [], [ptFilesQuery.data?.items])
  const runs = activeModel?.supports_runs ? runsQuery.data?.items ?? [] : []
  const taskDetail = taskDetailQuery.data
  const taskRecord = taskDetail?.record

  /** 文件数据源，供 OperationForm 使用 */
  const fileItemsMap: Record<string, typeof materialItems> = useMemo(() => ({
    materials: materialItems,
    h5_files: h5Items,
    pt_files: ptItems,
  }), [materialItems, h5Items, ptItems])

  const fileErrorsMap: Record<string, Error | null> = useMemo(() => ({
    materials: materialsQuery.error as Error | null,
    h5_files: h5FilesQuery.error as Error | null,
    pt_files: ptFilesQuery.error as Error | null,
  }), [materialsQuery.error, h5FilesQuery.error, ptFilesQuery.error])

  // ── Initialize operationValues when model changes ──
  useEffect(() => {
    if (!activeModel) return
    setOperationValues(initOperationValues(operations))
  }, [activeModel?.key, operations])

  // ── Clean up file_picker selections only for the matching file_source ──
  const materialsKeys = useMemo(() => collectFieldKeysForSource(operations, 'materials'), [operations])
  const h5Keys = useMemo(() => collectFieldKeysForSource(operations, 'h5_files'), [operations])
  const ptKeys = useMemo(() => collectFieldKeysForSource(operations, 'pt_files'), [operations])

  useEffect(() => {
    if (materialsKeys.size === 0) return
    const available = new Set(materialItems.map((item) => item.name))
    setOperationValues((prev) => {
      const next = { ...prev }
      for (const opKey of Object.keys(next)) {
        next[opKey] = sanitizeFilePickerFields(next[opKey], available, materialsKeys)
      }
      return next
    })
  }, [materialItems, materialsKeys])

  useEffect(() => {
    if (h5Keys.size === 0 || !needsH5) return
    const available = new Set(h5Items.map((item) => item.name))
    setOperationValues((prev) => {
      const next = { ...prev }
      for (const opKey of Object.keys(next)) {
        next[opKey] = sanitizeFilePickerFields(next[opKey], available, h5Keys)
      }
      return next
    })
  }, [h5Items, needsH5, h5Keys])

  useEffect(() => {
    if (ptKeys.size === 0 || !needsPt) return
    const available = new Set(ptItems.map((item) => item.name))
    setOperationValues((prev) => {
      const next = { ...prev }
      for (const opKey of Object.keys(next)) {
        next[opKey] = sanitizeFilePickerFields(next[opKey], available, ptKeys)
      }
      return next
    })
  }, [ptItems, needsPt, ptKeys])

  // ── Task log sync (re-sync when task ID or log content changes) ──
  useEffect(() => {
    if (!taskDetail) return
    setLiveLogs(taskDetail.logs.slice(-160))
  }, [taskDetail?.record.task_id, taskDetail?.logs])

  // ── Task WebSocket ──
  useEffect(() => {
    if (!activeTaskId) return
    const wsProtocol = BACKEND_ORIGIN.startsWith('https') ? 'wss' : 'ws'
    const socket = new WebSocket(`${wsProtocol}://${new URL(BACKEND_ORIGIN).host}/ws/tasks/${activeTaskId}`)

    socket.onmessage = (event) => {
      const payload = JSON.parse(event.data) as TaskEvent
      if (payload.message) {
        setLiveLogs((current) => {
          if (current[current.length - 1] === payload.message) return current
          return [...current, payload.message].slice(-160)
        })
      }
      // 轻量刷新任务详情（轮询替代品 — 只更新内存中的 taskRecord）
      if (payload.event === 'snapshot' || payload.event === 'done') {
        queryClient.invalidateQueries({ queryKey: ['train-task-detail', activeTaskId] })
      }
      // runs/files 只在任务终结时刷新，避免每条日志都触发重取
      if (payload.event === 'done') {
        queryClient.invalidateQueries({ queryKey: ['train-runs'] })
        queryClient.invalidateQueries({ queryKey: ['workspace-files'] })
      }
    }

    return () => { socket.close() }
  }, [activeTaskId, queryClient])

  const logs = liveLogs.length > 0 ? liveLogs : taskDetail?.logs ?? []
  const currentStatus = taskRecord?.status ?? 'idle'
  const progressValue = taskRecord?.progress ?? 0
  const taskError = executeOperation.error ?? stopTrainTask.error
  const taskStateMessage =
    taskRecord?.status === 'failed'
      ? taskRecord.message || '任务执行失败，请检查环境、路径和日志输出。'
      : taskRecord?.status === 'cancelled'
        ? taskRecord.message || '任务已取消。'
        : null

  // ── Splitter drag ──
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

  // ── Navigation handlers ──
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
    // Fill values in reconstruct/train operations
    setOperationValues((prev) => {
      const next = { ...prev }
      for (const opKey of Object.keys(next)) {
        if (opKey === 'reconstruct' || opKey === 'extract') {
          // 同时填充 checkpoint 和 model_path，后端模板统一使用 model_path
          next[opKey] = { ...next[opKey], checkpoint: run.checkpoint_path, model_path: run.checkpoint_path, dataset: run.dataset === 'EPFL' ? 'EPFL' : 'MERL' }
        }
        if (opKey === 'train') {
          next[opKey] = { ...next[opKey], dataset: run.dataset === 'EPFL' ? 'EPFL' : 'MERL' }
        }
      }
      return next
    })
  }

  // ── Generic execute / preview ──
  const handleExecuteOperation = async (opKey: string, params: Record<string, unknown>) => {
    if (!activeModel) return
    setLiveLogs([])
    try {
      const response = await executeOperation.mutateAsync({
        model_key: activeModel.key,
        operation: opKey,
        params,
      })
      setActiveTaskId(response.task_id)
    } catch {
      // Error handled via executeOperation.error
    }
  }

  /** 将多命令 PreviewCommandResponse 格式化为可读的 Shell 脚本文本 */
  function formatCommandsAsScript(
    commands: Array<{ command: string[]; cwd?: string; conda_env?: string; step_index: number; step_label?: string }>,
  ): string {
    const lines: string[] = []
    for (const cmd of commands) {
      const cmdStr = cmd.command.join(' ')
      if (!cmdStr.trim()) continue
      if (cmd.step_label) {
        lines.push(`# === ${cmd.step_label} ===`)
      } else {
        lines.push(`# --- Step ${cmd.step_index} ---`)
      }
      if (cmd.cwd) {
        lines.push(`cd ${cmd.cwd}`)
      }
      if (cmd.conda_env) {
        lines.push(`conda activate ${cmd.conda_env}`)
      }
      lines.push(cmdStr)
      lines.push('')
    }
    return lines.join('\n')
  }

  const handlePreviewCommand = async (opKey: string, params: Record<string, unknown>) => {
    if (!activeModel) return
    try {
      const result = await previewCommand.mutateAsync({
        model_key: activeModel.key,
        operation: opKey,
        params,
      })
      const commands = result.commands ?? []
      if (commands.length === 0) {
        alert('预览结果为空，无命令可发送。')
        return
      }

      // 格式化为多行脚本文本
      const script = formatCommandsAsScript(commands)

      // Priority 1: send to terminal if connected (仅当只有一条简单命令时)
      const terminal = terminalRef.current
      const singleFlat = commands.length === 1 && commands[0].command.length <= 2
      if (terminal && singleFlat) {
        terminal.sendCommand(commands[0].command.join(' '))
        return
      }

      // Priority 2: 多命令/复杂命令 → 复制到剪贴板并给出提示
      try {
        await navigator.clipboard.writeText(script)
      } catch {
        // fallback: 无可用的 clipboard API
      }

      const stepCount = commands.length
      alert(
        `已生成 ${stepCount} 步命令，已复制到剪贴板。\n\n` +
        `如需执行，请粘贴到左侧终端运行。\n\n--- 预览 ---\n${script.slice(0, 600)}`,
      )
    } catch {
      // Error handled via previewCommand.error
    }
  }

  // ── Other handlers ──
  const stopTask = async () => {
    if (!activeTaskId) return
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

        {showImportWizard && (
          <div
            style={{
              position: 'fixed', inset: 0, zIndex: 900,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              background: 'rgba(0,0,0,0.5)',
            }}
            onClick={(e) => { if (e.target === e.currentTarget) setShowImportWizard(false) }}
          >
            <div
              style={{
                background: 'var(--surface-strong)',
                border: '1px solid var(--border)',
                borderRadius: 8,
                padding: 24,
                maxWidth: 720,
                width: '90%',
                maxHeight: '80vh',
                overflow: 'auto',
              }}
            >
              <ModelImportWizard
                onImport={(request) => void handleImportModel(request)}
                onCancel={() => setShowImportWizard(false)}
                isPending={importModelMutation.isPending}
              />
            </div>
          </div>
        )}

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
            ref={terminalRef}
            sessionId={terminalSessionId}
            condaEnv={getRuntimeValue(activeModel, 'conda_env')}
            workingDir={getRuntimeValue(activeModel, 'working_dir')}
          />
        </div>
        <div className="model-splitter" onMouseDown={handleSplitterMouseDown} />
        <div className="model-split-pane model-split-pane--panels">
          {/* ── Runs Card (only for models with supports_runs) ── */}
          {activeModel.supports_runs && (
            <div className="models-section" style={{ marginBottom: 8 }}>
              <div className="detail-board__lead">
                <h3>运行记录</h3>
              </div>
              <div className="runs-list">
                {runs.length === 0 && (
                  <span className="muted" style={{ fontSize: '0.85rem', padding: 8 }}>暂无运行记录</span>
                )}
                {runs.map((run) => (
                  <article key={`${run.model_key}-${run.run_dir}`} className="run-card">
                    <strong>{run.label}</strong>
                    <span>{run.run_name} — {run.dataset} / {run.completed_epochs} epochs</span>
                    <div className="render-actions" style={{ marginTop: 4 }}>
                      <button
                        type="button"
                        className="theme-toggle"
                        onClick={() => applyRun(run)}
                        disabled={!run.has_checkpoint}
                        style={{ fontSize: '0.8rem', padding: '4px 10px' }}
                      >
                        应用 Checkpoint
                      </button>
                    </div>
                  </article>
                ))}
              </div>
            </div>
          )}

          {/* ── Operation Cards ── */}
          {operations.map((op) => {
            const collapsed = collapsedCards.has(op.key)
            const values = operationValues[op.key] ?? {}
            return (
              <div
                key={op.key}
                className={`model-floating-card${collapsed ? ' model-floating-card--collapsed' : ''}`}
                style={{ marginBottom: 8 }}
              >
                <button
                  type="button"
                  className="model-floating-card__header"
                  onClick={() => toggleCardCollapse(op.key)}
                >
                  <span className="model-floating-card__chevron">{collapsed ? '▸' : '▾'}</span>
                  <span className="model-floating-card__title">{op.label}</span>
                </button>
                {!collapsed && (
                  <div className="model-floating-card__body">
                    <OperationForm
                      operation={op}
                      values={values}
                      onChange={(key, value) => {
                        setOperationValues((prev) => ({
                          ...prev,
                          [op.key]: { ...(prev[op.key] ?? {}), [key]: value },
                        }))
                      }}
                      onExecute={(vals) => void handleExecuteOperation(op.key, vals)}
                      onPreview={(vals) => void handlePreviewCommand(op.key, vals)}
                      isExecuting={executeOperation.isPending}
                      isPreviewing={previewCommand.isPending}
                      fileItemsMap={fileItemsMap}
                      fileErrorsMap={fileErrorsMap}
                    />
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

      {showCommandsDoc && activeModel.commands_doc && (
        <CommandsDocPanel
          docPath={activeModel.commands_doc}
          onClose={() => setShowCommandsDoc(false)}
        />
      )}
    </section>
  )
}
