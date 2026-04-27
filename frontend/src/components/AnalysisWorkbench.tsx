import { useEffect, useMemo, useRef, useState } from 'react'

import { useQueryClient } from '@tanstack/react-query'

import { toBackendUrl } from '../lib/api'
import { normalizeMaterialName, parseAssetName } from '../lib/fileNames'
import type { AnalysisImageSet, FileListItem } from '../types/api'
import { FeedbackPanel } from './FeedbackPanel'
import { MaterialSelector } from './MaterialSelector'
import { Badge } from './ui/Badge'
import { Button } from './ui/Button'
import { Card } from './ui/Card'
import { CheckboxField } from './ui/CheckboxField'
import { Field } from './ui/Field'
import {
  useAnalysisImages,
  useEvaluateAnalysis,
  useGenerateComparison,
  useGenerateGrid,
} from '../features/analysis/useAnalysisWorkbench'


type ComparisonColumnDraft = {
  key: 'gt' | 'fullbin' | 'npy'
  enabled: boolean
  imageSet: AnalysisImageSet
  label: string
}

type EvaluationRangeMode = 'all' | 'selected' | 'preset20'
type CompareSelectionMode = 'material' | 'custom'


const IMAGE_SET_LABELS: Record<AnalysisImageSet, string> = {
  brdfs: 'GT / 参考值',
  fullbin: 'HyperBRDF 输出',
  npy: 'Neural-BRDF 输出',
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

export function AnalysisWorkbench({ activeSubView, onSubViewChange: _onSubViewChange }: { activeSubView: AnalysisSubView; onSubViewChange: (view: AnalysisSubView) => void }) {
  const queryClient = useQueryClient()

  const [gtLabel, setGtLabel] = useState('GT / 参考值')
  const [method1Label, setMethod1Label] = useState('HyperBRDF 输出')
  const [method2Label, setMethod2Label] = useState('Neural-BRDF 输出')
  const [evaluationRangeMode, setEvaluationRangeMode] = useState<EvaluationRangeMode>('all')
  const [selectedEvaluationMaterials, setSelectedEvaluationMaterials] = useState<string[]>([])

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
  const gridsQuery = useAnalysisImages('grids', '', '')
  const comparisonsQuery = useAnalysisImages('comparisons', '', '')

  const evaluateMutation = useEvaluateAnalysis()
  const gridMutation = useGenerateGrid()
  const comparisonMutation = useGenerateComparison()

  const brdfItems = brdfsQuery.data?.items ?? []
  const fullbinItems = fullbinQuery.data?.items ?? []
  const npyItems = npyQuery.data?.items ?? []
  const gridItems = gridsQuery.data?.items ?? []
  const comparisonItems = comparisonsQuery.data?.items ?? []

  const brdfMaterialMap = useMemo(() => buildMaterialMap(brdfItems), [brdfItems])
  const fullbinMaterialMap = useMemo(() => buildMaterialMap(fullbinItems), [fullbinItems])
  const npyMaterialMap = useMemo(() => buildMaterialMap(npyItems), [npyItems])

  const evaluationMaterials = useMemo(
    () =>
      Array.from(brdfMaterialMap.keys())
        .filter((material) => fullbinMaterialMap.has(material) && npyMaterialMap.has(material))
        .sort(),
    [brdfMaterialMap, fullbinMaterialMap, npyMaterialMap],
  )

  const compareLeftItems = useMemo(
    () => (compareLeftSet === 'brdfs' ? brdfItems : compareLeftSet === 'fullbin' ? fullbinItems : npyItems),
    [brdfItems, compareLeftSet, fullbinItems, npyItems],
  )
  const compareRightItems = useMemo(
    () => (compareRightSet === 'brdfs' ? brdfItems : compareRightSet === 'fullbin' ? fullbinItems : npyItems),
    [brdfItems, compareRightSet, fullbinItems, npyItems],
  )
  const compareLeftMap = useMemo(() => buildMaterialMap(compareLeftItems), [compareLeftItems])
  const compareRightMap = useMemo(() => buildMaterialMap(compareRightItems), [compareRightItems])

  const commonMaterials = useMemo(
    () =>
      Array.from(compareLeftMap.keys())
        .filter((material) => compareRightMap.has(material))
        .sort(),
    [compareLeftMap, compareRightMap],
  )

  const gridSourceItems = useMemo(
    () => (gridSet === 'brdfs' ? brdfItems : gridSet === 'fullbin' ? fullbinItems : npyItems),
    [brdfItems, fullbinItems, gridSet, npyItems],
  )
  const gridMaterials = useMemo(
    () => Array.from(buildMaterialMap(gridSourceItems).keys()).sort(),
    [gridSourceItems],
  )

  const compareGridMaterials = useMemo(() => {
    const enabledSets = comparisonColumns.filter((column) => column.enabled).map((column) => column.imageSet)
    if (enabledSets.length === 0) {
      return []
    }
    const maps = enabledSets.map((imageSet) =>
      imageSet === 'brdfs' ? brdfMaterialMap : imageSet === 'fullbin' ? fullbinMaterialMap : npyMaterialMap,
    )
    const [firstMap, ...restMaps] = maps
    return Array.from(firstMap.keys())
      .filter((material) => restMaps.every((map) => map.has(material)))
      .sort()
  }, [brdfMaterialMap, comparisonColumns, fullbinMaterialMap, npyMaterialMap])

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

    await evaluateMutation.mutateAsync({
      gt_set: 'brdfs',
      method1_set: 'fullbin',
      method2_set: 'npy',
      gt_dir: '',
      method1_dir: '',
      method2_dir: '',
      gt_label: gtLabel,
      method1_label: method1Label,
      method2_label: method2Label,
      selected_materials: evaluationSelection,
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

                <div className="render-form-grid">
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
                  <Field label="方法一标签">
              <input value={method1Label} onChange={(event) => setMethod1Label(event.target.value)} />
            </Field>
                  <Field label="方法二标签">
              <input value={method2Label} onChange={(event) => setMethod2Label(event.target.value)} />
            </Field>
                </div>

                {evaluationRangeMode === 'selected' ? (
                  <div className="render-form-grid">
                    <Field label="评估材质">
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
            </Field>
                  </div>
                ) : null}

                <div className="render-actions">
                  <Button type="button"  onClick={() => void evaluate()} disabled={evaluateMutation.isPending}>
                    开始评估
                  </Button>
                </div>
                <p className="muted">评估所用图像目录统一读取设置页中的默认路径。</p>
                
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
                    </select>
            </Field>
                  <Field label="右图">
              <select value={compareRightSet} onChange={(event) => setCompareRightSet(event.target.value as AnalysisImageSet)}>
                      <option value="brdfs">GT / 参考值</option>
                      <option value="fullbin">HyperBRDF 输出</option>
                      <option value="npy">Neural-BRDF 输出</option>
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
                        { label: '选前 20 个', filter: (items) => items.slice(0, 20).map((i) => i.name) },
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
              <div className="metric-grid">
                {(evaluateMutation.data?.comparisons ?? []).map((comparison) => (
                  <Card key={comparison.label} variant="metric">
                    <strong>{comparison.label}</strong>
                    <span>PSNR {comparison.metrics.psnr.toFixed(2)} dB</span>
                    <span>SSIM {comparison.metrics.ssim.toFixed(4)}</span>
                    <span>Delta E {comparison.metrics.delta_e.toFixed(4)}</span>
                  </Card>
                ))}
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
