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

      <div className="gallery-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div className="panel-head">
          <h2>输出画廊预览</h2>
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
          <span className="gallery-count">{sortedItems.length} visible</span>
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
                <div className="gallery-item__meta" title={item.name}>
                  <strong style={{ wordBreak: 'break-word', fontSize: '0.9rem', lineHeight: '1.2' }}>{parsedName.materialName}</strong>
                  {parsedName.timestampDisplay ? <span className="gallery-item__timestamp">{parsedName.timestampDisplay}</span> : null}
                  <span>{Math.max(1, Math.round(item.size / 1024))} KB</span>
                </div>
              </article>
            )
          })}
        </div>
      ) : null}
    </section>
  )
}
