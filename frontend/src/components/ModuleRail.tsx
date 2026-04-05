import type { ModuleKey } from '../types/api'

type ModuleRailProps = {
  activeModule: ModuleKey
  onChange: (module: ModuleKey) => void
}

const modules: Array<{ key: ModuleKey; label: string; detail: string; phase: string }> = [
  { key: 'render', label: '渲染可视化', detail: '场景、材质、输出画廊与任务日志', phase: 'Phase 2 First' },
  { key: 'analysis', label: '材质结果分析', detail: '量化对比、滑块预览、拼图与报告', phase: 'Phase 3 Next' },
  { key: 'models', label: '网络模型管理', detail: '训练入口、运行记录、checkpoint 与导出', phase: 'Phase 4 Queue' },
]

export function ModuleRail({ activeModule, onChange }: ModuleRailProps) {
  return (
    <aside className="module-rail">
      <div className="module-rail__header">
        <span className="eyebrow">MatReflect_NN V2</span>
        <h2>Research Console</h2>
        <p>不再沿用默认侧栏页面模型，而是改成可扩展的实验工作台。每个入口都会展开成更细的设置面板。</p>
      </div>

      <div className="module-rail__summary">
        <span>Current Track</span>
        <strong>Phase 1 / Shell + API Stabilization</strong>
      </div>

      <div className="module-rail__list">
        {modules.map((module) => (
          <button
            key={module.key}
            type="button"
            className={module.key === activeModule ? 'module-card module-card--active' : 'module-card'}
            onClick={() => onChange(module.key)}
          >
            <span className="module-card__phase">{module.phase}</span>
            <span className="module-card__label">{module.label}</span>
            <span className="module-card__detail">{module.detail}</span>
          </button>
        ))}
      </div>

      <div className="module-rail__footer">
        <strong>Migration Rule</strong>
        <p>V1 逻辑暂时保留，V2 先把渲染闭环做通，再迁移分析与模型管理。</p>
      </div>
    </aside>
  )
}
