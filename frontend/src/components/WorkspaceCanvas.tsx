import { useEffect, useMemo, useState } from 'react'

import { useQueryClient } from '@tanstack/react-query'

import type { AnalysisSubView, ModelsSubView } from '../App'
import { BACKEND_ORIGIN } from '../lib/api'
import { parseAssetName } from '../lib/fileNames'
import type { FileListItem, ModuleKey, SystemDependencySetting, SystemSummary, SystemVirtualEnvSetting, TaskEvent } from '../types/api'
import {
  useCheckSystemSettings,
  useSaveSystemSettings,
  useStartSystemCompile,
  useStopSystemCompile,
  useSystemCompileTaskDetail,
} from '../features/system/useSystemSummary'
import { AnalysisWorkbench } from './AnalysisWorkbench'
import { FeedbackPanel } from './FeedbackPanel'
import { ModelsWorkbench } from './ModelsWorkbench'
import { RenderWorkbench } from './RenderWorkbench'
import { TerminalDrawer } from './TerminalDrawer'
import { Badge } from './ui/Badge'
import { Button } from './ui/Button'
import { Card } from './ui/Card'
import { Field } from './ui/Field'

type WorkspaceCanvasProps = {
  activeModule: ModuleKey
  activeAnalysisSubView: AnalysisSubView
  onAnalysisSubViewChange: (view: AnalysisSubView) => void
  activeModelsSubView: ModelsSubView
  onModelsSubViewChange: (view: ModelsSubView) => void
  galleryItems: FileListItem[]
  galleryCount: number
  system?: SystemSummary
  systemError?: string
  systemLoading: boolean
}

type ActionSpec = {
  key: string
  label: string
  settings: string[]
}

type ModuleMeta = {
  title: string
  actions: ActionSpec[]
}

const moduleMeta: Record<Exclude<ModuleKey, 'settings'>, ModuleMeta> = {
  render: {
    title: '渲染可视化工作台',
    actions: [
      {
        key: 'scene',
        label: '场景与输入配置',
        settings: ['Scene XML selector', 'Input mode switch', 'Selected file list', 'Skip existing / auto convert'],
      },
      {
        key: 'quality',
        label: '采样与渲染参数',
        settings: ['Integrator type', 'Sample count', 'Output routing', 'Custom render command'],
      },
      {
        key: 'review',
        label: '输出转换与结果',
        settings: ['EXR -> PNG convert', 'Recent output gallery', 'Task log snapshot', 'Open in analysis'],
      },
    ],
  },
  analysis: {
    title: '材质表达结果分析',
    actions: [
      {
        key: 'metrics',
        label: '表达结果对比',
        settings: ['Reference set', 'Compared outputs', 'Error metric selection', 'Batch evaluation'],
      },
      {
        key: 'slider',
        label: '图像滑块检查',
        settings: ['Before / after pair', 'Region zoom', 'Linked cursor', 'Channel emphasis'],
      },
      {
        key: 'report',
        label: '拼图与报告',
        settings: ['Grid montage', 'Comparison board', 'Summary annotation', 'Export snapshot'],
      },
    ],
  },
  models: {
    title: '网络模型管理',
    actions: [
      {
        key: 'preset',
        label: '新建训练方案',
        settings: ['Model family', 'Dataset routing', 'Training hyper-params', 'Launch command'],
      },
      {
        key: 'runs',
        label: '运行记录',
        settings: ['Run list', 'Latest checkpoints', 'Failure note', 'Resume action'],
      },
      {
        key: 'export',
        label: '参数提取与导出',
        settings: ['Extract weights', 'Decode material', 'Export fullbin', 'Output verification'],
      },
    ],
  },
}

function summarizePath(path: string) {
  return path.length > 68 ? `...${path.slice(-68)}` : path
}

function SettingRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="settings-row">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  )
}

