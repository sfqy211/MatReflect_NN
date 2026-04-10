import { useEffect, useMemo, useRef, useState } from 'react'

import { useQueryClient } from '@tanstack/react-query'

import { toBackendUrl } from '../lib/api'
import { normalizeMaterialName } from '../lib/fileNames'
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
  directory: string
}


const IMAGE_SET_LABELS: Record<AnalysisImageSet, string> = {
  brdfs: 'GT / BRDF',
  fullbin: 'FullBin',
  npy: 'NPY',
  grids: '网格拼图',
  comparisons: '对比拼图',
}

const DEFAULT_GRID_OUTPUT_DIR = 'data/outputs/grids'
const DEFAULT_COMPARISON_OUTPUT_DIR = 'data/outputs/comparisons'


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

export function AnalysisWorkbench({ activeSubView, onSubViewChange: _onSubViewChange }: { activeSubView: AnalysisSubView; onSubViewChange: (view: AnalysisSubView) => void }) {
  const queryClient = useQueryClient()

  const [gtDir, setGtDir] = useState('')
  const [method1Dir, setMethod1Dir] = useState('')
  const [method2Dir, setMethod2Dir] = useState('')
  const [gtLabel, setGtLabel] = useState('GT / BRDF')
  const [method1Label, setMethod1Label] = useState('FullBin')
  const [method2Label, setMethod2Label] = useState('NPY')

  const [compareLeftSet, setCompareLeftSet] = useState<AnalysisImageSet>('brdfs')
  const [compareRightSet, setCompareRightSet] = useState<AnalysisImageSet>('fullbin')
  const [compareRatio, setCompareRatio] = useState(50)

  const [selectedMaterials, setSelectedMaterials] = useState<string[]>([])

  const [gridSet, setGridSet] = useState<AnalysisImageSet>('brdfs')
  const [gridSourceDir, setGridSourceDir] = useState('')
  const [gridOutputDir, setGridOutputDir] = useState(DEFAULT_GRID_OUTPUT_DIR)
  const [gridOutputName, setGridOutputName] = useState('merged_grid.png')
  const [gridShowNames, setGridShowNames] = useState(true)
  const [gridCellWidth, setGridCellWidth] = useState(256)
  const [gridPadding, setGridPadding] = useState(10)

  const [comparisonColumns, setComparisonColumns] = useState<ComparisonColumnDraft[]>([
    { key: 'gt', enabled: true, imageSet: 'brdfs', label: 'BRDF', directory: '' },
    { key: 'fullbin', enabled: true, imageSet: 'fullbin', label: 'FullBin', directory: '' },
    { key: 'npy', enabled: true, imageSet: 'npy', label: 'NPY', directory: '' },
  ])
  const [comparisonOutputDir, setComparisonOutputDir] = useState(DEFAULT_COMPARISON_OUTPUT_DIR)
  const [comparisonOutputName, setComparisonOutputName] = useState('merged_comparison.png')
  const [comparisonShowLabel, setComparisonShowLabel] = useState(true)
  const [comparisonShowFilename, setComparisonShowFilename] = useState(true)

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

  const brdfsQuery = useAnalysisImages('brdfs', '', gtDir)
  const fullbinQuery = useAnalysisImages('fullbin', '', method1Dir)
  const npyQuery = useAnalysisImages('npy', '', method2Dir)
  const gridsQuery = useAnalysisImages('grids', '', '')
  const comparisonsQuery = useAnalysisImages('comparisons', '', '')

  const evaluateMutation = useEvaluateAnalysis()
  const gridMutation = useGenerateGrid()
  const comparisonMutation = useGenerateComparison()

  const baseMaterials = useMemo(
    () => Array.from(buildMaterialMap(brdfsQuery.data?.items ?? []).keys()).sort(),
    [brdfsQuery.data?.items],
  )

  const compareLeftMap = useMemo(
    () =>
      buildMaterialMap(
        (compareLeftSet === 'brdfs'
          ? brdfsQuery.data
          : compareLeftSet === 'fullbin'
            ? fullbinQuery.data
            : npyQuery.data
        )?.items ?? [],
      ),
    [brdfsQuery.data, compareLeftSet, fullbinQuery.data, npyQuery.data],
  )

  const compareRightMap = useMemo(
    () =>
      buildMaterialMap(
        (compareRightSet === 'brdfs'
          ? brdfsQuery.data
          : compareRightSet === 'fullbin'
            ? fullbinQuery.data
            : npyQuery.data
        )?.items ?? [],
      ),
    [brdfsQuery.data, compareRightSet, fullbinQuery.data, npyQuery.data],
  )

  const commonMaterials = useMemo(
    () =>
      Array.from(compareLeftMap.keys())
        .filter((material) => compareRightMap.has(material))
        .sort(),
    [compareLeftMap, compareRightMap],
  )

  const sliderMaterial =
    selectedMaterials[0] && commonMaterials.includes(selectedMaterials[0]) ? selectedMaterials[0] : commonMaterials[0]
  const sliderLeft = sliderMaterial ? compareLeftMap.get(sliderMaterial) : undefined
  const sliderRight = sliderMaterial ? compareRightMap.get(sliderMaterial) : undefined

  const summaryChips = [
    `候选材质: ${baseMaterials.length}`,
    `已选材质: ${selectedMaterials.length}`,
    `网格输出: ${gridsQuery.data?.total ?? 0}`,
    `对比输出: ${comparisonsQuery.data?.total ?? 0}`,
  ]

  const updateComparisonColumn = (key: ComparisonColumnDraft['key'], patch: Partial<ComparisonColumnDraft>) => {
    setComparisonColumns((current) => current.map((column) => (column.key === key ? { ...column, ...patch } : column)))
  }

  const evaluate = async () => {
    await evaluateMutation.mutateAsync({
      gt_set: 'brdfs',
      method1_set: 'fullbin',
      method2_set: 'npy',
      gt_dir: gtDir,
      method1_dir: method1Dir,
      method2_dir: method2Dir,
      gt_label: gtLabel,
      method1_label: method1Label,
      method2_label: method2Label,
      selected_materials: selectedMaterials,
    })
  }

  const generateGrid = async () => {
    const result = await gridMutation.mutateAsync({
      image_set: gridSet,
      source_dir: gridSourceDir,
      output_dir: gridOutputDir,
      output_name: gridOutputName,
      show_names: gridShowNames,
      cell_width: gridCellWidth,
      padding: gridPadding,
      selected_materials: selectedMaterials,
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
          directory: column.directory,
          label: column.label,
        })),
      selected_materials: selectedMaterials,
      show_label: comparisonShowLabel,
      show_filename: comparisonShowFilename,
      output_dir: comparisonOutputDir,
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
                  <Field label="GT 目录">
              <input value={gtDir} onChange={(event) => setGtDir(event.target.value)} placeholder={brdfsQuery.data?.resolved_path ?? '留空使用默认目录'} />
            </Field>
                  <Field label="方法一目录">
              <input value={method1Dir} onChange={(event) => setMethod1Dir(event.target.value)} placeholder={fullbinQuery.data?.resolved_path ?? '留空使用默认目录'} />
            </Field>
                  <Field label="方法二目录">
              <input value={method2Dir} onChange={(event) => setMethod2Dir(event.target.value)} placeholder={npyQuery.data?.resolved_path ?? '留空使用默认目录'} />
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

                <div className="render-actions">
                  <Button type="button"  onClick={() => void evaluate()} disabled={evaluateMutation.isPending}>
                    开始评估
                  </Button>
                </div>
                
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
                  <Field label="左图">
              <select value={compareLeftSet} onChange={(event) => setCompareLeftSet(event.target.value as AnalysisImageSet)}>
                      <option value="brdfs">GT / BRDF</option>
                      <option value="fullbin">FullBin</option>
                      <option value="npy">NPY</option>
                    </select>
            </Field>
                  <Field label="右图">
              <select value={compareRightSet} onChange={(event) => setCompareRightSet(event.target.value as AnalysisImageSet)}>
                      <option value="brdfs">GT / BRDF</option>
                      <option value="fullbin">FullBin</option>
                      <option value="npy">NPY</option>
                    </select>
            </Field>
                  <Field label="对比材质">
              <MaterialSelector
                      title="对比材质"
                      items={commonMaterials}
                      selectedItems={sliderMaterial ? [sliderMaterial] : []}
                      onSelectionChange={(selected) => setSelectedMaterials(selected.length > 0 ? [selected[0]] : [])}
                      multiSelect={false}
                      emptyMessage="没有同时在左右图集中找到相同的材质"
                    />
            </Field>
                </div>
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
                      items={baseMaterials}
                      selectedItems={selectedMaterials}
                      onSelectionChange={setSelectedMaterials}
                      multiSelect={true}
                      emptyMessage="请先生成 GT / BRDF 图片，或检查 GT 目录配置。"
                      presets={[
                        { label: '选前 20 个', filter: (items) => items.slice(0, 20).map((i) => i.name) },
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
                      <option value="brdfs">GT / BRDF</option>
                      <option value="fullbin">FullBin</option>
                      <option value="npy">NPY</option>
                    </select>
            </Field>
                  <Field label="源目录">
              <input value={gridSourceDir} onChange={(event) => setGridSourceDir(event.target.value)} placeholder="留空使用源图片集默认目录" />
            </Field>
                  <Field label="输出目录">
              <input value={gridOutputDir} onChange={(event) => setGridOutputDir(event.target.value)} />
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
              </section>
            ) : null}

            {activeSubView === 'compare-grid' ? (
              <section className="analysis-section">
                <div className="detail-board__lead" style={{ marginTop: '16px' }}>
                  <h3>对比拼图设置</h3>
                </div>

                <div className="render-form-grid">
                  {comparisonColumns.map((column) => (
                    <label key={column.key} className="field">
                      <span>{column.label || IMAGE_SET_LABELS[column.imageSet]}目录</span>
                      <input
                        value={column.directory}
                        onChange={(event) => updateComparisonColumn(column.key, { directory: event.target.value })}
                        placeholder="留空使用默认目录"
                      />
                    </label>
                  ))}
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
                  <Field label="输出目录">
              <input value={comparisonOutputDir} onChange={(event) => setComparisonOutputDir(event.target.value)} />
            </Field>
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
                  <p className="muted">当前材质: {sliderMaterial}</p>
                </>
              ) : (
                <FeedbackPanel title="当前没有可用于滑块对比的成对图片" message="请确认左右图片集下存在相同材质名的输出。" tone="empty" compact />
              )
            ) : null}

            {activeSubView === 'grid' ? (
              <>
                {gridMutation.error instanceof Error ? <FeedbackPanel title="网格拼图生成失败" message={gridMutation.error.message} tone="error" compact /> : null}
                {gridMutation.data?.item.preview_url ? (
                  <div className="analysis-output-wrapper">
                    <img src={toBackendUrl(gridMutation.data.item.preview_url)} alt={gridMutation.data.item.name} className="analysis-output-image" />
                  </div>
                ) : (
                  !gridMutation.isPending && <FeedbackPanel title="等待生成" message="配置完成后点击“生成网格图”。" tone="empty" compact />
                )}
              </>
            ) : null}

            {activeSubView === 'compare-grid' ? (
              <>
                {comparisonMutation.error instanceof Error ? <FeedbackPanel title="对比拼图生成失败" message={comparisonMutation.error.message} tone="error" compact /> : null}
                {comparisonMutation.data?.item.preview_url ? (
                  <div className="analysis-output-wrapper">
                    <img src={toBackendUrl(comparisonMutation.data.item.preview_url)} alt={comparisonMutation.data.item.name} className="analysis-output-image" />
                  </div>
                ) : (
                  !comparisonMutation.isPending && <FeedbackPanel title="等待生成" message="配置完成后点击“生成对比拼图”。" tone="empty" compact />
                )}
              </>
            ) : null}
          </div>
        </div>
      </div>
    </section>
  )
}
