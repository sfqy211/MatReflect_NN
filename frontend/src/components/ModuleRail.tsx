import { useEffect } from 'react'
import type { ModuleKey } from '../types/api'
import type { AnalysisSubView, ModelsSubView } from '../App'
import { useTrainModels } from '../features/models/useModelsWorkbench'

type ModuleRailProps = {
  activeModule: ModuleKey
  onChange: (module: ModuleKey) => void
  activeAnalysisSubView: AnalysisSubView
  onAnalysisSubViewChange: (view: AnalysisSubView) => void
  activeModelsSubView: ModelsSubView
  onModelsSubViewChange: (view: ModelsSubView) => void
  pinned: boolean
  onTogglePin: () => void
}

const moduleIcons: Record<ModuleKey, string> = {
  models: 'M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5',
  render: 'M23 19a2 2 0 01-2 2H3a2 2 0 01-2-2V8a2 2 0 012-2h4l2-3h6l2 3h4a2 2 0 012 2zM12 17a4 4 0 100-8 4 4 0 000 8z',
  analysis: 'M18 20V10M12 20V4M6 20v-6',
  settings: 'M12 15a3 3 0 100-6 3 3 0 000 6zM19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 112.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06a1.65 1.65 0 00-.33 1.82V9c.26.604.852.997 1.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z',
}

const modules: Array<{ key: ModuleKey; label: string }> = [
  { key: 'models', label: '网络模型管理' },
  { key: 'render', label: '渲染可视化' },
  { key: 'analysis', label: '材质结果分析' },
  { key: 'settings', label: '设置' },
]

const analysisSubViews: Array<{ key: AnalysisSubView; label: string }> = [
  { key: 'evaluate', label: '量化评估' },
  { key: 'compare', label: '图像对比滑块' },
  { key: 'grid', label: '网格拼图' },
  { key: 'compare-grid', label: '对比拼图' },
]

export function ModuleRail({ activeModule, onChange, activeAnalysisSubView, onAnalysisSubViewChange, activeModelsSubView, onModelsSubViewChange, pinned, onTogglePin }: ModuleRailProps) {
  const modelQuery = useTrainModels()
  const models = modelQuery.data?.items ?? []

  useEffect(() => {
    if (activeModule === 'models' && !activeModelsSubView && models.length > 0) {
      onModelsSubViewChange(models[0].key)
    }
  }, [activeModule, activeModelsSubView, models, onModelsSubViewChange])

  return (
    <aside className={`module-rail${pinned ? ' module-rail--pinned' : ''}`}>
      <div className="module-rail__header">
        <h2 className="module-rail__title">功能导航</h2>
        <button
          type="button"
          className="rail-pin"
          onClick={onTogglePin}
          title={pinned ? '取消固定' : '固定导航'}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill={pinned ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 17v5M9 11V4a1 1 0 011-1h4a1 1 0 011 1v7M7 11h10l-1 6H8l-1-6z" />
          </svg>
        </button>
      </div>

      <div className="module-rail__list">
        {modules.map((module) => (
          <div key={module.key}>
            <button
              type="button"
              className={`module-card${module.key === activeModule ? ' module-card--active' : ''}`}
              onClick={() => onChange(module.key)}
              title={module.label}
            >
              <svg className="module-card__icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d={moduleIcons[module.key]} />
              </svg>
              <span className="module-card__label">{module.label}</span>
            </button>
            {module.key === 'analysis' && activeModule === 'analysis' && (
              <div className="module-sub-menu">
                {analysisSubViews.map((subView) => (
                  <button
                    key={subView.key}
                    type="button"
                    className={`module-sub-item${subView.key === activeAnalysisSubView ? ' module-sub-item--active' : ''}`}
                    onClick={() => onAnalysisSubViewChange(subView.key)}
                  >
                    {subView.label}
                  </button>
                ))}
              </div>
            )}
            {module.key === 'models' && activeModule === 'models' && (
              <div className="module-sub-menu">
                {models.map((m) => (
                  <button
                    key={m.key}
                    type="button"
                    className={`module-sub-item${m.key === activeModelsSubView ? ' module-sub-item--active' : ''}`}
                    onClick={() => onModelsSubViewChange(m.key)}
                    title={m.label}
                  >
                    {m.label}
                  </button>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </aside>
  )
}
