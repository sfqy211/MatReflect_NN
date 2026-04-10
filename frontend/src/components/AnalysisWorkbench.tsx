import { useEffect, useMemo, useRef, useState } from 'react'

import { useQueryClient } from '@tanstack/react-query'

import { toBackendUrl } from '../lib/api'
import type { AnalysisImageSet, FileListItem } from '../types/api'
import { FeedbackPanel } from './FeedbackPanel'
import { GalleryPreview } from './GalleryPreview'
import { MaterialSelector } from './MaterialSelector'
import {
  useAnalysisImages,
  useDeleteAnalysisImage,
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


function normalizeMaterialName(fileName: string) {
  return fileName.replace(/(_\d{1,2}_\d{6})?(_fc1)?(\.fullbin)?(\.binary)?\.png$/i, '')
}


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


type AnalysisSubView = 'preview' | 'evaluate' | 'compare' | 'grid' | 'compare-grid'

export function AnalysisWorkbench({ activeSubView, onSubViewChange: _onSubViewChange }: { activeSubView: AnalysisSubView; onSubViewChange: (view: AnalysisSubView) => void }) {
  const queryClient = useQueryClient()

  const [previewSet, setPreviewSet] = useState<AnalysisImageSet>('brdfs')
  const [previewSearch, setPreviewSearch] = useState('')
  const [previewDirectory, setPreviewDirectory] = useState('')
  const [previewSelectedPaths, setPreviewSelectedPaths] = useState<string[]>([])

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

  const previewQuery = useAnalysisImages(previewSet, previewSearch, previewDirectory)
  const brdfsQuery = useAnalysisImages('brdfs', '', gtDir)
  const fullbinQuery = useAnalysisImages('fullbin', '', method1Dir)
  const npyQuery = useAnalysisImages('npy', '', method2Dir)
  const gridsQuery = useAnalysisImages('grids', '', '')
  const comparisonsQuery = useAnalysisImages('comparisons', '', '')

  const deleteImageMutation = useDeleteAnalysisImage()
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

  const previewItems = previewQuery.data?.items ?? []
  const previewSelectedNames = previewSelectedPaths.map(p => previewItems.find(i => i.path === p)?.name).filter(Boolean) as string[]

  const summaryChips = [
    `预览目录: ${previewQuery.data?.resolved_path ?? '-'}`,
    `候选材质: ${baseMaterials.length}`,
    `已选材质: ${selectedMaterials.length}`,
    `网格输出: ${gridsQuery.data?.total ?? 0}`,
    `对比输出: ${comparisonsQuery.data?.total ?? 0}`,
  ]

  const updateComparisonColumn = (key: ComparisonColumnDraft['key'], patch: Partial<ComparisonColumnDraft>) => {
    setComparisonColumns((current) => current.map((column) => (column.key === key ? { ...column, ...patch } : column)))
  }

  const deletePreviewImage = async () => {
    if (previewSelectedPaths.length === 0) {
      return
    }
    await deleteImageMutation.mutateAsync({
      image_paths: previewSelectedPaths,
      delete_matching_exr: true,
    })
    setPreviewSelectedPaths([])
    await queryClient.invalidateQueries({ queryKey: ['analysis-images'] })
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
          <span key={chip} className="detail-pill">
            {chip}
          </span>
        ))}
      </div>

      <div className="analysis-layout">
        <div className="resizable-container" ref={resizableContainerRef}>
          <div className="resizable-pane resizable-pane--left" style={{ width: leftPaneWidth }}>
            {activeSubView === 'preview' ? (
              <section className="analysis-section">
                <div className="detail-board__lead">
                  <h3>图片预览</h3>
                </div>

                <div className="render-form-grid" style={{ gridTemplateColumns: '1fr' }}>
                  <label className="field">
                    <span>预览类型</span>
                    <select value={previewSet} onChange={(event) => setPreviewSet(event.target.value as AnalysisImageSet)}>
                      {Object.entries(IMAGE_SET_LABELS).map(([key, label]) => (
                        <option key={key} value={key}>
                          {label}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="field">
                    <span>预览目录</span>
                    <input value={previewDirectory} onChange={(event) => setPreviewDirectory(event.target.value)} placeholder={previewQuery.data?.resolved_path ?? '留空使用默认目录'} />
                  </label>
                  <label className="field">
                    <span>搜索</span>
                    <input value={previewSearch} onChange={(event) => setPreviewSearch(event.target.value)} placeholder="搜索图片名" />
                  </label>
                </div>

                <div className="render-form-grid" style={{ gridTemplateColumns: '1fr' }}>
                  <label className="field">
                    <span>删除目标</span>
                    <MaterialSelector
                      title="选择要删除的图片"
                      items={previewItems}
                      selectedItems={previewSelectedNames}
                      onSelectionChange={(selected) => {
                        const selectedPaths = selected
                          .map((name) => previewItems.find((i) => i.name === name)?.path)
                          .filter(Boolean) as string[]
                        setPreviewSelectedPaths(selectedPaths)
                      }}
                      multiSelect={true}
                      emptyMessage="当前目录下没有图片"
                    />
                  </label>
                </div>

                <div className="render-actions">
                  <button type="button" className="theme-toggle render-actions--danger" onClick={() => void deletePreviewImage()} disabled={previewSelectedPaths.length === 0 || deleteImageMutation.isPending}>
                    删除选中的 {previewSelectedPaths.length > 0 ? previewSelectedPaths.length : ''} 张图片及关联 EXR
                  </button>
                </div>

                {deleteImageMutation.data ? (
                  <p className="muted">
                    已删除 {deleteImageMutation.data.deleted.length} 个文件
                    {deleteImageMutation.data.missing.length > 0 ? `，未找到 ${deleteImageMutation.data.missing.length} 个文件` : ''}
                  </p>
                ) : null}
                {deleteImageMutation.error instanceof Error ? <FeedbackPanel title="删除失败" message={deleteImageMutation.error.message} tone="error" compact /> : null}
              </section>
            ) : null}

            {activeSubView === 'evaluate' ? (
              <section className="analysis-section">
                <div className="detail-board__lead">
                  <h3>量化评估</h3>
                </div>

                <div className="render-form-grid" style={{ gridTemplateColumns: '1fr' }}>
                  <label className="field">
                    <span>GT 目录</span>
                    <input value={gtDir} onChange={(event) => setGtDir(event.target.value)} placeholder={brdfsQuery.data?.resolved_path ?? '留空使用默认目录'} />
                  </label>
                  <label className="field">
                    <span>方法一目录</span>
                    <input value={method1Dir} onChange={(event) => setMethod1Dir(event.target.value)} placeholder={fullbinQuery.data?.resolved_path ?? '留空使用默认目录'} />
                  </label>
                  <label className="field">
                    <span>方法二目录</span>
                    <input value={method2Dir} onChange={(event) => setMethod2Dir(event.target.value)} placeholder={npyQuery.data?.resolved_path ?? '留空使用默认目录'} />
                  </label>
                  <label className="field">
                    <span>GT 标签</span>
                    <input value={gtLabel} onChange={(event) => setGtLabel(event.target.value)} />
                  </label>
                  <label className="field">
                    <span>方法一标签</span>
                    <input value={method1Label} onChange={(event) => setMethod1Label(event.target.value)} />
                  </label>
                  <label className="field">
                    <span>方法二标签</span>
                    <input value={method2Label} onChange={(event) => setMethod2Label(event.target.value)} />
                  </label>
                </div>

                <div className="render-actions">
                  <button type="button" className="theme-toggle" onClick={() => void evaluate()} disabled={evaluateMutation.isPending}>
                    开始评估
                  </button>
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

                <div className="render-form-grid" style={{ gridTemplateColumns: '1fr' }}>
                  <label className="field">
                    <span>左图</span>
                    <select value={compareLeftSet} onChange={(event) => setCompareLeftSet(event.target.value as AnalysisImageSet)}>
                      <option value="brdfs">GT / BRDF</option>
                      <option value="fullbin">FullBin</option>
                      <option value="npy">NPY</option>
                    </select>
                  </label>
                  <label className="field">
                    <span>右图</span>
                    <select value={compareRightSet} onChange={(event) => setCompareRightSet(event.target.value as AnalysisImageSet)}>
                      <option value="brdfs">GT / BRDF</option>
                      <option value="fullbin">FullBin</option>
                      <option value="npy">NPY</option>
                    </select>
                  </label>
                  <label className="field">
                    <span>对比材质</span>
                    <MaterialSelector
                      title="对比材质"
                      items={commonMaterials}
                      selectedItems={sliderMaterial ? [sliderMaterial] : []}
                      onSelectionChange={(selected) => setSelectedMaterials(selected.length > 0 ? [selected[0]] : [])}
                      multiSelect={false}
                      emptyMessage="没有同时在左右图集中找到相同的材质"
                    />
                  </label>
                </div>
              </section>
            ) : null}

            {activeSubView === 'grid' || activeSubView === 'compare-grid' ? (
              <section className="analysis-section" style={{ flex: 'none', overflowY: 'visible', paddingBottom: 0 }}>
                <div className="detail-board__lead">
                  <h3>材质选择</h3>
                </div>
                <div className="render-form-grid" style={{ gridTemplateColumns: '1fr' }}>
                  <label className="field">
                    <span>源材质列表</span>
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
                  </label>
                </div>
              </section>
            ) : null}

            {activeSubView === 'grid' ? (
              <section className="analysis-section">
                <div className="detail-board__lead" style={{ marginTop: '16px' }}>
                  <h3>网格拼图设置</h3>
                </div>
                <div className="render-form-grid" style={{ gridTemplateColumns: '1fr' }}>
                  <label className="field">
                    <span>源图片集</span>
                    <select value={gridSet} onChange={(event) => setGridSet(event.target.value as AnalysisImageSet)}>
                      <option value="brdfs">GT / BRDF</option>
                      <option value="fullbin">FullBin</option>
                      <option value="npy">NPY</option>
                    </select>
                  </label>
                  <label className="field">
                    <span>源目录</span>
                    <input value={gridSourceDir} onChange={(event) => setGridSourceDir(event.target.value)} placeholder="留空使用源图片集默认目录" />
                  </label>
                  <label className="field">
                    <span>输出目录</span>
                    <input value={gridOutputDir} onChange={(event) => setGridOutputDir(event.target.value)} />
                  </label>
                  <label className="field">
                    <span>输出文件名</span>
                    <input value={gridOutputName} onChange={(event) => setGridOutputName(event.target.value)} />
                  </label>
                  <label className="field">
                    <span>单图宽度</span>
                    <input type="number" value={gridCellWidth} onChange={(event) => setGridCellWidth(Number(event.target.value) || 256)} />
                  </label>
                  <label className="field">
                    <span>间距</span>
                    <input type="number" value={gridPadding} onChange={(event) => setGridPadding(Number(event.target.value) || 10)} />
                  </label>
                </div>
                <label className="toggle-field" style={{ marginBottom: '12px' }}>
                  <input type="checkbox" checked={gridShowNames} onChange={(event) => setGridShowNames(event.target.checked)} />
                  <span>显示文件名</span>
                </label>
                <div className="render-actions">
                  <button type="button" className="theme-toggle" onClick={() => void generateGrid()} disabled={gridMutation.isPending}>
                    生成网格图
                  </button>
                </div>
              </section>
            ) : null}

            {activeSubView === 'compare-grid' ? (
              <section className="analysis-section">
                <div className="detail-board__lead" style={{ marginTop: '16px' }}>
                  <h3>对比拼图设置</h3>
                </div>

                <div className="render-form-grid" style={{ gridTemplateColumns: '1fr' }}>
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

                <div className="render-form-grid" style={{ gridTemplateColumns: '1fr' }}>
                  {comparisonColumns.map((column) => (
                    <label key={`${column.key}-label`} className="field">
                      <span>{IMAGE_SET_LABELS[column.imageSet]} 标签</span>
                      <input value={column.label} onChange={(event) => updateComparisonColumn(column.key, { label: event.target.value })} />
                    </label>
                  ))}
                </div>

                <div className="render-toggle-row">
                  {comparisonColumns.map((column) => (
                    <label key={`${column.key}-enabled`} className="toggle-field">
                      <input type="checkbox" checked={column.enabled} onChange={(event) => updateComparisonColumn(column.key, { enabled: event.target.checked })} />
                      <span>启用 {column.label || IMAGE_SET_LABELS[column.imageSet]}</span>
                    </label>
                  ))}
                </div>

                <div className="render-form-grid" style={{ gridTemplateColumns: '1fr' }}>
                  <label className="field">
                    <span>输出目录</span>
                    <input value={comparisonOutputDir} onChange={(event) => setComparisonOutputDir(event.target.value)} />
                  </label>
                  <label className="field">
                    <span>输出文件名</span>
                    <input value={comparisonOutputName} onChange={(event) => setComparisonOutputName(event.target.value)} />
                  </label>
                </div>

                <div className="render-toggle-row">
                  <label className="toggle-field">
                    <input type="checkbox" checked={comparisonShowLabel} onChange={(event) => setComparisonShowLabel(event.target.checked)} />
                    <span>显示列标题</span>
                  </label>
                  <label className="toggle-field">
                    <input type="checkbox" checked={comparisonShowFilename} onChange={(event) => setComparisonShowFilename(event.target.checked)} />
                    <span>显示文件名</span>
                  </label>
                </div>

                <div className="render-actions">
                  <button type="button" className="theme-toggle" onClick={() => void generateComparison()} disabled={comparisonMutation.isPending}>
                    生成对比拼图
                  </button>
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
            {activeSubView === 'preview' ? (
              <GalleryPreview items={previewItems} isLoading={previewQuery.isLoading} />
            ) : null}

            {activeSubView === 'evaluate' ? (
              <div className="metric-grid">
                {(evaluateMutation.data?.comparisons ?? []).map((comparison) => (
                  <article key={comparison.label} className="metric-card">
                    <strong>{comparison.label}</strong>
                    <span>PSNR {comparison.metrics.psnr.toFixed(2)} dB</span>
                    <span>SSIM {comparison.metrics.ssim.toFixed(4)}</span>
                    <span>Delta E {comparison.metrics.delta_e.toFixed(4)}</span>
                  </article>
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
