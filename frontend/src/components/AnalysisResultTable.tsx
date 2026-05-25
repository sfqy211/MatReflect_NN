import { useMemo, useState } from 'react'

import type { EvaluationPairResult } from '../types/api'

type SortKey = 'label' | 'psnr' | 'ssim' | 'delta_e'
type SortDir = 'asc' | 'desc'

type AnalysisResultTableProps = {
  comparisons: EvaluationPairResult[]
  onExportCsv?: () => void
}

export function AnalysisResultTable({ comparisons, onExportCsv }: AnalysisResultTableProps) {
  const [sortKey, setSortKey] = useState<SortKey>('label')
  const [sortDir, setSortDir] = useState<SortDir>('asc')

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortKey(key)
      setSortDir(key === 'label' ? 'asc' : 'desc')
    }
  }

  const sorted = useMemo(() => {
    const arr = [...comparisons]
    arr.sort((a, b) => {
      let cmp: number
      switch (sortKey) {
        case 'label': cmp = a.label.localeCompare(b.label); break
        case 'psnr': cmp = a.metrics.psnr - b.metrics.psnr; break
        case 'ssim': cmp = a.metrics.ssim - b.metrics.ssim; break
        case 'delta_e': cmp = a.metrics.delta_e - b.metrics.delta_e; break
      }
      return sortDir === 'asc' ? cmp : -cmp
    })
    return arr
  }, [comparisons, sortKey, sortDir])

  const indicator = (key: SortKey) => sortKey === key ? (sortDir === 'asc' ? ' ↑' : ' ↓') : ''
  const thStyle: React.CSSProperties = { textAlign: 'right', padding: '8px 12px', color: 'var(--text-muted)', fontWeight: 500, cursor: 'pointer', userSelect: 'none' }
  const tdStyle: React.CSSProperties = { textAlign: 'right', padding: '8px 12px', fontFamily: 'monospace' }

  return (
    <div style={{ overflow: 'auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
        <strong style={{ fontSize: '0.9rem' }}>评估结果</strong>
        {onExportCsv ? (
          <button
            type="button"
            onClick={onExportCsv}
            style={{
              padding: '4px 12px',
              fontSize: '0.8rem',
              background: 'var(--surface-soft)',
              border: '1px solid var(--border)',
              borderRadius: 4,
              cursor: 'pointer',
              color: 'var(--text-muted)',
            }}
          >
            导出 CSV
          </button>
        ) : null}
      </div>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
        <thead>
          <tr style={{ borderBottom: '2px solid var(--border)' }}>
            <th style={{ ...thStyle, textAlign: 'left' }} onClick={() => toggleSort('label')}>对比组{indicator('label')}</th>
            <th style={thStyle} onClick={() => toggleSort('psnr')}>PSNR (dB){indicator('psnr')}</th>
            <th style={thStyle} onClick={() => toggleSort('ssim')}>SSIM{indicator('ssim')}</th>
            <th style={thStyle} onClick={() => toggleSort('delta_e')}>Delta E{indicator('delta_e')}</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((comp) => (
            <tr key={comp.label} style={{ borderBottom: '1px solid color-mix(in oklab, var(--border) 40%, transparent)' }}>
              <td style={{ ...tdStyle, textAlign: 'left' }}>{comp.label}</td>
              <td style={tdStyle}>{comp.metrics.psnr.toFixed(2)}</td>
              <td style={tdStyle}>{comp.metrics.ssim.toFixed(4)}</td>
              <td style={tdStyle}>{comp.metrics.delta_e.toFixed(4)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
