import { useEffect } from 'react'
import type { ModuleKey } from '../types/api'
import type { AnalysisSubView, ModelsSubView } from '../App'
import { useTrainModels } from '../features/models/useModelsWorkbench'
import { Button } from './ui/Button'

type ThemeMode = 'dark' | 'light'

type ModuleRailProps = {
  activeModule: ModuleKey
  onChange: (module: ModuleKey) => void
  activeAnalysisSubView: AnalysisSubView
  onAnalysisSubViewChange: (view: AnalysisSubView) => void
  activeModelsSubView: ModelsSubView
  onModelsSubViewChange: (view: ModelsSubView) => void
  collapsed: boolean
  onToggleCollapse: () => void
  theme: ThemeMode
  onThemeChange: (theme: ThemeMode) => void
}

const modules: Array<{ key: ModuleKey; label: string; shortLabel: string }> = [
  { key: 'render', label: '渲染可视化', shortLabel: '渲染' },
  { key: 'analysis', label: '材质结果分析', shortLabel: '分析' },
  { key: 'models', label: '网络模型管理', shortLabel: '模型' },
  { key: 'settings', label: '设置', shortLabel: '设置' },
]

const analysisSubViews: Array<{ key: AnalysisSubView; label: string }> = [
  { key: 'preview', label: '图片预览' },
  { key: 'evaluate', label: '量化评估' },
  { key: 'compare', label: '图像对比滑块' },
  { key: 'grid', label: '网格拼图' },
  { key: 'compare-grid', label: '对比拼图' },
]

export function ModuleRail({ activeModule, onChange, activeAnalysisSubView, onAnalysisSubViewChange, activeModelsSubView, onModelsSubViewChange, collapsed, onToggleCollapse, theme, onThemeChange }: ModuleRailProps) {
  const modelQuery = useTrainModels()
  const models = modelQuery.data?.items ?? []

  useEffect(() => {
    if (activeModule === 'models' && !activeModelsSubView && models.length > 0) {
      onModelsSubViewChange(models[0].key)
    }
  }, [activeModule, activeModelsSubView, models, onModelsSubViewChange])

  return (
    <aside className={collapsed ? 'module-rail module-rail--collapsed' : 'module-rail'}>
      <div className="module-rail__header" style={{ minHeight: '40px' }}>
        {!collapsed ? <h2>功能导航</h2> : null}
        <button 
          type="button" 
          className="rail-toggle" 
          onClick={onToggleCollapse} 
          style={{ 
            marginLeft: collapsed ? 0 : 'auto', 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'center',
            padding: '8px'
          }}
          title={collapsed ? '展开导航' : '收起导航'}
        >
          <svg 
            width="20" 
            height="20" 
            viewBox="0 0 24 24" 
            fill="none" 
            stroke="currentColor" 
            strokeWidth="2" 
            strokeLinecap="round" 
            strokeLinejoin="round"
            style={{
              transform: collapsed ? 'rotate(180deg)' : 'none',
              transition: 'transform 0.3s ease'
            }}
          >
            <path d="M15 18l-6-6 6-6" />
          </svg>
        </button>
      </div>

      <div className="module-rail__list">
        {modules.map((module) => (
          <div key={module.key}>
            <button
              type="button"
              className={module.key === activeModule ? 'module-card module-card--active' : 'module-card'}
              onClick={() => onChange(module.key)}
              title={module.label}
            >
              <span className="module-card__label">{collapsed ? module.shortLabel : module.label}</span>
            </button>
            {module.key === 'analysis' && activeModule === 'analysis' && !collapsed && (
              <div className="module-sub-menu" style={{ paddingLeft: '16px', marginTop: '8px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                {analysisSubViews.map((subView) => (
                  <button
                    key={subView.key}
                    type="button"
                    onClick={() => onAnalysisSubViewChange(subView.key)}
                    style={{
                      textAlign: 'left',
                      padding: '8px 12px',
                      background: subView.key === activeAnalysisSubView ? 'color-mix(in oklab, var(--surface-strong) 100%, transparent)' : 'transparent',
                      color: subView.key === activeAnalysisSubView ? 'var(--accent)' : 'var(--text-muted)',
                      border: '1px solid transparent',
                      borderColor: subView.key === activeAnalysisSubView ? 'var(--border)' : 'transparent',
                      borderRadius: '4px',
                      fontSize: '0.9rem',
                      transition: 'all 0.2s ease',
                      cursor: 'pointer',
                    }}
                    onMouseEnter={(e) => {
                      if (subView.key !== activeAnalysisSubView) {
                        e.currentTarget.style.color = 'var(--text-strong)'
                        e.currentTarget.style.background = 'color-mix(in oklab, var(--surface-soft) 40%, transparent)'
                      }
                    }}
                    onMouseLeave={(e) => {
                      if (subView.key !== activeAnalysisSubView) {
                        e.currentTarget.style.color = 'var(--text-muted)'
                        e.currentTarget.style.background = 'transparent'
                      }
                    }}
                  >
                    {subView.label}
                  </button>
                ))}
              </div>
            )}
            {module.key === 'models' && activeModule === 'models' && !collapsed && (
              <div className="module-sub-menu" style={{ paddingLeft: '16px', marginTop: '8px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                {models.map((m) => (
                  <button
                    key={m.key}
                    type="button"
                    onClick={() => onModelsSubViewChange(m.key)}
                    style={{
                      textAlign: 'left',
                      padding: '8px 12px',
                      background: m.key === activeModelsSubView ? 'color-mix(in oklab, var(--surface-strong) 100%, transparent)' : 'transparent',
                      color: m.key === activeModelsSubView ? 'var(--accent)' : 'var(--text-muted)',
                      border: '1px solid transparent',
                      borderColor: m.key === activeModelsSubView ? 'var(--border)' : 'transparent',
                      borderRadius: '4px',
                      fontSize: '0.9rem',
                      transition: 'all 0.2s ease',
                      cursor: 'pointer',
                      whiteSpace: 'nowrap',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                    }}
                    title={m.label}
                    onMouseEnter={(e) => {
                      if (m.key !== activeModelsSubView) {
                        e.currentTarget.style.color = 'var(--text-strong)'
                        e.currentTarget.style.background = 'color-mix(in oklab, var(--surface-soft) 40%, transparent)'
                      }
                    }}
                    onMouseLeave={(e) => {
                      if (m.key !== activeModelsSubView) {
                        e.currentTarget.style.color = 'var(--text-muted)'
                        e.currentTarget.style.background = 'transparent'
                      }
                    }}
                  >
                    {m.label}
                  </button>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>

      <div style={{ marginTop: 'auto', paddingTop: '20px' }}>
        <Button
          type="button"
          onClick={() => onThemeChange(theme === 'dark' ? 'light' : 'dark')}
          style={{ width: '100%', display: 'flex', justifyContent: 'center', alignItems: 'center' }}
          title={theme === 'dark' ? '切换到浅色模式' : '切换到深色模式'}
        >
          {collapsed ? (theme === 'dark' ? '🌙' : '🌞') : (theme === 'dark' ? '🌙 深色模式' : '🌞 浅色模式')}
        </Button>
      </div>
    </aside>
  )
}
