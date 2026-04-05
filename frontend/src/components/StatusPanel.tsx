import type { ModuleKey, SystemSummary } from '../types/api'

type StatusPanelProps = {
  activeModule: ModuleKey
  galleryCount: number
  system?: SystemSummary
  isLoading: boolean
  error?: string
}

const moduleTitles: Record<ModuleKey, string> = {
  render: '渲染模块优先落地',
  analysis: '分析模块等待 API 抽离',
  models: '模型管理将在训练服务稳定后接入',
}

function summarizePath(path: string) {
  return path.length > 44 ? `...${path.slice(-44)}` : path
}

export function StatusPanel({ activeModule, galleryCount, system, isLoading, error }: StatusPanelProps) {
  const pathKeys = system?.available_path_keys.slice(0, 6) ?? []

  return (
    <aside className="status-panel">
      <div className="panel-head">
        <span className="eyebrow">Context Rail</span>
        <h2>运行摘要</h2>
        <p>右侧保留系统状态、迁移节奏和任务上下文，避免再次回到 Streamlit 那种被默认布局限制的页面结构。</p>
      </div>
      {isLoading ? <p className="muted">正在读取后端摘要...</p> : null}
      {error ? <p className="error-text">{error}</p> : null}

      <div className="status-metric-grid">
        <article className="status-metric">
          <span className="status-metric__label">当前聚焦</span>
          <strong>{activeModule === 'render' ? 'Render' : activeModule === 'analysis' ? 'Analysis' : 'Models'}</strong>
        </article>
        <article className="status-metric">
          <span className="status-metric__label">Mitsuba</span>
          <strong>{system?.mitsuba_exists ? 'Ready' : 'Pending'}</strong>
        </article>
        <article className="status-metric">
          <span className="status-metric__label">输出索引</span>
          <strong>{galleryCount}</strong>
        </article>
        <article className="status-metric">
          <span className="status-metric__label">模块数</span>
          <strong>{system?.available_modules.length ?? 3}</strong>
        </article>
      </div>

      <section className="status-section">
        <h3>当前模块</h3>
        <p>{moduleTitles[activeModule]}</p>
      </section>

      {system ? (
        <>
          <section className="status-section">
            <h3>项目路径</h3>
            <div className="mono-value">{summarizePath(system.project_root)}</div>
          </section>

          <section className="status-section">
            <h3>路径索引</h3>
            <div className="tag-cloud">
              {pathKeys.map((pathKey) => (
                <span key={pathKey} className="tag-chip">
                  {pathKey}
                </span>
              ))}
            </div>
          </section>

          <section className="status-section">
            <h3>执行节奏</h3>
            <div className="timeline-list">
              <article className="timeline-item timeline-item--done">
                <strong>01</strong>
                <span>API skeleton ready</span>
              </article>
              <article className="timeline-item timeline-item--active">
                <strong>02</strong>
                <span>Workbench shell rebuild</span>
              </article>
              <article className="timeline-item">
                <strong>03</strong>
                <span>Render service extraction</span>
              </article>
              <article className="timeline-item">
                <strong>04</strong>
                <span>Analysis / Models migration</span>
              </article>
            </div>
          </section>
        </>
      ) : null}

      {system ? (
        <section className="status-section">
          <h3>后端能力</h3>
          <div className="tag-cloud">
            {system.available_modules.map((module) => (
              <span key={module} className="tag-chip">
                {module}
              </span>
            ))}
          </div>
        </section>
      ) : (
        <section className="status-section">
          <h3>后端能力</h3>
          <p>等待后端摘要返回后，这里会显示模块和安全路径索引。</p>
        </section>
      )}
    </aside>
  )
}
