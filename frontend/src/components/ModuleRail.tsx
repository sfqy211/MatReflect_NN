import type { ModuleKey } from '../types/api'

type ModuleRailProps = {
  activeModule: ModuleKey
  onChange: (module: ModuleKey) => void
}

const modules: Array<{ key: ModuleKey; label: string }> = [
  { key: 'render', label: '渲染可视化' },
  { key: 'analysis', label: '材质结果分析' },
  { key: 'models', label: '网络模型管理' },
  { key: 'settings', label: '设置' },
]

export function ModuleRail({ activeModule, onChange }: ModuleRailProps) {
  return (
    <aside className="module-rail">
      <div className="module-rail__header">
        <h2>Research Console</h2>
      </div>

      <div className="module-rail__list">
        {modules.map((module) => (
          <button
            key={module.key}
            type="button"
            className={module.key === activeModule ? 'module-card module-card--active' : 'module-card'}
            onClick={() => onChange(module.key)}
          >
            <span className="module-card__label">{module.label}</span>
          </button>
        ))}
      </div>
    </aside>
  )
}
