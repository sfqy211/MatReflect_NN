import type { FileListItem } from '../types/api'

type GalleryPreviewProps = {
  items: FileListItem[]
  isLoading: boolean
}

export function GalleryPreview({ items, isLoading }: GalleryPreviewProps) {
  return (
    <section className="gallery-panel">
      <div className="gallery-header">
        <div className="panel-head">
          <h2>输出画廊预览</h2>
        </div>
        <span className="gallery-count">{items.length} visible</span>
      </div>
      {isLoading ? <p className="muted">正在读取渲染输出...</p> : null}
      {!isLoading && items.length === 0 ? (
        <div className="empty-card">
          <strong>暂无图片</strong>
        </div>
      ) : null}
      {items.length > 0 ? (
        <div className="gallery-grid">
          {items.map((item, index) => (
            <article key={item.path} className="gallery-item">
              <div className="gallery-item__thumb">
                <span>{String(index + 1).padStart(2, '0')}</span>
              </div>
              <div className="gallery-item__meta">
                <strong>{item.name}</strong>
                <span>{Math.max(1, Math.round(item.size / 1024))} KB</span>
              </div>
            </article>
          ))}
        </div>
      ) : null}
    </section>
  )
}
