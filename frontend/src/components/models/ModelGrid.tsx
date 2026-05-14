import type { TrainModelItem } from '../../types/api'
import { Button } from '../ui/Button'

type ModelGridProps = {
  models: TrainModelItem[]
  onSelectModel: (key: string) => void
  onDeleteModel: (key: string) => void
  onImport: () => void
}

const capabilityLabels: Record<string, string> = {
  supports_training: '训练',
  supports_reconstruction: '重建',
  supports_extract: '参数提取',
  supports_decode: '解码',
}

function getModelCapabilities(model: TrainModelItem): string[] {
  return Object.entries(capabilityLabels)
    .filter(([key]) => model[key as keyof TrainModelItem] === true)
    .map(([, label]) => label)
}

export function ModelGrid({ models, onSelectModel, onDeleteModel, onImport }: ModelGridProps) {
  const grouped = new Map<string, TrainModelItem[]>()
  for (const m of models) {
    const list = grouped.get(m.category) ?? []
    list.push(m)
    grouped.set(m.category, list)
  }

  return (
    <section className="workspace-canvas" style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div className="model-grid__header">
        <h2 style={{ margin: 0, fontFamily: 'var(--font-display)', letterSpacing: '-0.03em' }}>网络模型管理</h2>
        <Button type="button" onClick={onImport}>导入模型</Button>
      </div>
      <div className="model-grid">
        {Array.from(grouped.entries()).map(([category, items]) => (
          <div key={category} className="model-grid__category">
            <h3>{category}</h3>
            <div className="model-grid__cards">
              {items.map((model) => {
                const caps = getModelCapabilities(model)
                return (
                  <div
                    key={model.key}
                    className="model-card"
                    onClick={() => onSelectModel(model.key)}
                    role="button"
                    tabIndex={0}
                    onKeyDown={(e) => { if (e.key === 'Enter') onSelectModel(model.key) }}
                  >
                    <div className="model-card__header">
                      <span className="model-card__name">{model.label}</span>
                      <span className={`model-card__badge${model.built_in ? '' : ' model-card__badge--custom'}`}>
                        {model.built_in ? '内建' : '自定义'}
                      </span>
                    </div>
                    {model.description && (
                      <p className="model-card__description">{model.description}</p>
                    )}
                    {caps.length > 0 && (
                      <div className="model-card__capabilities">
                        {caps.map((cap) => (
                          <span key={cap} className="model-card__cap-tag">{cap}</span>
                        ))}
                      </div>
                    )}
                    {!model.built_in && (
                      <button
                        type="button"
                        className="model-card__delete"
                        onClick={(e) => { e.stopPropagation(); onDeleteModel(model.key) }}
                        title="删除模型"
                      >
                        &times;
                      </button>
                    )}
                  </div>
                )
              })}
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}
