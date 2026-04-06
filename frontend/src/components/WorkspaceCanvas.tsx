import { useEffect, useMemo, useState } from 'react'

import type { FileListItem, ModuleKey, SystemSummary } from '../types/api'
import { AnalysisWorkbench } from './AnalysisWorkbench'
import { ModelsWorkbench } from './ModelsWorkbench'
import { RenderWorkbench } from './RenderWorkbench'

type WorkspaceCanvasProps = {
  activeModule: ModuleKey
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
        label: '图像滑块检视',
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
  const pathKeys = system?.available_path_keys ?? []

  return (
    <section className="workspace-canvas">
      <div className="workspace-hero">
        <div>
          <h2>设置与系统状态</h2>
        </div>
      </div>

      <div className="settings-grid">
        <section className="settings-card">
          <div className="detail-board__lead">
            <h3>系统状态</h3>
          </div>
          {systemLoading ? <p className="muted">正在读取后端摘要...</p> : null}
          {systemError ? <p className="error-text">{systemError}</p> : null}
          <div className="settings-list">
            <SettingRow label="Backend" value={systemError ? 'Error' : systemLoading ? 'Syncing' : 'Online'} />
            <SettingRow label="Mitsuba" value={system?.mitsuba_exists ? 'Ready' : 'Pending'} />
            <SettingRow label="输出索引" value={String(galleryCount)} />
            <SettingRow label="模块数" value={String(system?.available_modules.length ?? 4)} />
          </div>
        </section>

        <section className="settings-card settings-card--wide">
          <div className="detail-board__lead">
            <h3>项目路径</h3>
          </div>
          <div className="mono-value">{system ? summarizePath(system.project_root) : '等待后端摘要返回'}</div>
          <div className="settings-list">
            <SettingRow label="Mitsuba EXE" value={system ? summarizePath(system.mitsuba_exe) : '-'} />
            <SettingRow label="mtsutil EXE" value={system ? summarizePath(system.mtsutil_exe) : '-'} />
          </div>
        </section>

        <section className="settings-card settings-card--wide">
          <div className="detail-board__lead">
            <h3>路径索引与能力</h3>
          </div>
          <div className="tag-cloud">
            {pathKeys.length > 0 ? (
              pathKeys.map((pathKey) => (
                <span key={pathKey} className="tag-chip">
                  {pathKey}
                </span>
              ))
            ) : (
              <span className="detail-pill">等待路径索引</span>
            )}
          </div>
          <div className="tag-cloud">
            {(system?.available_modules ?? ['render', 'analysis', 'models', 'settings']).map((module) => (
              <span key={module} className="detail-pill">
                {module}
              </span>
            ))}
          </div>
        </section>
      </div>
    </section>
  )
}

export function WorkspaceCanvas({
  activeModule,
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
    return <AnalysisWorkbench />
  }

  if (activeModule === 'models') {
    return <ModelsWorkbench />
  }

  if (activeModule === 'settings') {
    return (
      <SettingsCanvas
        system={system}
        systemError={systemError}
        systemLoading={systemLoading}
        galleryCount={galleryCount}
      />
    )
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
            <span key={setting} className="detail-pill">
              {setting}
            </span>
          ))}
        </div>
      </div>

      <div className="mini-output-list">
        {previewItems.length > 0 ? (
          previewItems.map((item) => (
            <article key={item.path} className="mini-output">
              <div className="gallery-item__thumb" />
              <div>
                <strong>{item.name}</strong>
              </div>
            </article>
          ))
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