function SettingsCanvas({
  system,
  systemError,
  systemLoading,
  galleryCount,
}: Pick<WorkspaceCanvasProps, 'system' | 'systemError' | 'systemLoading' | 'galleryCount'>) {
  const queryClient = useQueryClient()
  const compileDefaults = system?.compile_defaults
  const savedSettings = system?.settings
  const [projectRoot, setProjectRoot] = useState('')
  const [mitsubaExe, setMitsubaExe] = useState('')
  const [mtsutilExe, setMtsutilExe] = useState('')
  const [compileCmd, setCompileCmd] = useState('')
  const [compileCondaEnv, setCompileCondaEnv] = useState('')
  const [compileLabel, setCompileLabel] = useState('')
  const [vcvarsallPath, setVcvarsallPath] = useState('')
  const [compileWorkDir, setCompileWorkDir] = useState('')
  const [dependencies, setDependencies] = useState<SystemDependencySetting[]>([])
  const [virtualEnvs, setVirtualEnvs] = useState<SystemVirtualEnvSetting[]>([])
  const [activeTaskId, setActiveTaskId] = useState<string | null>(null)
  const [liveLogs, setLiveLogs] = useState<string[]>([])

  const compileTaskQuery = useSystemCompileTaskDetail(activeTaskId)
  const startCompileMutation = useStartSystemCompile()
  const stopCompileMutation = useStopSystemCompile()
  const saveSettingsMutation = useSaveSystemSettings()
  const checkSettingsMutation = useCheckSystemSettings()
  const taskDetail = compileTaskQuery.data
  const taskRecord = taskDetail?.record

  useEffect(() => {
    if (!savedSettings || projectRoot || dependencies.length > 0) {
      return
    }
    setProjectRoot(savedSettings.project_root)
    setMitsubaExe(savedSettings.mitsuba_exe)
    setMtsutilExe(savedSettings.mtsutil_exe)
    setCompileCmd(savedSettings.compile_cmd)
    setCompileCondaEnv(savedSettings.conda_env)
    setCompileLabel(savedSettings.preset_label)
    setVcvarsallPath(savedSettings.vcvarsall_path)
    setCompileWorkDir(savedSettings.work_dir)
    setDependencies(savedSettings.dependencies)
    setVirtualEnvs(savedSettings.virtual_envs)
  }, [dependencies.length, projectRoot, savedSettings, virtualEnvs.length])

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
      queryClient.invalidateQueries({ queryKey: ['system-compile-task', activeTaskId] })
    }

    return () => socket.close()
  }, [activeTaskId, queryClient])

  const compileError =
    startCompileMutation.error instanceof Error
      ? startCompileMutation.error
      : stopCompileMutation.error instanceof Error
        ? stopCompileMutation.error
        : saveSettingsMutation.error instanceof Error
          ? saveSettingsMutation.error
          : checkSettingsMutation.error instanceof Error
            ? checkSettingsMutation.error
            : null
  const logs = liveLogs.length > 0 ? liveLogs : taskDetail?.logs ?? []
  const compileStatus =
    taskRecord?.status ?? (startCompileMutation.isPending || stopCompileMutation.isPending ? 'pending' : 'idle')
  const compileProgress = taskRecord?.progress ?? 0
  const dependencyChecks = saveSettingsMutation.data?.checks ?? checkSettingsMutation.data?.checks ?? system?.checks ?? []
  const envChecks = saveSettingsMutation.data?.env_checks ?? checkSettingsMutation.data?.env_checks ?? system?.env_checks ?? []
  const dependencyOkCount = dependencyChecks.filter((check) => check.status === 'ok').length
  const dependencyTotalCount = dependencyChecks.length
  const envOkCount = envChecks.filter((check) => check.status === 'ok').length
  const envTotalCount = envChecks.length
  const settingsSavedState = savedSettings ? '已加载' : '未加载'
  const currentCompileProfile = compileLabel.trim() || compileDefaults?.preset_label || '-'

  const settingsPayload = {
    project_root: projectRoot.trim(),
    mitsuba_exe: mitsubaExe.trim(),
    mtsutil_exe: mtsutilExe.trim(),
    preset_label: compileLabel.trim(),
    conda_env: compileCondaEnv.trim(),
    compile_cmd: compileCmd.trim(),
    vcvarsall_path: vcvarsallPath.trim(),
    work_dir: compileWorkDir.trim(),
    dependencies: dependencies
      .map((dependency) => ({
        id: dependency.id,
        label: dependency.label.trim(),
        path: dependency.path.trim(),
      }))
      .filter((dependency) => dependency.label || dependency.path),
    virtual_envs: virtualEnvs
      .map((env) => ({
        id: env.id,
        label: env.label.trim(),
        manager: env.manager.trim() || 'conda',
        env_name: env.env_name.trim(),
        role: env.role.trim(),
      }))
      .filter((env) => env.label || env.env_name),
  }

  const resetFromSavedSettings = () => {
    if (!savedSettings) {
      return
    }
    setProjectRoot(savedSettings.project_root)
    setMitsubaExe(savedSettings.mitsuba_exe)
    setMtsutilExe(savedSettings.mtsutil_exe)
    setCompileCmd(savedSettings.compile_cmd)
    setCompileCondaEnv(savedSettings.conda_env)
    setCompileLabel(savedSettings.preset_label)
    setVcvarsallPath(savedSettings.vcvarsall_path)
    setCompileWorkDir(savedSettings.work_dir)
    setDependencies(savedSettings.dependencies)
    setVirtualEnvs(savedSettings.virtual_envs)
  }

  const updateDependency = (id: string, patch: Partial<SystemDependencySetting>) => {
    setDependencies((current) => current.map((dependency) => (dependency.id === id ? { ...dependency, ...patch } : dependency)))
  }

  const addDependency = () => {
    setDependencies((current) => [...current, { id: `dep-${Date.now()}-${current.length}`, label: '', path: '' }])
  }

  const removeDependency = (id: string) => {
    setDependencies((current) => current.filter((dependency) => dependency.id !== id))
  }

  const updateVirtualEnv = (id: string, patch: Partial<SystemVirtualEnvSetting>) => {
    setVirtualEnvs((current) => current.map((env) => (env.id === id ? { ...env, ...patch } : env)))
  }

  const addVirtualEnv = () => {
    setVirtualEnvs((current) => [...current, { id: `env-${Date.now()}-${current.length}`, label: '', manager: 'conda', env_name: '', role: '' }])
  }

  const removeVirtualEnv = (id: string) => {
    setVirtualEnvs((current) => current.filter((env) => env.id !== id))
  }

  const startCompile = async () => {
    if (!compileCmd.trim() || !compileCondaEnv.trim() || !compileWorkDir.trim()) {
      return
    }
    setLiveLogs([])
    const response = await startCompileMutation.mutateAsync({
      compile_cmd: compileCmd.trim(),
      conda_env: compileCondaEnv.trim(),
      compile_label: compileLabel.trim() || compileDefaults?.preset_label || '自定义编译',
      vcvarsall_path: vcvarsallPath.trim(),
      work_dir: compileWorkDir.trim(),
      dependency_paths: settingsPayload.dependencies.map((dependency) => dependency.path),
    })
    setActiveTaskId(response.task_id)
  }

  const stopCompile = async () => {
    if (!activeTaskId) {
      return
    }
    await stopCompileMutation.mutateAsync(activeTaskId)
    queryClient.invalidateQueries({ queryKey: ['system-compile-task', activeTaskId] })
  }

  const saveSettings = async () => {
    const response = await saveSettingsMutation.mutateAsync(settingsPayload)
    setProjectRoot(response.settings.project_root)
    setMitsubaExe(response.settings.mitsuba_exe)
    setMtsutilExe(response.settings.mtsutil_exe)
    setCompileCmd(response.settings.compile_cmd)
    setCompileCondaEnv(response.settings.conda_env)
    setCompileLabel(response.settings.preset_label)
    setVcvarsallPath(response.settings.vcvarsall_path)
    setCompileWorkDir(response.settings.work_dir)
    setDependencies(response.settings.dependencies)
    setVirtualEnvs(response.settings.virtual_envs)
    await queryClient.invalidateQueries({ queryKey: ['system-summary'] })
  }

  const checkSettings = async () => {
    await checkSettingsMutation.mutateAsync(settingsPayload)
  }

  return (
    <section className="workspace-canvas" style={{ overflowY: 'auto' }}>
      <div className="settings-grid">
        <Card variant="settings" className="settings-card--wide">
          <div className="detail-board__lead">
            <h3>系统状态</h3>
          </div>
          {systemLoading ? <p className="muted">正在读取后端摘要...</p> : null}
          {systemError ? <p className="error-text">{systemError}</p> : null}
          <div className="settings-list" style={{ marginTop: 0 }}>
            <SettingRow label="Backend" value={systemError ? 'Error' : systemLoading ? 'Syncing' : 'Online'} />
            <SettingRow label="Mitsuba" value={system?.mitsuba_exists ? 'Ready' : 'Pending'} />
            <SettingRow label="mtsutil" value={system?.mtsutil_exists ? 'Ready' : 'Pending'} />
            <SettingRow label="输出索引" value={String(galleryCount)} />
            <SettingRow label="依赖检查" value={dependencyTotalCount > 0 ? `${dependencyOkCount} / ${dependencyTotalCount}` : '未检查'} />
            <SettingRow label="环境检查" value={envTotalCount > 0 ? `${envOkCount} / ${envTotalCount}` : '未检查'} />
            <SettingRow label="设置状态" value={settingsSavedState} />
            <SettingRow label="当前编译预设" value={currentCompileProfile} />
          </div>
        </Card>

        <Card variant="settings" className="settings-card--wide">
          <div className="detail-board__lead">
            <h3>核心路径</h3>
          </div>
          <div className="render-form-grid" style={{ marginTop: 12 }}>
            <Field label="项目路径">
              <input value={projectRoot} onChange={(event) => setProjectRoot(event.target.value)} placeholder="." />
            </Field>
            <Field label="Mitsuba EXE">
              <input value={mitsubaExe} onChange={(event) => setMitsubaExe(event.target.value)} placeholder="mitsuba\\dist\\mitsuba.exe" />
            </Field>
            <Field label="mtsutil EXE">
              <input value={mtsutilExe} onChange={(event) => setMtsutilExe(event.target.value)} placeholder="mitsuba\\dist\\mtsutil.exe" />
            </Field>
          </div>
        </Card>

        <Card variant="settings" className="settings-card--wide">
          <div className="detail-board__lead">
            <h3>Mitsuba 编译辅助</h3>
          </div>
          <p className="muted">该入口已从 V1 迁移到 V2。用于调用 Visual Studio 工具链、激活 `mitsuba-build` 环境并执行 SCons 编译。</p>
          <div className="render-form-grid" style={{ marginTop: 12 }}>
            <Field label="预设名称">
              <input value={compileLabel} onChange={(event) => setCompileLabel(event.target.value)} placeholder="Default SCons Parallel Build" />
            </Field>
            <Field label="Conda 环境">
              <input value={compileCondaEnv} onChange={(event) => setCompileCondaEnv(event.target.value)} placeholder="mitsuba-build" />
            </Field>
            <Field label="编译命令">
              <input value={compileCmd} onChange={(event) => setCompileCmd(event.target.value)} placeholder="scons --parallelize" />
            </Field>
            <Field label="vcvarsall">
              <input value={vcvarsallPath} onChange={(event) => setVcvarsallPath(event.target.value)} placeholder="可填 vcvarsall.bat 或 .lnk；留空时自动探测" />
            </Field>
            <Field label="编译工作目录">
              <input value={compileWorkDir} onChange={(event) => setCompileWorkDir(event.target.value)} placeholder="mitsuba" />
            </Field>
          </div>

          <div className="detail-board__lead" style={{ marginTop: 18 }}>
            <h3>依赖路径</h3>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginTop: 12 }}>
            {dependencies.map((dependency) => (
              <div key={dependency.id} style={{ display: 'grid', gridTemplateColumns: '180px minmax(0, 1fr) 96px', gap: '10px', alignItems: 'end' }}>
                <Field label="名称">
                  <input value={dependency.label} onChange={(event) => updateDependency(dependency.id, { label: event.target.value })} placeholder="依赖名称" />
                </Field>
                <Field label="路径">
                  <input value={dependency.path} onChange={(event) => updateDependency(dependency.id, { path: event.target.value })} placeholder="mitsuba\\dependencies\\bin" />
                </Field>
                <Button type="button" onClick={() => removeDependency(dependency.id)}>
                  删除
                </Button>
              </div>
            ))}
            <div className="render-actions" style={{ marginTop: 0 }}>
              <Button type="button" onClick={() => addDependency()}>
                添加依赖
              </Button>
            </div>
          </div>

          <div className="detail-board__lead" style={{ marginTop: 18 }}>
            <h3>虚拟环境管理</h3>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginTop: 12 }}>
            {virtualEnvs.map((env) => (
              <div key={env.id} style={{ display: 'grid', gridTemplateColumns: '170px 120px 170px minmax(0, 1fr) 96px', gap: '10px', alignItems: 'end' }}>
                <Field label="名称">
                  <input value={env.label} onChange={(event) => updateVirtualEnv(env.id, { label: event.target.value })} placeholder="环境名称" />
                </Field>
                <Field label="管理器">
                  <input value={env.manager} onChange={(event) => updateVirtualEnv(env.id, { manager: event.target.value })} placeholder="conda" />
                </Field>
                <Field label="环境名">
                  <input value={env.env_name} onChange={(event) => updateVirtualEnv(env.id, { env_name: event.target.value })} placeholder="matreflect" />
                </Field>
                <Field label="用途">
                  <input value={env.role} onChange={(event) => updateVirtualEnv(env.id, { role: event.target.value })} placeholder="项目后端 / 某模型训练" />
                </Field>
                <Button type="button" onClick={() => removeVirtualEnv(env.id)}>
                  删除
                </Button>
              </div>
            ))}
            <div className="render-actions" style={{ marginTop: 0 }}>
              <Button type="button" onClick={() => addVirtualEnv()}>
                添加环境
              </Button>
            </div>
          </div>

          <div className="settings-list" style={{ marginTop: 16 }}>
            <SettingRow label="当前任务" value={activeTaskId ?? '暂无'} />
            <SettingRow label="已保存依赖数" value={String(savedSettings?.dependencies.length ?? dependencies.length)} />
          </div>

          <div className="render-actions" style={{ marginTop: 12, marginBottom: 0 }}>
            <Button type="button" disabled={checkSettingsMutation.isPending} onClick={() => void checkSettings()}>
              检查依赖
            </Button>
            <Button type="button" disabled={saveSettingsMutation.isPending} onClick={() => void saveSettings()}>
              保存设置
            </Button>
            <Button type="button" disabled={!savedSettings} onClick={() => resetFromSavedSettings()}>
              恢复已保存
            </Button>
            <Button
              type="button"
              variant="primary"
              disabled={startCompileMutation.isPending || !compileCmd.trim() || !compileCondaEnv.trim() || !compileWorkDir.trim()}
              onClick={() => void startCompile()}
            >
              启动编译
            </Button>
            <Button
              type="button"
              variant="danger"
              disabled={!activeTaskId || !['pending', 'running'].includes(compileStatus)}
              onClick={() => void stopCompile()}
            >
              停止编译
            </Button>
          </div>
          {compileError ? <FeedbackPanel title="系统设置或编译操作失败" message={compileError.message} tone="error" compact /> : null}
          {dependencyChecks.length > 0 ? (
            <div className="settings-list" style={{ marginTop: 16 }}>
              {dependencyChecks.map((check) => (
                <SettingRow key={check.id} label={`${check.label} [${check.status}]`} value={check.path ? `${summarizePath(check.path)} | ${check.message}` : check.message} />
              ))}
            </div>
          ) : null}
          {envChecks.length > 0 ? (
            <div className="settings-list" style={{ marginTop: 16 }}>
              {envChecks.map((check) => (
                <SettingRow
                  key={check.id}
                  label={`${check.label} [${check.status}]`}
                  value={check.prefix ? `${check.env_name} | ${summarizePath(check.prefix)} | ${check.message}` : `${check.env_name} | ${check.message}`}
                />
              ))}
            </div>
          ) : null}
          <TerminalDrawer
            taskId={activeTaskId}
            status={compileStatus}
            progress={compileProgress}
            logs={logs}
            error={compileError}
            onStop={!['pending', 'running'].includes(compileStatus) ? undefined : () => void stopCompile()}
            taskStateMessage={taskRecord?.message ?? null}
          />
        </Card>
      </div>
    </section>
  )
}

