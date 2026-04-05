import type { ModuleKey } from '../types/api'

type ModuleRailProps = {
  activeModule: ModuleKey
  onChange: (module: ModuleKey) => void
  collapsed: boolean
  onToggleCollapse: () => void
}

const modules: Array<{ key: ModuleKey; label: string; shortLabel: string }> = [
  { key: 'render', label: '渲染可视化', shortLabel: '渲染' },
  { key: 'analysis', label: '材质结果分析', shortLabel: '分析' },
  { key: 'models', label: '网络模型管理', shortLabel: '模型' },
  { key: 'settings', label: '设置', shortLabel: '设置' },
]

export function ModuleRail({ activeModule, onChange, collapsed, onToggleCollapse }: ModuleRailProps) {
  return (
    <aside className={collapsed ? 'module-rail module-rail--collapsed' : 'module-rail'}>
      <div className="module-rail__header">
        {!collapsed ? <h2>功能导航</h2> : null}
        <button type="button" className="rail-toggle" onClick={onToggleCollapse}>
          {collapsed ? '展开' : '收起'}
        </button>
      </div>

      <div className="module-rail__list">
        {modules.map((module) => (
          <button
            key={module.key}
            type="button"
            className={module.key === activeModule ? 'module-card module-card--active' : 'module-card'}
            onClick={() => onChange(module.key)}
            title={module.label}
          >
            <span className="module-card__label">{collapsed ? module.shortLabel : module.label}</span>
          </button>
        ))}
      </div>
    </aside>
  )
}
