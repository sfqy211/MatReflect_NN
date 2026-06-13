import React, { useEffect, useMemo, useRef, useState } from 'react'

import { useQueryClient } from '@tanstack/react-query'

import { toBackendUrl } from '../lib/api'
import { normalizeMaterialName, parseAssetName } from '../lib/fileNames'
import type { AnalysisImageSet, FileListItem, MaterialMetricItem } from '../types/api'
import { AnalysisResultTable } from './AnalysisResultTable'
import { FeedbackPanel } from './FeedbackPanel'
import { MaterialSelector } from './MaterialSelector'
import { Badge } from './ui/Badge'
import { Button } from './ui/Button'
import { CheckboxField } from './ui/CheckboxField'
import { Field } from './ui/Field'
import {
  useAnalysisImages,
  useEvaluateAnalysis,
  useGenerateComparison,
  useGenerateGrid,
} from '../features/analysis/useAnalysisWorkbench'


type ComparisonColumnDraft = {
  key: 'gt' | 'fullbin' | 'npy' | 'snbrdf'
  enabled: boolean
  imageSet: AnalysisImageSet
  label: string
}

type EvaluationRangeMode = 'all' | 'selected' | 'preset20'
type CompareSelectionMode = 'material' | 'custom'


const AVAILABLE_METRICS = [
  { key: 'psnr', label: 'PSNR' },
  { key: 'ssim', label: 'SSIM' },
  { key: 'delta_e', label: 'Delta E' },
  { key: 'rmse', label: 'RMSE' },
  { key: 'mae', label: 'MAE' },
] as const

const IMAGE_SET_LABELS: Record<AnalysisImageSet, string> = {
  brdfs: 'GT / 参考值',
  fullbin: 'HyperBRDF 输出',
  npy: 'Neural-BRDF 输出',
  snbrdf: 'HyperSNBRDF 输出',
  grids: '网格拼图',
  comparisons: '对比拼图',
}

const TEST_SET_20 = [
  'alum-bronze',
  'beige-fabric',
  'black-obsidian',
  'blue-acrylic',
  'chrome',
  'chrome-steel',
  'dark-red-paint',
  'dark-specular-fabric',
  'delrin',
  'green-metallic-paint',
  'natural-209',
  'nylon',
  'polyethylene',
  'pure-rubber',
  'silicon-nitrade',
  'teflon',
  'violet-rubber',
  'white-diffuse-bball',
  'white-fabric',
  'yellow-paint',
]

function buildMaterialMap(items: FileListItem[]) {
  const map = new Map<string, FileListItem>()
  for (const item of items) {
    const material = normalizeMaterialName(item.name)
    if (!map.has(material)) {
      map.set(material, item)
    }
  }
  return map
}


type AnalysisSubView = 'evaluate' | 'compare' | 'grid' | 'compare-grid'

function AnalysisResultPane({
  title,
  items,
  selectedPath,
  onSelect,
  emptyTitle,
  emptyMessage,
}: {
  title: string
  items: FileListItem[]
  selectedPath: string | null
  onSelect: (path: string) => void
  emptyTitle: string
  emptyMessage: string
}) {
  const [fullscreenImage, setFullscreenImage] = useState<string | null>(null)
  const selectedItem = items.find((item) => item.path === selectedPath) ?? items[0] ?? null

  useEffect(() => {
    if (!selectedItem) {
      return
    }
    if (selectedItem.path !== selectedPath) {
      onSelect(selectedItem.path)
    }
  }, [onSelect, selectedItem, selectedPath])

  if (!selectedItem) {
    return <FeedbackPanel title={emptyTitle} message={emptyMessage} tone="empty" compact />
  }

  const parsedSelected = parseAssetName(selectedItem.name)

  return (
    <div className="analysis-result-shell">
      {fullscreenImage ? (
        <div className="fullscreen-modal" onClick={() => setFullscreenImage(null)} title="点击关闭">
          <img src={fullscreenImage} alt="Detailed preview" className="fullscreen-modal__image" />
        </div>
      ) : null}

      <div className="analysis-result-stage">
        <div className="panel-head">
          <h2>{title}</h2>
          <p>
            {parsedSelected.materialName}
            {parsedSelected.timestampDisplay ? ` · ${parsedSelected.timestampDisplay}` : ''}
          </p>
        </div>
        <div className="analysis-output-wrapper">
          <img
            src={toBackendUrl(selectedItem.preview_url)}
            alt={selectedItem.name}
            className="analysis-output-image analysis-output-image--interactive"
            onClick={() => {
              const url = toBackendUrl(selectedItem.preview_url)
              if (url) {
                setFullscreenImage(url)
              }
            }}
          />
        </div>
      </div>

      <div className="analysis-history-list">
        {items.map((item) => {
          const parsed = parseAssetName(item.name)
          return (
            <button
              key={item.path}
              type="button"
              className={item.path === selectedItem.path ? 'analysis-history-card analysis-history-card--active' : 'analysis-history-card'}
              onClick={() => onSelect(item.path)}
            >
              <div className="analysis-history-card__thumb">
                {item.preview_url ? <img src={toBackendUrl(item.preview_url)} alt={item.name} className="analysis-history-card__image" /> : null}
              </div>
              <div className="analysis-history-card__meta">
                <strong>{parsed.materialName}</strong>
                {parsed.timestampDisplay ? <span>{parsed.timestampDisplay}</span> : null}
              </div>
            </button>
          )
        })}
      </div>
    </div>
  )
}

type SortKey = 'material' | string
type SortDir = 'asc' | 'desc'

