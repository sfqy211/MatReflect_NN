import type { ModuleKey, SystemSummary } from '../types/api'
import { Card } from './ui/Card'

type StatusPanelProps = {
  activeModule: ModuleKey
  galleryCount: number
  system?: SystemSummary
  isLoading: boolean
  error?: string
}

const moduleTitles: Record<ModuleKey, string> = {
  render: '渲染参数、输出和任务流',
  analysis: '对比、指标和结果检视',
  models: '训练、运行记录与导出',
  settings: '主题与系统配置',
}

export function StatusPanel({ activeModule, galleryCount, system, isLoading, error }: StatusPanelProps) {
  return (
    <aside className="status-panel">
      <div className="panel-head">
        <span className="eyebrow">Context Rail</span>
        <h2>运行摘要</h2>
      </div>

      {isLoading ? <p className="muted">正在读取后端摘要...</p> : null}
      {error ? <p className="error-text">{error}</p> : null}

      <div className="status-metric-grid">
        <Card variant="status">
          <span className="status-metric__label">当前聚焦</span>
          <strong>{activeModule === 'render' ? 'Render' : activeModule === 'analysis' ? 'Analysis' : 'Models'}</strong>
        </Card>
        <Card variant="status">
          <span className="status-metric__label">Mitsuba</span>
          <strong>{system?.mitsuba_exists ? 'Ready' : 'Pending'}</strong>
        </Card>
        <Card variant="status">
          <span className="status-metric__label">输出索引</span>
          <strong>{galleryCount}</strong>
        </Card>
        <Card variant="status">
          <span className="status-metric__label">模块数</span>
          <strong>{system?.available_modules.length ?? 3}</strong>
        </Card>
      </div>

      <section className="status-section">
        <h3>当前区域</h3>
        <p>{moduleTitles[activeModule]}</p>
      </section>

      <section className="status-section">
        <h3>说明</h3>
        <p>
          {activeModule === 'settings'
            ? '设置页集中管理主题和系统信息，避免这些内容继续占用主工作区之外的固定位置。'
            : '系统路径、后端能力和主题切换已移入设置页，右侧只保留轻量运行摘要。'}
        </p>
      </section>
    </aside>
  )
}
