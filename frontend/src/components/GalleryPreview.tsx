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
          <span className="eyebrow">Render Outputs</span>
          <h2>输出画廊预览</h2>
          <p>这里只展示最近索引结果。等真正的渲染任务接入后，这里会和任务状态、日志及分析入口联动。</p>
        </div>
        <span className="gallery-count">{items.length} visible</span>
      </div>
      {isLoading ? <p className="muted">正在读取渲染输出...</p> : null}
      {!isLoading && items.length === 0 ? (
        <div className="empty-card">
          <strong>当前还没有可展示图片</strong>
          <p>下一阶段会把渲染任务、日志和画廊联动起来，这里现在主要验证文件 API 和新版布局结构。</p>
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