const PM_METRIC_LABELS: Record<string, string> = {
  psnr: 'PSNR',
  ssim: 'SSIM',
  delta_e: 'DeltaE',
  rmse: 'RMSE',
  mae: 'MAE',
}

const PM_METRIC_PRECISION: Record<string, number> = {
  psnr: 2,
  ssim: 4,
  delta_e: 4,
  rmse: 4,
  mae: 4,
}

function downloadCsv(filename: string, csvContent: string) {
  const BOM = '﻿'
  const blob = new Blob([BOM + csvContent], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

function exportSummaryCsv(comparisons: import('../types/api').EvaluationPairResult[]) {
  if (!comparisons.length) return
  const first = comparisons[0]
  const metricKeys = Object.keys(first.metrics).filter((k) => (first.metrics as Record<string, number | undefined>)[k] !== undefined)
  const header = ['对比组', ...metricKeys.map((k) => PM_METRIC_LABELS[k] ?? k)]
  const rows = comparisons.map((c) => [
    c.label,
    ...metricKeys.map((k) => {
      const v = (c.metrics as Record<string, number | undefined>)[k]
      return v !== undefined ? v.toFixed(PM_METRIC_PRECISION[k] ?? 4) : ''
    }),
  ])
  downloadCsv('evaluation_summary.csv', [header, ...rows].map((r) => r.join(',')).join('\n'))
}

function exportPerMaterialCsv(perMaterial: MaterialMetricItem[]) {
  if (!perMaterial.length) return
  const first = perMaterial[0]
  const pairLabels = Object.keys(first.metrics)
  const firstPair = Object.values(first.metrics)[0]
  const metricKeys = firstPair ? Object.keys(firstPair).filter((k) => (firstPair as Record<string, number | undefined>)[k] !== undefined) : []
  const header = ['材质', ...pairLabels.flatMap((pl) => metricKeys.map((mk) => `${pl} - ${PM_METRIC_LABELS[mk] ?? mk}`))]
  const rows = perMaterial.map((item) => [
    item.material,
    ...pairLabels.flatMap((pl) => {
      const m = item.metrics[pl]
      return metricKeys.map((mk) => {
        if (!m) return ''
        const v = (m as Record<string, number | undefined>)[mk]
        return v !== undefined ? v.toFixed(PM_METRIC_PRECISION[mk] ?? 4) : ''
      })
    }),
  ])
  downloadCsv('evaluation_per_material.csv', [header, ...rows].map((r) => r.join(',')).join('\n'))
}

function PerMaterialTable({ perMaterial, onExportCsv }: { perMaterial: MaterialMetricItem[]; onExportCsv?: () => void }) {
  const [sortKey, setSortKey] = useState<SortKey>('material')
  const [sortDir, setSortDir] = useState<SortDir>('asc')

  const pairLabels = useMemo(() => {
    const first = perMaterial[0]
    return first ? Object.keys(first.metrics) : []
  }, [perMaterial])

  const metricKeys = useMemo(() => {
    const first = perMaterial[0]
    if (!first) return []
    const firstPair = Object.values(first.metrics)[0]
    if (!firstPair) return []
    return Object.keys(firstPair).filter((k) => (firstPair as Record<string, number | undefined>)[k] !== undefined)
  }, [perMaterial])

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortKey(key)
      setSortDir(key === 'material' ? 'asc' : 'desc')
    }
  }

  const sorted = useMemo(() => {
    const arr = [...perMaterial]
    arr.sort((a, b) => {
      let cmp: number
      if (sortKey === 'material') {
        cmp = a.material.localeCompare(b.material)
      } else {
        const [pairLabel, metricKey] = sortKey.split(':')
        const am = a.metrics[pairLabel]
        const bm = b.metrics[pairLabel]
        const av = am ? (am as Record<string, number | undefined>)[metricKey] ?? 0 : 0
        const bv = bm ? (bm as Record<string, number | undefined>)[metricKey] ?? 0 : 0
        cmp = av - bv
      }
      return sortDir === 'asc' ? cmp : -cmp
    })
    return arr
  }, [perMaterial, sortKey, sortDir])

  const thStyle: React.CSSProperties = { textAlign: 'right', padding: '6px 8px', color: 'var(--text-muted)', fontWeight: 500, cursor: 'pointer', whiteSpace: 'nowrap', userSelect: 'none' }
  const tdStyle: React.CSSProperties = { textAlign: 'right', padding: '6px 8px', fontFamily: 'monospace', fontSize: '0.8rem' }
  const groupSep = '1px solid color-mix(in oklab, var(--border) 40%, transparent)'

  const sortIndicator = (key: SortKey) => sortKey === key ? (sortDir === 'asc' ? ' ↑' : ' ↓') : ''

  return (
    <div style={{ overflow: 'auto', border: '1px solid var(--border)', borderRadius: 4 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 12px', borderBottom: '2px solid var(--border)' }}>
        <strong style={{ fontSize: '0.9rem' }}>分材质评估结果</strong>
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
            <th style={{ ...thStyle, textAlign: 'left', position: 'sticky', left: 0, background: 'var(--surface)' }} onClick={() => toggleSort('material')} rowSpan={2}>
              材质{sortIndicator('material')}
            </th>
            {pairLabels.map((label) => (
              <th key={label} colSpan={metricKeys.length} style={{ ...thStyle, textAlign: 'center', borderLeft: groupSep }}>
                {label}
              </th>
            ))}
          </tr>
          <tr style={{ borderBottom: '2px solid var(--border)' }}>
            {pairLabels.map((label) => (
              metricKeys.map((mk) => (
                <th key={`${label}:${mk}`} style={thStyle} onClick={() => toggleSort(`${label}:${mk}`)}>
                  {PM_METRIC_LABELS[mk] ?? mk}{sortIndicator(`${label}:${mk}`)}
                </th>
              ))
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.map((item) => (
            <tr key={item.material} style={{ borderBottom: '1px solid color-mix(in oklab, var(--border) 40%, transparent)' }}>
              <td style={{ ...tdStyle, textAlign: 'left', fontWeight: 500, position: 'sticky', left: 0, background: 'var(--surface)' }}>{item.material}</td>
              {pairLabels.map((label) => {
                const m = item.metrics[label]
                return m ? (
                  metricKeys.map((mk) => {
                    const val = (m as Record<string, number | undefined>)[mk]
                    const prec = PM_METRIC_PRECISION[mk] ?? 4
                    return (
                      <td key={`${label}:${mk}`} style={{ ...tdStyle, borderLeft: mk === metricKeys[0] ? groupSep : undefined }}>
                        {val !== undefined ? val.toFixed(prec) : '—'}
                      </td>
                    )
                  })
                ) : (
                  metricKeys.map((mk) => (
                    <td key={`${label}:${mk}`} style={{ ...tdStyle, borderLeft: mk === metricKeys[0] ? groupSep : undefined }}>—</td>
                  ))
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function AnalysisWorkbench({ activeSubView, onSubViewChange: _onSubViewChange }: { activeSubView: AnalysisSubView; onSubViewChange: (view: AnalysisSubView) => void }) {
  const queryClient = useQueryClient()

  const [gtLabel, setGtLabel] = useState('GT / 参考值')
  const [method1Enabled, setMethod1Enabled] = useState(true)
  const [method1Label, setMethod1Label] = useState('HyperBRDF 输出')
  const [method2Enabled, setMethod2Enabled] = useState(true)
  const [method2Label, setMethod2Label] = useState('Neural-BRDF 输出')
  const [method3Enabled, setMethod3Enabled] = useState(false)
  const [method3Label, setMethod3Label] = useState('HyperSNBRDF 输出')
  const [evaluationRangeMode, setEvaluationRangeMode] = useState<EvaluationRangeMode>('all')
  const [selectedEvaluationMaterials, setSelectedEvaluationMaterials] = useState<string[]>([])
  const [evaluationMode, setEvaluationMode] = useState<'summary' | 'per_material'>('summary')
  const [selectedMetrics, setSelectedMetrics] = useState<string[]>(['psnr', 'ssim', 'delta_e'])

  const [compareSelectionMode, setCompareSelectionMode] = useState<CompareSelectionMode>('material')
  const [compareLeftSet, setCompareLeftSet] = useState<AnalysisImageSet>('brdfs')
  const [compareRightSet, setCompareRightSet] = useState<AnalysisImageSet>('fullbin')
  const [compareRatio, setCompareRatio] = useState(50)
  const [selectedCompareMaterials, setSelectedCompareMaterials] = useState<string[]>([])
  const [selectedCompareLeftFiles, setSelectedCompareLeftFiles] = useState<string[]>([])
  const [selectedCompareRightFiles, setSelectedCompareRightFiles] = useState<string[]>([])

  const [gridSet, setGridSet] = useState<AnalysisImageSet>('brdfs')
  const [gridOutputName, setGridOutputName] = useState('merged_grid.png')
  const [gridShowNames, setGridShowNames] = useState(true)
  const [gridCellWidth, setGridCellWidth] = useState(256)
  const [gridPadding, setGridPadding] = useState(10)
  const [selectedGridMaterials, setSelectedGridMaterials] = useState<string[]>([])

  const [comparisonColumns, setComparisonColumns] = useState<ComparisonColumnDraft[]>([
    { key: 'gt', enabled: true, imageSet: 'brdfs', label: 'GT / 参考值' },
    { key: 'fullbin', enabled: true, imageSet: 'fullbin', label: 'HyperBRDF 输出' },
    { key: 'npy', enabled: true, imageSet: 'npy', label: 'Neural-BRDF 输出' },
    { key: 'snbrdf', enabled: false, imageSet: 'snbrdf', label: 'HyperSNBRDF 输出' },
  ])
  const [comparisonOutputName, setComparisonOutputName] = useState('merged_comparison.png')
  const [comparisonShowLabel, setComparisonShowLabel] = useState(true)
  const [comparisonShowFilename, setComparisonShowFilename] = useState(true)
  const [selectedComparisonMaterials, setSelectedComparisonMaterials] = useState<string[]>([])
  const [selectedGridOutputPath, setSelectedGridOutputPath] = useState<string | null>(null)
  const [selectedComparisonOutputPath, setSelectedComparisonOutputPath] = useState<string | null>(null)

  const [leftPaneWidth, setLeftPaneWidth] = useState(380)
  const [isDraggingSplitter, setIsDraggingSplitter] = useState(false)
  const resizableContainerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!isDraggingSplitter) return

    const handleMouseMove = (e: MouseEvent) => {
      if (!resizableContainerRef.current) return
      const rect = resizableContainerRef.current.getBoundingClientRect()
      const newWidth = e.clientX - rect.left
      if (newWidth > 200 && newWidth < rect.width - 200) {
        setLeftPaneWidth(newWidth)
      }
    }

    const handleMouseUp = () => {
      setIsDraggingSplitter(false)
    }

    document.addEventListener('mousemove', handleMouseMove)
    document.addEventListener('mouseup', handleMouseUp)
    return () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
    }
  }, [isDraggingSplitter])

  const brdfsQuery = useAnalysisImages('brdfs', '')
  const fullbinQuery = useAnalysisImages('fullbin', '')
  const npyQuery = useAnalysisImages('npy', '')
  const snbrdfQuery = useAnalysisImages('snbrdf', '')
  const gridsQuery = useAnalysisImages('grids', '', '')
  const comparisonsQuery = useAnalysisImages('comparisons', '', '')

  const evaluateMutation = useEvaluateAnalysis()
  const gridMutation = useGenerateGrid()
  const comparisonMutation = useGenerateComparison()

  const brdfItems = brdfsQuery.data?.items ?? []
  const fullbinItems = fullbinQuery.data?.items ?? []
  const npyItems = npyQuery.data?.items ?? []
  const snbrdfItems = snbrdfQuery.data?.items ?? []
  const gridItems = gridsQuery.data?.items ?? []
  const comparisonItems = comparisonsQuery.data?.items ?? []

  const brdfMaterialMap = useMemo(() => buildMaterialMap(brdfItems), [brdfItems])
  const fullbinMaterialMap = useMemo(() => buildMaterialMap(fullbinItems), [fullbinItems])
  const npyMaterialMap = useMemo(() => buildMaterialMap(npyItems), [npyItems])
  const snbrdfMaterialMap = useMemo(() => buildMaterialMap(snbrdfItems), [snbrdfItems])

  const getItemsForSet = (set: AnalysisImageSet) =>
    set === 'brdfs' ? brdfItems : set === 'fullbin' ? fullbinItems : set === 'npy' ? npyItems : snbrdfItems
  const getMaterialMapForSet = (set: AnalysisImageSet) =>
    set === 'brdfs' ? brdfMaterialMap : set === 'fullbin' ? fullbinMaterialMap : set === 'npy' ? npyMaterialMap : snbrdfMaterialMap

  const evaluationMaterials = useMemo(
    () =>
      Array.from(brdfMaterialMap.keys())
        .filter((material) => (!method1Enabled || fullbinMaterialMap.has(material)) && (!method2Enabled || npyMaterialMap.has(material)) && (!method3Enabled || snbrdfMaterialMap.has(material)))
        .sort(),
    [brdfMaterialMap, method1Enabled, method2Enabled, method3Enabled, fullbinMaterialMap, npyMaterialMap, snbrdfMaterialMap],
  )

  const compareLeftItems = useMemo(() => getItemsForSet(compareLeftSet), [brdfItems, compareLeftSet, fullbinItems, npyItems, snbrdfItems])
  const compareRightItems = useMemo(() => getItemsForSet(compareRightSet), [brdfItems, compareRightSet, fullbinItems, npyItems, snbrdfItems])
  const compareLeftMap = useMemo(() => buildMaterialMap(compareLeftItems), [compareLeftItems])
  const compareRightMap = useMemo(() => buildMaterialMap(compareRightItems), [compareRightItems])

  const commonMaterials = useMemo(
    () =>
      Array.from(compareLeftMap.keys())
        .filter((material) => compareRightMap.has(material))
        .sort(),
    [compareLeftMap, compareRightMap],
  )

  const gridSourceItems = useMemo(() => getItemsForSet(gridSet), [brdfItems, fullbinItems, gridSet, npyItems, snbrdfItems])
  const gridMaterials = useMemo(
    () => Array.from(buildMaterialMap(gridSourceItems).keys()).sort(),
    [gridSourceItems],
  )

  const compareGridMaterials = useMemo(() => {
    const enabledSets = comparisonColumns.filter((column) => column.enabled).map((column) => column.imageSet)
    if (enabledSets.length === 0) {
      return []
    }
    const maps = enabledSets.map((imageSet) => getMaterialMapForSet(imageSet))
    const [firstMap, ...restMaps] = maps
    return Array.from(firstMap.keys())
      .filter((material) => restMaps.every((map) => map.has(material)))
      .sort()
  }, [brdfMaterialMap, comparisonColumns, fullbinMaterialMap, npyMaterialMap, snbrdfMaterialMap])

  const sliderMaterial =
    selectedCompareMaterials[0] && commonMaterials.includes(selectedCompareMaterials[0]) ? selectedCompareMaterials[0] : commonMaterials[0]
  const materialModeLeft = sliderMaterial ? compareLeftMap.get(sliderMaterial) : undefined
  const materialModeRight = sliderMaterial ? compareRightMap.get(sliderMaterial) : undefined
  const customModeLeft = selectedCompareLeftFiles[0] ? compareLeftItems.find((item) => item.name === selectedCompareLeftFiles[0]) : compareLeftItems[0]
  const customModeRight = selectedCompareRightFiles[0] ? compareRightItems.find((item) => item.name === selectedCompareRightFiles[0]) : compareRightItems[0]
  const sliderLeft = compareSelectionMode === 'custom' ? customModeLeft : materialModeLeft
  const sliderRight = compareSelectionMode === 'custom' ? customModeRight : materialModeRight

  useEffect(() => {
    const available = new Set(evaluationMaterials)
    setSelectedEvaluationMaterials((current) => current.filter((name) => available.has(name)))
  }, [evaluationMaterials])

  useEffect(() => {
    const available = new Set(commonMaterials)
    setSelectedCompareMaterials((current) => current.filter((name) => available.has(name)))
  }, [commonMaterials])

  useEffect(() => {
    const available = new Set(compareLeftItems.map((item) => item.name))
    setSelectedCompareLeftFiles((current) => current.filter((name) => available.has(name)))
  }, [compareLeftItems])

  useEffect(() => {
    const available = new Set(compareRightItems.map((item) => item.name))
    setSelectedCompareRightFiles((current) => current.filter((name) => available.has(name)))
  }, [compareRightItems])

  useEffect(() => {
    const available = new Set(gridMaterials)
    setSelectedGridMaterials((current) => current.filter((name) => available.has(name)))
  }, [gridMaterials])

  useEffect(() => {
    const available = new Set(compareGridMaterials)
    setSelectedComparisonMaterials((current) => current.filter((name) => available.has(name)))
  }, [compareGridMaterials])

  useEffect(() => {
    if (gridMutation.data?.item.path) {
      setSelectedGridOutputPath(gridMutation.data.item.path)
      return
    }
    if (!selectedGridOutputPath && gridItems[0]) {
      setSelectedGridOutputPath(gridItems[0].path)
    }
    if (selectedGridOutputPath && !gridItems.some((item) => item.path === selectedGridOutputPath)) {
      setSelectedGridOutputPath(gridItems[0]?.path ?? null)
    }
  }, [gridItems, gridMutation.data?.item.path, selectedGridOutputPath])

  useEffect(() => {
    if (comparisonMutation.data?.item.path) {
      setSelectedComparisonOutputPath(comparisonMutation.data.item.path)
      return
    }
    if (!selectedComparisonOutputPath && comparisonItems[0]) {
      setSelectedComparisonOutputPath(comparisonItems[0].path)
    }
    if (selectedComparisonOutputPath && !comparisonItems.some((item) => item.path === selectedComparisonOutputPath)) {
      setSelectedComparisonOutputPath(comparisonItems[0]?.path ?? null)
    }
  }, [comparisonItems, comparisonMutation.data?.item.path, selectedComparisonOutputPath])

  const summaryChips = [
    `评估候选: ${evaluationMaterials.length}`,
    `滑块公共材质: ${commonMaterials.length}`,
    `网格候选: ${gridMaterials.length}`,
    `对比候选: ${compareGridMaterials.length}`,
    `网格输出: ${gridsQuery.data?.total ?? 0}`,
    `对比输出: ${comparisonsQuery.data?.total ?? 0}`,
  ]

  const updateComparisonColumn = (key: ComparisonColumnDraft['key'], patch: Partial<ComparisonColumnDraft>) => {
    setComparisonColumns((current) => current.map((column) => (column.key === key ? { ...column, ...patch } : column)))
  }

  const evaluate = async () => {
    const evaluationSelection =
      evaluationRangeMode === 'all'
        ? []
        : evaluationRangeMode === 'preset20'
          ? evaluationMaterials.filter((material) => TEST_SET_20.includes(material))
          : selectedEvaluationMaterials

    // 按启用顺序映射到 method1/2/3
    const enabledMethods: { imageSet: AnalysisImageSet; label: string }[] = []
    if (method1Enabled) enabledMethods.push({ imageSet: 'fullbin', label: method1Label })
    if (method2Enabled) enabledMethods.push({ imageSet: 'npy', label: method2Label })
    if (method3Enabled) enabledMethods.push({ imageSet: 'snbrdf', label: method3Label })

    const m0 = enabledMethods[0]
    const m1 = enabledMethods[1]
    const m2 = enabledMethods[2]

    await evaluateMutation.mutateAsync({
      gt_set: 'brdfs',
      method1_set: m0?.imageSet ?? 'fullbin',
      method2_set: m1?.imageSet ?? 'npy',
      method3_set: m2?.imageSet ?? null,
      gt_dir: '',
      method1_dir: '',
      method2_dir: '',
      method3_dir: '',
      gt_label: gtLabel,
      method1_label: m0?.label ?? '',
      method2_label: m1?.label ?? '',
      method3_label: m2?.label ?? '',
      selected_materials: evaluationSelection,
      metrics: selectedMetrics,
    })
  }

  const generateGrid = async () => {
    const result = await gridMutation.mutateAsync({
      image_set: gridSet,
      source_dir: '',
      output_dir: '',
      output_name: gridOutputName,
      show_names: gridShowNames,
      cell_width: gridCellWidth,
      padding: gridPadding,
      selected_materials: selectedGridMaterials,
    })
    await queryClient.invalidateQueries({ queryKey: ['analysis-images', 'grids'] })
    return result
  }

  const generateComparison = async () => {
    const result = await comparisonMutation.mutateAsync({
      columns: comparisonColumns
        .filter((column) => column.enabled)
        .map((column) => ({
          image_set: column.imageSet,
          directory: '',
          label: column.label,
        })),
      selected_materials: selectedComparisonMaterials,
      show_label: comparisonShowLabel,
      show_filename: comparisonShowFilename,
      output_dir: '',
      output_name: comparisonOutputName,
    })
    await queryClient.invalidateQueries({ queryKey: ['analysis-images', 'comparisons'] })
    return result
  }

  return (
    <section className="workspace-canvas">
      <div className="detail-pill-grid">
        {summaryChips.map((chip) => (
          <Badge key={chip} variant="detail">
              {chip}
            </Badge>
        ))}
      </div>

      <div className="analysis-layout">
        <div className="resizable-container" ref={resizableContainerRef}>
          <div className="resizable-pane resizable-pane--left" style={{ width: leftPaneWidth }}>
            {activeSubView === 'evaluate' ? (
              <section className="analysis-section">
                <div className="detail-board__lead">
                  <h3>量化评估</h3>
                </div>

                <div className="eval-group">
                  <span className="eval-group__title">基本设置</span>
                  <Field label="评估范围">
                    <select value={evaluationRangeMode} onChange={(event) => setEvaluationRangeMode(event.target.value as EvaluationRangeMode)}>
                      <option value="all">全部材质</option>
                      <option value="selected">手动选择</option>
                      <option value="preset20">预设 20 材质</option>
                    </select>
                  </Field>
                  <Field label="GT 标签">
                    <input value={gtLabel} onChange={(event) => setGtLabel(event.target.value)} />
                  </Field>
                </div>

                <div className="eval-group">
                  <span className="eval-group__title">对比方法</span>
                  <div className="eval-method-row">
                    <input className="eval-method-row__check" type="checkbox" checked={method1Enabled} onChange={(event) => setMethod1Enabled(event.target.checked)} />
                    <span className="eval-method-row__name">方法一</span>
                    <input className="eval-method-row__label" value={method1Label} onChange={(event) => setMethod1Label(event.target.value)} disabled={!method1Enabled} />
                  </div>
                  <div className="eval-method-row">
                    <input className="eval-method-row__check" type="checkbox" checked={method2Enabled} onChange={(event) => setMethod2Enabled(event.target.checked)} />
                    <span className="eval-method-row__name">方法二</span>
                    <input className="eval-method-row__label" value={method2Label} onChange={(event) => setMethod2Label(event.target.value)} disabled={!method2Enabled} />
                  </div>
                  <div className="eval-method-row">
                    <input className="eval-method-row__check" type="checkbox" checked={method3Enabled} onChange={(event) => setMethod3Enabled(event.target.checked)} />
                    <span className="eval-method-row__name">方法三</span>
                    <input className="eval-method-row__label" value={method3Label} onChange={(event) => setMethod3Label(event.target.value)} disabled={!method3Enabled} />
                  </div>
                </div>

                <div className="eval-group">
                  <span className="eval-group__title">评估指标</span>
                  <div className="eval-metrics-grid">
                    {AVAILABLE_METRICS.map((m) => (
                      <label key={m.key}>
                        <input
                          type="checkbox"
                          checked={selectedMetrics.includes(m.key)}
                          onChange={(event) => {
                            if (event.target.checked) {
                              setSelectedMetrics((prev) => [...prev, m.key])
                            } else {
                              setSelectedMetrics((prev) => prev.filter((k) => k !== m.key))
                            }
                          }}
                        />
                        <span>{m.label}</span>
                      </label>
                    ))}
                  </div>
                </div>

                {evaluationRangeMode === 'selected' ? (
                  <div className="eval-group">
                    <span className="eval-group__title">选择材质</span>
                    <MaterialSelector
                      title="选择评估材质"
                      items={evaluationMaterials}
                      selectedItems={selectedEvaluationMaterials}
                      onSelectionChange={setSelectedEvaluationMaterials}
                      multiSelect={true}
                      emptyMessage="当前没有可用于量化评估的公共材质。"
                      presets={[
                        {
                          label: '预设 20',
                          filter: (items) => items.filter((item) => TEST_SET_20.includes(item.name)).map((item) => item.name),
                        },
                      ]}
                    />
                  </div>
                ) : null}

                <div className="render-actions" style={{ gap: 8 }}>
                  <Button type="button" onClick={() => { setEvaluationMode('summary'); void evaluate() }} disabled={evaluateMutation.isPending}>
                    整体评估
                  </Button>
                  <Button type="button" onClick={() => { setEvaluationMode('per_material'); void evaluate() }} disabled={evaluateMutation.isPending}>
                    分材质评估
                  </Button>
                </div>
                <p className="muted" style={{ fontSize: '0.78rem' }}>评估所用图像目录统一读取设置页中的默认路径。</p>
                
                {evaluateMutation.data ? (
                  <p className="muted" style={{ marginTop: '12px' }}>
                    已处理 {evaluateMutation.data.processed_count} 个材质
                    {evaluateMutation.data.skipped.length > 0 ? `，跳过 ${evaluateMutation.data.skipped.length} 个` : ''}
                  </p>
                ) : null}
                {evaluateMutation.error instanceof Error ? <FeedbackPanel title="量化评估失败" message={evaluateMutation.error.message} tone="error" compact /> : null}
              </section>
            ) : null}

            {activeSubView === 'compare' ? (
              <section className="analysis-section">
                <div className="detail-board__lead">
                  <h3>图像对比滑块</h3>
                </div>

                <div className="render-form-grid">
                  <Field label="选择方式">
              <select value={compareSelectionMode} onChange={(event) => setCompareSelectionMode(event.target.value as CompareSelectionMode)}>
                      <option value="material">同材质联动</option>
                      <option value="custom">自定义左右图</option>
                    </select>
            </Field>
                  <Field label="左图">
              <select value={compareLeftSet} onChange={(event) => setCompareLeftSet(event.target.value as AnalysisImageSet)}>
                      <option value="brdfs">GT / 参考值</option>
                      <option value="fullbin">HyperBRDF 输出</option>
                      <option value="npy">Neural-BRDF 输出</option>
                      <option value="snbrdf">HyperSNBRDF 输出</option>
                    </select>
            </Field>
                  <Field label="右图">
              <select value={compareRightSet} onChange={(event) => setCompareRightSet(event.target.value as AnalysisImageSet)}>
                      <option value="brdfs">GT / 参考值</option>
                      <option value="fullbin">HyperBRDF 输出</option>
                      <option value="npy">Neural-BRDF 输出</option>
                      <option value="snbrdf">HyperSNBRDF 输出</option>
                    </select>
            </Field>
                  {compareSelectionMode === 'material' ? (
                    <Field label="对比材质">
              <MaterialSelector
                      title="对比材质"
                      items={commonMaterials}
                      selectedItems={sliderMaterial ? [sliderMaterial] : []}
                      onSelectionChange={(selected) => setSelectedCompareMaterials(selected.length > 0 ? [selected[0]] : [])}
                      multiSelect={false}
                      emptyMessage="没有同时在左右图集中找到相同的材质"
                    />
            </Field>
                  ) : null}
                </div>

                {compareSelectionMode === 'custom' ? (
                  <div className="render-form-grid">
                    <Field label="左侧文件">
              <MaterialSelector
                        title="选择左侧输出"
                        items={compareLeftItems}
                        selectedItems={selectedCompareLeftFiles}
                        onSelectionChange={(selected) => setSelectedCompareLeftFiles(selected.length > 0 ? [selected[0]] : [])}
                        multiSelect={false}
                        emptyMessage="左图当前没有可用输出"
                        formatName={(name) => {
                          const parsed = parseAssetName(name)
                          return parsed.timestampDisplay ? `${parsed.materialName} · ${parsed.timestampDisplay}` : parsed.materialName
                        }}
                      />
            </Field>
                    <Field label="右侧文件">
              <MaterialSelector
                        title="选择右侧输出"
                        items={compareRightItems}
                        selectedItems={selectedCompareRightFiles}
                        onSelectionChange={(selected) => setSelectedCompareRightFiles(selected.length > 0 ? [selected[0]] : [])}
                        multiSelect={false}
                        emptyMessage="右图当前没有可用输出"
                        formatName={(name) => {
                          const parsed = parseAssetName(name)
                          return parsed.timestampDisplay ? `${parsed.materialName} · ${parsed.timestampDisplay}` : parsed.materialName
                        }}
                      />
            </Field>
                  </div>
                ) : null}
                <p className="muted">
                  {compareSelectionMode === 'custom'
                    ? '自定义模式下可以直接对比同一渲染方式下不同时间的输出文件。'
                    : '同材质联动模式会自动对齐左右图中同名材质。'}
                </p>
              </section>
            ) : null}

            {activeSubView === 'grid' || activeSubView === 'compare-grid' ? (
              <section className="analysis-section" style={{ flex: 'none', overflowY: 'visible', paddingBottom: 0 }}>
                <div className="detail-board__lead">
                  <h3>材质选择</h3>
                </div>
                <div className="render-form-grid">
                  <Field label="源材质列表">
              <MaterialSelector
                      title="选择材质"
                      items={activeSubView === 'grid' ? gridMaterials : compareGridMaterials}
                      selectedItems={activeSubView === 'grid' ? selectedGridMaterials : selectedComparisonMaterials}
                      onSelectionChange={activeSubView === 'grid' ? setSelectedGridMaterials : setSelectedComparisonMaterials}
                      multiSelect={true}
                      emptyMessage={
                        activeSubView === 'grid'
                          ? '当前源图片集中没有可用材质，请检查设置页中的默认输入输出路径。'
                          : '当前启用列之间没有公共材质，请检查输出结果或调整启用列。'
                      }
                      presets={[
                        { label: '预设 20', filter: (items) => items.filter((item) => TEST_SET_20.includes(item.name)).map((item) => item.name) },
                      ]}
                    />
            </Field>
                </div>
              </section>
            ) : null}

            {activeSubView === 'grid' ? (
              <section className="analysis-section">
                <div className="detail-board__lead" style={{ marginTop: '16px' }}>
                  <h3>网格拼图设置</h3>
                </div>
                <div className="render-form-grid">
                  <Field label="源图片集">
              <select value={gridSet} onChange={(event) => setGridSet(event.target.value as AnalysisImageSet)}>
                      <option value="brdfs">GT / 参考值</option>
                      <option value="fullbin">HyperBRDF 输出</option>
                      <option value="npy">Neural-BRDF 输出</option>
                      <option value="snbrdf">HyperSNBRDF 输出</option>
                    </select>
            </Field>
                  <Field label="输出文件名">
              <input value={gridOutputName} onChange={(event) => setGridOutputName(event.target.value)} />
            </Field>
                  <Field label="单图宽度">
              <input type="number" value={gridCellWidth} onChange={(event) => setGridCellWidth(Number(event.target.value) || 256)} />
            </Field>
                  <Field label="间距">
              <input type="number" value={gridPadding} onChange={(event) => setGridPadding(Number(event.target.value) || 10)} />
            </Field>
                </div>
                <CheckboxField 
                  style={{ marginBottom: '12px' }}
                  label="显示文件名" 
                  checked={gridShowNames} 
                  onChange={(event) => setGridShowNames(event.target.checked)} 
                />
                <div className="render-actions">
                  <Button type="button"  onClick={() => void generateGrid()} disabled={gridMutation.isPending}>
                    生成网格图
                  </Button>
                </div>
                <p className="muted">源图与输出目录统一读取设置页中的默认路径。</p>
              </section>
            ) : null}

            {activeSubView === 'compare-grid' ? (
              <section className="analysis-section">
                <div className="detail-board__lead" style={{ marginTop: '16px' }}>
                  <h3>对比拼图设置</h3>
                </div>

                <div className="render-form-grid">
                  {comparisonColumns.map((column) => (
                    <label key={`${column.key}-label`} className="field">
                      <span>{IMAGE_SET_LABELS[column.imageSet]} 标签</span>
                      <input value={column.label} onChange={(event) => updateComparisonColumn(column.key, { label: event.target.value })} />
                    </label>
                  ))}
                </div>

                <div className="render-toggle-row">
                  {comparisonColumns.map((column) => (
                    <CheckboxField 
                      key={`${column.key}-enabled`}
                      label={`启用 ${column.label || IMAGE_SET_LABELS[column.imageSet]}`}
                      checked={column.enabled}
                      onChange={(event) => updateComparisonColumn(column.key, { enabled: event.target.checked })}
                    />
                  ))}
                </div>

                <div className="render-form-grid">
                  <Field label="输出文件名">
              <input value={comparisonOutputName} onChange={(event) => setComparisonOutputName(event.target.value)} />
            </Field>
                </div>

                <div className="render-toggle-row">
                  <CheckboxField label="显示列标题" checked={comparisonShowLabel} onChange={(event) => setComparisonShowLabel(event.target.checked)} />
                  <CheckboxField label="显示文件名" checked={comparisonShowFilename} onChange={(event) => setComparisonShowFilename(event.target.checked)} />
                </div>

                <div className="render-actions">
                  <Button type="button"  onClick={() => void generateComparison()} disabled={comparisonMutation.isPending}>
                    生成对比拼图
                  </Button>
                </div>
                <p className="muted">对比源图与输出目录统一读取设置页中的默认路径。</p>
              </section>
            ) : null}
          </div>

          <div 
            className={`splitter ${isDraggingSplitter ? 'splitter--dragging' : ''}`} 
            onMouseDown={(e) => {
              e.preventDefault()
              setIsDraggingSplitter(true)
            }}
          />

          <div className="resizable-pane resizable-pane--right">
            {activeSubView === 'evaluate' ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 16, flex: 1, minHeight: 0, overflow: 'auto' }}>
                {evaluationMode === 'summary' ? (
                  evaluateMutation.data?.comparisons?.length ? (
                    <AnalysisResultTable
                      comparisons={evaluateMutation.data.comparisons}
                      onExportCsv={() => exportSummaryCsv(evaluateMutation.data!.comparisons)}
                    />
                  ) : (
                    <FeedbackPanel title="暂无评估数据" message="请点击「整体评估」按钮生成结果。" tone="empty" compact />
                  )
                ) : (
                  evaluateMutation.data?.per_material?.length ? (
                    <PerMaterialTable
                      perMaterial={evaluateMutation.data.per_material}
                      onExportCsv={() => exportPerMaterialCsv(evaluateMutation.data!.per_material)}
                    />
                  ) : (
                    <FeedbackPanel title="暂无分材质数据" message="请点击「分材质评估」按钮生成结果。" tone="empty" compact />
                  )
                )}
              </div>
            ) : null}

            {activeSubView === 'compare' ? (
              sliderLeft?.preview_url && sliderRight?.preview_url ? (
                <>
                  <div className="compare-stage">
                    <img src={toBackendUrl(sliderRight.preview_url)} alt={sliderRight.name} className="compare-stage__image" />
                    <img 
                      src={toBackendUrl(sliderLeft.preview_url)} 
                      alt={sliderLeft.name} 
                      className="compare-stage__image compare-stage__overlay-image" 
                      style={{
                        clipPath: `inset(0 ${100 - compareRatio}% 0 0)`
                      }}
                    />
                    <div className="compare-stage__divider" style={{ left: `${compareRatio}%` }} />
                  </div>
                  <input
                    type="range"
                    min={0}
                    max={100}
                    value={compareRatio}
                    onChange={(event) => setCompareRatio(Number(event.target.value))}
                    className="compare-slider"
                  />
                  <p className="muted">
                    当前对比:
                    {' '}
                    {parseAssetName(sliderLeft.name).materialName}
                    {' '}
                    vs
                    {' '}
                    {parseAssetName(sliderRight.name).materialName}
                  </p>
                </>
              ) : (
                <FeedbackPanel
                  title="当前没有可用于滑块对比的图片"
                  message={
                    compareSelectionMode === 'custom'
                      ? '请在左右侧文件选择器中各选择一张输出图片。'
                      : '请确认左右图片集下存在相同材质名的输出。'
                  }
                  tone="empty"
                  compact
                />
              )
            ) : null}

            {activeSubView === 'grid' ? (
              <>
                {gridMutation.error instanceof Error ? <FeedbackPanel title="网格拼图生成失败" message={gridMutation.error.message} tone="error" compact /> : null}
                {gridMutation.isPending && gridItems.length === 0 ? <p className="muted">正在生成网格拼图...</p> : null}
                {!gridMutation.isPending || gridItems.length > 0 ? (
                  <AnalysisResultPane
                    title="网格拼图结果"
                    items={gridItems}
                    selectedPath={selectedGridOutputPath}
                    onSelect={setSelectedGridOutputPath}
                    emptyTitle="等待生成"
                    emptyMessage="配置完成后点击“生成网格图”。"
                  />
                ) : null}
              </>
            ) : null}

            {activeSubView === 'compare-grid' ? (
              <>
                {comparisonMutation.error instanceof Error ? <FeedbackPanel title="对比拼图生成失败" message={comparisonMutation.error.message} tone="error" compact /> : null}
                {comparisonMutation.isPending && comparisonItems.length === 0 ? <p className="muted">正在生成对比拼图...</p> : null}
                {!comparisonMutation.isPending || comparisonItems.length > 0 ? (
                  <AnalysisResultPane
                    title="对比拼图结果"
                    items={comparisonItems}
                    selectedPath={selectedComparisonOutputPath}
                    onSelect={setSelectedComparisonOutputPath}
                    emptyTitle="等待生成"
                    emptyMessage="配置完成后点击“生成对比拼图”。"
                  />
                ) : null}
              </>
            ) : null}
          </div>
        </div>
      </div>
    </section>
  )
}
