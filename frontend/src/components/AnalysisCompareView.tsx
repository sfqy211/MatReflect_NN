import { useState } from 'react'
import { toBackendUrl } from '../lib/api'
import { parseAssetName } from '../lib/fileNames'
import type { FileListItem } from '../types/api'

type AnalysisCompareViewProps = {
  gtItems: FileListItem[]
  method1Items: FileListItem[]
  method2Items: FileListItem[]
  method1Label: string
  method2Label: string
  commonMaterials: string[]
  selectedMaterial: string | null
  onMaterialChange: (material: string) => void
}

export function AnalysisCompareView({
  gtItems,
  method1Items,
  method2Items,
  method1Label,
  method2Label,
  commonMaterials,
  selectedMaterial,
  onMaterialChange,
}: AnalysisCompareViewProps) {
  const [sliderPosition, setSliderPosition] = useState(50)
  const [compareMode, setCompareMode] = useState<'side-by-side' | 'slider'>('side-by-side')

  const currentMaterial = selectedMaterial || commonMaterials[0]
  if (!currentMaterial) {
    return (
      <div style={{ textAlign: 'center', padding: 40, color: 'var(--text-muted)' }}>
        没有公共材质可用于对比
      </div>
    )
  }

  const gtItem = gtItems.find((item) => parseAssetName(item.name).materialName === currentMaterial)
  const m1Item = method1Items.find((item) => parseAssetName(item.name).materialName === currentMaterial)
  const m2Item = method2Items.find((item) => parseAssetName(item.name).materialName === currentMaterial)

  if (!gtItem) {
    return (
      <div style={{ textAlign: 'center', padding: 40, color: 'var(--text-muted)' }}>
        未找到材质: {currentMaterial}
      </div>
    )
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* 控制栏 */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '8px 0', borderBottom: '1px solid var(--border)', marginBottom: 12 }}>
        <select
          value={currentMaterial}
          onChange={(e) => onMaterialChange(e.target.value)}
          style={{ flex: 1, maxWidth: 200 }}
        >
          {commonMaterials.map((m) => (
            <option key={m} value={m}>{m}</option>
          ))}
        </select>
        <div style={{ display: 'flex', gap: 4 }}>
          <button
            type="button"
            onClick={() => setCompareMode('side-by-side')}
            style={{
              padding: '4px 10px',
              background: compareMode === 'side-by-side' ? 'var(--accent)' : 'transparent',
              color: compareMode === 'side-by-side' ? '#fff' : 'var(--text-muted)',
              border: '1px solid var(--border)',
              borderRadius: 4,
              cursor: 'pointer',
              fontSize: '0.82rem',
            }}
          >
            并排对比
          </button>
          <button
            type="button"
            onClick={() => setCompareMode('slider')}
            style={{
              padding: '4px 10px',
              background: compareMode === 'slider' ? 'var(--accent)' : 'transparent',
              color: compareMode === 'slider' ? '#fff' : 'var(--text-muted)',
              border: '1px solid var(--border)',
              borderRadius: 4,
              cursor: 'pointer',
              fontSize: '0.82rem',
            }}
          >
            滑块对比
          </button>
        </div>
      </div>

      {/* 对比区域 */}
      <div style={{ flex: 1, overflow: 'auto' }}>
        {compareMode === 'side-by-side' ? (
          <div style={{ display: 'grid', gridTemplateColumns: gtItem && m1Item && m2Item ? 'repeat(3, 1fr)' : 'repeat(2, 1fr)', gap: 8 }}>
            <CompareColumn label="GT / 参考值" item={gtItem} />
            {m1Item ? <CompareColumn label={method1Label} item={m1Item} /> : null}
            {m2Item ? <CompareColumn label={method2Label} item={m2Item} /> : null}
          </div>
        ) : (
          <div style={{ position: 'relative', display: 'flex', justifyContent: 'center', alignItems: 'flex-start' }}>
            {m1Item ? (
              <>
                <img src={toBackendUrl(m1Item.preview_url)} alt={m1Item.name} style={{ maxWidth: '100%', maxHeight: 500, objectFit: 'contain' }} />
                <img
                  src={toBackendUrl(gtItem.preview_url)}
                  alt={gtItem.name}
                  style={{
                    position: 'absolute',
                    maxWidth: '100%',
                    maxHeight: 500,
                    objectFit: 'contain',
                    clipPath: `inset(0 ${100 - sliderPosition}% 0 0)`,
                  }}
                />
                <div style={{ position: 'absolute', left: `${sliderPosition}%`, top: 0, bottom: 0, width: 2, background: 'var(--accent)' }} />
              </>
            ) : (
              <img src={toBackendUrl(gtItem.preview_url)} alt={gtItem.name} style={{ maxWidth: '100%', maxHeight: 500, objectFit: 'contain' }} />
            )}
          </div>
        )}

        {compareMode === 'slider' && m1Item ? (
          <input
            type="range"
            min={0}
            max={100}
            value={sliderPosition}
            onChange={(e) => setSliderPosition(Number(e.target.value))}
            style={{ width: '100%', marginTop: 8 }}
          />
        ) : null}
      </div>
    </div>
  )
}

function CompareColumn({ label, item }: { label: string; item: FileListItem }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      <span style={{ fontSize: '0.82rem', color: 'var(--text-muted)', textAlign: 'center' }}>{label}</span>
      <img src={toBackendUrl(item.preview_url)} alt={item.name} style={{ width: '100%', objectFit: 'contain', borderRadius: 4 }} />
    </div>
  )
}
