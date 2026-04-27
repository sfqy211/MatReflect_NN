import type { EvaluationPairResult } from '../types/api'

type AnalysisResultTableProps = {
  comparisons: EvaluationPairResult[]
  onExportCsv?: () => void
}

export function AnalysisResultTable({ comparisons, onExportCsv }: AnalysisResultTableProps) {
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
            <th style={{ textAlign: 'left', padding: '8px 12px', color: 'var(--text-muted)', fontWeight: 500 }}>对比组</th>
            <th style={{ textAlign: 'right', padding: '8px 12px', color: 'var(--text-muted)', fontWeight: 500 }}>PSNR (dB)</th>
            <th style={{ textAlign: 'right', padding: '8px 12px', color: 'var(--text-muted)', fontWeight: 500 }}>SSIM</th>
            <th style={{ textAlign: 'right', padding: '8px 12px', color: 'var(--text-muted)', fontWeight: 500 }}>Delta E</th>
          </tr>
        </thead>
        <tbody>
          {comparisons.map((comp) => (
            <tr key={comp.label} style={{ borderBottom: '1px solid color-mix(in oklab, var(--border) 40%, transparent)' }}>
              <td style={{ padding: '8px 12px' }}>{comp.label}</td>
              <td style={{ textAlign: 'right', padding: '8px 12px', fontFamily: 'monospace' }}>{comp.metrics.psnr.toFixed(2)}</td>
              <td style={{ textAlign: 'right', padding: '8px 12px', fontFamily: 'monospace' }}>{comp.metrics.ssim.toFixed(4)}</td>
              <td style={{ textAlign: 'right', padding: '8px 12px', fontFamily: 'monospace' }}>{comp.metrics.delta_e.toFixed(4)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
