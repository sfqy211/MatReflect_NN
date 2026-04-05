import { useMemo, useState } from 'react'

import { useQueryClient } from '@tanstack/react-query'

import { toBackendUrl } from '../lib/api'
import type { AnalysisImageSet, FileListItem } from '../types/api'
import { GalleryPreview } from './GalleryPreview'
import {
  useAnalysisImages,
  useEvaluateAnalysis,
  useGenerateComparison,
  useGenerateGrid,
} from '../features/analysis/useAnalysisWorkbench'


const IMAGE_SET_LABELS: Record<AnalysisImageSet, string> = {
  brdfs: 'GT / BRDF',
  fullbin: 'FullBin',
  npy: 'NPY',
  grids: '网格拼图',
  comparisons: '对比拼图',
}


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


export function AnalysisWorkbench() {
  const queryClient = useQueryClient()
  const [previewSet, setPreviewSet] = useState<AnalysisImageSet>('brdfs')
  const [previewSearch, setPreviewSearch] = useState('')
  const [compareLeftSet, setCompareLeftSet] = useState<AnalysisImageSet>('brdfs')
  const [compareRightSet, setCompareRightSet] = useState<AnalysisImageSet>('fullbin')
  const [compareRatio, setCompareRatio] = useState(50)
  const [selectedMaterials, setSelectedMaterials] = useState<string[]>([])
  const [gridSet, setGridSet] = useState<AnalysisImageSet>('brdfs')
  const [gridOutputName, setGridOutputName] = useState('merged_grid.png')
  const [gridShowNames, setGridShowNames] = useState(true)
  const [gridCellWidth, setGridCellWidth] = useState(256)
  const [gridPadding, setGridPadding] = useState(10)
  const [comparisonOutputName, setComparisonOutputName] = useState('merged_comparison.png')
  const [comparisonShowLabel, setComparisonShowLabel] = useState(true)
  const [comparisonShowFilename, setComparisonShowFilename] = useState(true)

  const previewQuery = useAnalysisImages(previewSet, previewSearch)
  const brdfsQuery = useAnalysisImages('brdfs', '')
  const fullbinQuery = useAnalysisImages('fullbin', '')
  const npyQuery = useAnalysisImages('npy', '')
  const gridsQuery = useAnalysisImages('grids', '')
  const comparisonsQuery = useAnalysisImages('comparisons', '')

  const evaluateMutation = useEvaluateAnalysis()
  const gridMutation = useGenerateGrid()
  const comparisonMutation = useGenerateComparison()

  const baseMaterials = useMemo(
    () => Array.from(buildMaterialMap(brdfsQuery.data?.items ?? []).keys()).sort(),
    [brdfsQuery.data?.items],
  )

  const compareLeftMap = useMemo(() => buildMaterialMap((compareLeftSet === 'brdfs' ? brdfsQuery.data : compareLeftSet === 'fullbin' ? fullbinQuery.data : npyQuery.data)?.items ?? []), [
    brdfsQuery.data,
    compareLeftSet,
    fullbinQuery.data,
    npyQuery.data,
  ])
  const compareRightMap = useMemo(() => buildMaterialMap((compareRightSet === 'brdfs' ? brdfsQuery.data : compareRightSet === 'fullbin' ? fullbinQuery.data : npyQuery.data)?.items ?? []), [
    brdfsQuery.data,
    compareRightSet,
    fullbinQuery.data,
    npyQuery.data,
  ])

  const commonMaterials = useMemo(
    () =>
      Array.from(compareLeftMap.keys())
        .filter((material) => compareRightMap.has(material))
        .sort(),
    [compareLeftMap, compareRightMap],
  )
  const sliderMaterial = selectedMaterials[0] && commonMaterials.includes(selectedMaterials[0]) ? selectedMaterials[0] : commonMaterials[0]
  const sliderLeft = sliderMaterial ? compareLeftMap.get(sliderMaterial) : undefined
  const sliderRight = sliderMaterial ? compareRightMap.get(sliderMaterial) : undefined

  const evaluate = async () => {
    await evaluateMutation.mutateAsync({
      gt_set: 'brdfs',
      method1_set: 'fullbin',
      method2_set: 'npy',
      selected_materials: selectedMaterials,
    })
  }

  const generateGrid = async () => {
    const result = await gridMutation.mutateAsync({
      image_set: gridSet,
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
      columns: [
        { image_set: 'brdfs', label: 'BRDF' },
        { image_set: 'fullbin', label: 'FullBin' },
        { image_set: 'npy', label: 'NPY' },
      ],
      selected_materials: selectedMaterials,
      show_label: comparisonShowLabel,
      show_filename: comparisonShowFilename,
      output_name: comparisonOutputName,
    })
    await queryClient.invalidateQueries({ queryKey: ['analysis-images', 'comparisons'] })
    return result
  }

  const toggleMaterial = (material: string) => {
    setSelectedMaterials((current) =>
      current.includes(material) ? current.filter((item) => item !== material) : [...current, material],
    )
  }

  return (
    <section className="workspace-canvas">
      <div className="workspace-hero">
        <div>
          <h2>材质表达结果分析</h2>
        </div>
      </div>

      <div className="detail-pill-grid">
        <span className="detail-pill">预览集: {IMAGE_SET_LABELS[previewSet]}</span>
        <span className="detail-pill">候选材质: {baseMaterials.length}</span>
        <span className="detail-pill">已选材质: {selectedMaterials.length}</span>
        <span className="detail-pill">网格输出: {gridsQuery.data?.total ?? 0}</span>
        <span className="detail-pill">对比输出: {comparisonsQuery.data?.total ?? 0}</span>
      </div>

      <div className="analysis-layout">
        <section className="analysis-section">
          <div className="detail-board__lead">
            <h3>图片预览</h3>
          </div>

          <div className="render-form-grid">
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
              <span>搜索</span>
              <input value={previewSearch} onChange={(event) => setPreviewSearch(event.target.value)} placeholder="搜索图片名" />
            </label>
          </div>

          <GalleryPreview items={previewQuery.data?.items ?? []} isLoading={previewQuery.isLoading} />
        </section>

        <section className="analysis-section">
          <div className="detail-board__lead">
            <h3>量化评估</h3>
          </div>
          <div className="render-actions">
            <button type="button" className="theme-toggle" onClick={evaluate} disabled={evaluateMutation.isPending}>
              开始评估
            </button>
          </div>
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
          {evaluateMutation.data ? (
            <p className="muted">
              已处理 {evaluateMutation.data.processed_count} 个材质
              {evaluateMutation.data.skipped.length > 0 ? `，跳过 ${evaluateMutation.data.skipped.length} 个` : ''}
            </p>
          ) : null}
          {evaluateMutation.error instanceof Error ? <p className="error-text">{evaluateMutation.error.message}</p> : null}
        </section>

        <section className="analysis-section">
          <div className="detail-board__lead">
            <h3>图像对比滑块</h3>
          </div>

          <div className="render-form-grid">
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
          </div>

          {sliderLeft?.preview_url && sliderRight?.preview_url ? (
            <>
              <div className="compare-stage">
                <img src={toBackendUrl(sliderRight.preview_url)} alt={sliderRight.name} className="compare-stage__image" />
                <div
                  className="compare-stage__overlay"
                  style={{
                    width: `${compareRatio}%`,
                    backgroundImage: `url(${toBackendUrl(sliderLeft.preview_url)})`,
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
            <p className="muted">当前没有可用于滑块对比的成对图片。</p>
          )}
        </section>

        <section className="analysis-section">
          <div className="detail-board__lead">
            <h3>材质选择</h3>
          </div>
          <div className="file-toolbar__actions">
            <button type="button" className="theme-toggle" onClick={() => setSelectedMaterials(baseMaterials.slice(0, 20))}>
              选前20个
            </button>
            <button type="button" className="theme-toggle" onClick={() => setSelectedMaterials([])}>
              清空
            </button>
          </div>
          <div className="file-list">
            {baseMaterials.map((material) => (
              <label key={material} className="file-item">
                <input type="checkbox" checked={selectedMaterials.includes(material)} onChange={() => toggleMaterial(material)} />
                <span>{material}</span>
              </label>
            ))}
          </div>
        </section>

        <section className="analysis-section">
          <div className="detail-board__lead">
            <h3>网格拼图</h3>
          </div>
          <div className="render-form-grid">
            <label className="field">
              <span>源图片集</span>
              <select value={gridSet} onChange={(event) => setGridSet(event.target.value as AnalysisImageSet)}>
                <option value="brdfs">GT / BRDF</option>
                <option value="fullbin">FullBin</option>
                <option value="npy">NPY</option>
              </select>
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
          <label className="toggle-field">
            <input type="checkbox" checked={gridShowNames} onChange={(event) => setGridShowNames(event.target.checked)} />
            <span>显示文件名</span>
          </label>
          <div className="render-actions">
            <button type="button" className="theme-toggle" onClick={generateGrid} disabled={gridMutation.isPending}>
              生成网格图
            </button>
          </div>
          {gridMutation.data?.item.preview_url ? (
            <img src={toBackendUrl(gridMutation.data.item.preview_url)} alt={gridMutation.data.item.name} className="analysis-output-image" />
          ) : null}
          {gridMutation.error instanceof Error ? <p className="error-text">{gridMutation.error.message}</p> : null}
        </section>

        <section className="analysis-section">
          <div className="detail-board__lead">
            <h3>对比拼图</h3>
          </div>
          <div className="render-form-grid">
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
              <input
                type="checkbox"
                checked={comparisonShowFilename}
                onChange={(event) => setComparisonShowFilename(event.target.checked)}
              />
              <span>显示文件名</span>
            </label>
          </div>
          <div className="render-actions">
            <button type="button" className="theme-toggle" onClick={generateComparison} disabled={comparisonMutation.isPending}>
              生成对比拼图
            </button>
          </div>
          {comparisonMutation.data?.item.preview_url ? (
            <img
              src={toBackendUrl(comparisonMutation.data.item.preview_url)}
              alt={comparisonMutation.data.item.name}
              className="analysis-output-image"
            />
          ) : null}
          {comparisonMutation.error instanceof Error ? <p className="error-text">{comparisonMutation.error.message}</p> : null}
        </section>
      </div>
    </section>
  )
}
