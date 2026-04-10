import { useMemo, useState } from 'react'

import { toBackendUrl } from '../lib/api'
import { compareAssetNamesByMaterial, compareAssetNamesByTimestampDesc, parseAssetName } from '../lib/fileNames'
import type { FileListItem } from '../types/api'
import { FeedbackPanel } from './FeedbackPanel'

type GalleryPreviewProps = {
  items: FileListItem[]
  isLoading: boolean
}

type GallerySortMode = 'time' | 'name'

export function GalleryPreview({ items, isLoading }: GalleryPreviewProps) {
  const [selectedImage, setSelectedImage] = useState<string | null>(null)
  const [zoomLevel, setZoomLevel] = useState<number>(3)
  const [sortMode, setSortMode] = useState<GallerySortMode>('time')

  const sortedItems = useMemo(() => {
    const nextItems = [...items]
    nextItems.sort((left, right) => {
      if (sortMode === 'name') {
        const materialCompare = compareAssetNamesByMaterial(left.name, right.name)
        if (materialCompare !== 0) {
          return materialCompare
        }
        return compareAssetNamesByTimestampDesc(left.name, right.name)
      }
      const timeCompare = compareAssetNamesByTimestampDesc(left.name, right.name)
      if (timeCompare !== 0) {
        return timeCompare
      }
      return compareAssetNamesByMaterial(left.name, right.name)
    })
    return nextItems
  }, [items, sortMode])

  const gridColumns =
    zoomLevel === 1 ? 'repeat(auto-fill, minmax(80px, 1fr))' : zoomLevel === 2 ? 'repeat(auto-fill, minmax(120px, 1fr))' : 'repeat(auto-fill, minmax(180px, 1fr))'

  return (
    <section className="gallery-panel">
      {selectedImage ? (
        <div className="fullscreen-modal" onClick={() => setSelectedImage(null)} title="点击关闭">
          <img src={selectedImage} alt="Detailed preview" className="fullscreen-modal__image" />
        </div>
      ) : null}

      <div className="gallery-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <span className="eyebrow" style={{ margin: 0 }}>输出预览</span>
          <span className="gallery-count">{sortedItems.length} 个结果</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <select value={sortMode} onChange={(event) => setSortMode(event.target.value as GallerySortMode)} className="select-input">
            <option value="time">按时间</option>
            <option value="name">按名称</option>
          </select>
          <input
            type="range"
            min="1"
            max="3"
            step="1"
            value={zoomLevel}
            onChange={(event) => setZoomLevel(Number(event.target.value))}
            style={{ width: '80px', accentColor: 'var(--accent)' }}
            title="缩放网格"
          />
        </div>
      </div>

      {isLoading ? <p className="muted">正在读取渲染输出...</p> : null}
      {!isLoading && sortedItems.length === 0 ? <FeedbackPanel title="暂无图片" message="任务完成后，最新输出会出现在这里。" tone="empty" compact /> : null}

      {sortedItems.length > 0 ? (
        <div className="gallery-grid" style={{ display: 'grid', gridTemplateColumns: gridColumns, gap: '8px' }}>
          {sortedItems.map((item, index) => {
            const parsedName = parseAssetName(item.name)
            return (
              <article key={item.path} className="gallery-item">
                <div className="gallery-item__thumb">
                  {item.preview_url ? (
                    <img
                      src={toBackendUrl(item.preview_url)}
                      alt={item.name}
                      className="gallery-item__image"
                      onClick={() => {
                        const url = toBackendUrl(item.preview_url)
                        if (url) {
                          setSelectedImage(url)
                        }
                      }}
                      style={{ cursor: 'zoom-in' }}
                    />
                  ) : (
                    <span>{String(index + 1).padStart(2, '0')}</span>
                  )}
                </div>
                <div className="gallery-item__meta" title={item.name} style={{ display: 'flex', flexDirection: 'column', gap: 2, padding: '0 4px' }}>
                  <strong style={{ wordBreak: 'break-word', fontSize: '0.85rem', lineHeight: '1.2', color: 'var(--text-strong)' }}>
                    {parsedName.materialName}
                  </strong>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    {parsedName.timestampDisplay ? <span>{parsedName.timestampDisplay}</span> : <span>-</span>}
                    <span>{Math.max(1, Math.round(item.size / 1024))} KB</span>
                  </div>
                </div>
              </article>
            )
          })}
        </div>
      ) : null}
    </section>
  )
}
