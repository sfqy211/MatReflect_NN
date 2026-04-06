import type { ModuleKey } from '../types/api'

type ThemeMode = 'dark' | 'light'

type ModuleRailProps = {
  activeModule: ModuleKey
  onChange: (module: ModuleKey) => void
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

export function ModuleRail({ activeModule, onChange, collapsed, onToggleCollapse, theme, onThemeChange }: ModuleRailProps) {
  return (
    <aside className={collapsed ? 'module-rail module-rail--collapsed' : 'module-rail'}>
      <div className="module-rail__header" style={{ minHeight: '40px' }}>
        {!collapsed ? <h2>功能导航</h2> : null}
        <button type="button" className="rail-toggle" onClick={onToggleCollapse} style={{ marginLeft: collapsed ? 0 : 'auto' }}>
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

      <div style={{ marginTop: 'auto', paddingTop: '20px' }}>
        <button
          type="button"
          className="theme-toggle"
          onClick={() => onThemeChange(theme === 'dark' ? 'light' : 'dark')}
          style={{ width: '100%', display: 'flex', justifyContent: 'center', alignItems: 'center' }}
          title={theme === 'dark' ? '切换到浅色模式' : '切换到深色模式'}
        >
          {collapsed ? (theme === 'dark' ? '🌙' : '🌞') : (theme === 'dark' ? '🌙 深色模式' : '🌞 浅色模式')}
        </button>
      </div>
    </aside>
  )
}
