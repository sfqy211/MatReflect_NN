import { useMemo, useState } from 'react'

import type { EvaluationPairResult } from '../types/api'

type SortKey = 'label' | string
type SortDir = 'asc' | 'desc'

const METRIC_LABELS: Record<string, string> = {
  psnr: 'PSNR (dB)',
  ssim: 'SSIM',
  delta_e: 'Delta E',
  rmse: 'RMSE',
  mae: 'MAE',
}

const METRIC_PRECISION: Record<string, number> = {
  psnr: 2,
  ssim: 4,
  delta_e: 4,
  rmse: 4,
  mae: 4,
}

type AnalysisResultTableProps = {
  comparisons: EvaluationPairResult[]
  onExportCsv?: () => void
}

export function AnalysisResultTable({ comparisons, onExportCsv }: AnalysisResultTableProps) {
  const [sortKey, setSortKey] = useState<SortKey>('label')
  const [sortDir, setSortDir] = useState<SortDir>('asc')

  const metricKeys = useMemo(() => {
    const first = comparisons[0]
    if (!first) return []
    return Object.keys(first.metrics).filter((k) => (first.metrics as Record<string, number | undefined>)[k] !== undefined)
  }, [comparisons])

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
      if (sortKey === 'label') {
        cmp = a.label.localeCompare(b.label)
      } else {
        const av = (a.metrics as Record<string, number | undefined>)[sortKey] ?? 0
        const bv = (b.metrics as Record<string, number | undefined>)[sortKey] ?? 0
        cmp = av - bv
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
            {metricKeys.map((key) => (
              <th key={key} style={thStyle} onClick={() => toggleSort(key)}>
                {METRIC_LABELS[key] ?? key}{indicator(key)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.map((comp) => (
            <tr key={comp.label} style={{ borderBottom: '1px solid color-mix(in oklab, var(--border) 40%, transparent)' }}>
              <td style={{ ...tdStyle, textAlign: 'left' }}>{comp.label}</td>
              {metricKeys.map((key) => {
                const val = (comp.metrics as Record<string, number | undefined>)[key]
                const prec = METRIC_PRECISION[key] ?? 4
                return (
                  <td key={key} style={tdStyle}>{val !== undefined ? val.toFixed(prec) : '—'}</td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