export function WorkspaceCanvas({
  activeModule,
  activeAnalysisSubView,
  onAnalysisSubViewChange,
  activeModelsSubView,
  onModelsSubViewChange,
  galleryItems,
  galleryCount,
  system,
  systemError,
  systemLoading,
}: WorkspaceCanvasProps) {
  if (activeModule === 'render') {
    return <RenderWorkbench />
  }

  if (activeModule === 'analysis') {
    return <AnalysisWorkbench activeSubView={activeAnalysisSubView} onSubViewChange={onAnalysisSubViewChange} />
  }

  if (activeModule === 'models') {
    return <ModelsWorkbench activeSubView={activeModelsSubView} onSubViewChange={onModelsSubViewChange} />
  }

  if (activeModule === 'settings') {
    return <SettingsCanvas system={system} systemError={systemError} systemLoading={systemLoading} galleryCount={galleryCount} />
  }

  return <ModulePlaceholder activeModule={activeModule} galleryItems={galleryItems} />
}

function ModulePlaceholder({
  activeModule,
  galleryItems,
}: {
  activeModule: Exclude<ModuleKey, 'render' | 'analysis' | 'settings'>
  galleryItems: FileListItem[]
}) {
  const meta = moduleMeta[activeModule]
  const [selectedAction, setSelectedAction] = useState<string>(meta.actions[0].key)

  useEffect(() => {
    setSelectedAction(moduleMeta[activeModule].actions[0].key)
  }, [activeModule])

  const activeAction = useMemo(
    () => meta.actions.find((action) => action.key === selectedAction) ?? meta.actions[0],
    [meta.actions, selectedAction],
  )
  const previewItems = galleryItems.slice(0, 3)

  return (
    <section className="workspace-canvas">
      <div className="workspace-hero">
        <div>
          <h2>{meta.title}</h2>
        </div>
      </div>

      <div className="action-grid">
        {meta.actions.map((action) => (
          <button
            key={action.key}
            type="button"
            className={action.key === activeAction.key ? 'action-tile action-tile--active' : 'action-tile'}
            onClick={() => setSelectedAction(action.key)}
          >
            <span className="action-tile__label">{action.label}</span>
          </button>
        ))}
      </div>

      <div className="detail-board">
        <div className="detail-board__lead">
          <h3>{activeAction.label}</h3>
        </div>
        <div className="detail-pill-grid">
          {activeAction.settings.map((setting) => (
            <Badge key={setting} variant="detail">
              {setting}
            </Badge>
          ))}
        </div>
      </div>

      <div className="mini-output-list">
        {previewItems.length > 0 ? (
          previewItems.map((item) => {
            const parsedName = parseAssetName(item.name)
            return (
              <article key={item.path} className="mini-output">
                <div className="gallery-item__thumb" />
                <div>
                  <strong>{parsedName.materialName}</strong>
                  {parsedName.timestampDisplay ? <div className="muted">{parsedName.timestampDisplay}</div> : null}
                </div>
              </article>
            )
          })
        ) : (
          <article className="mini-output mini-output--empty">
            <div className="gallery-item__thumb" />
            <div>
              <strong>暂无输出</strong>
            </div>
          </article>
        )}
      </div>
    </section>
  )
}
