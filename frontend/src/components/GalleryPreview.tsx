import { useState } from 'react'
import type { FileListItem } from '../types/api'
import { toBackendUrl } from '../lib/api'
import { FeedbackPanel } from './FeedbackPanel'

type GalleryPreviewProps = {
  items: FileListItem[]
  isLoading: boolean
}

function formatDisplayName(name: string) {
  // Remove the timestamp suffix like _13_204338
  const withoutTimestamp = name.replace(/_\d{1,2}_\d{6}/, '')
  return withoutTimestamp
}

export function GalleryPreview({ items, isLoading }: GalleryPreviewProps) {
  const [selectedImage, setSelectedImage] = useState<string | null>(null)

  return (
    <section className="gallery-panel">
      {selectedImage && (
        <div 
          className="fullscreen-modal" 
          onClick={() => setSelectedImage(null)}
          title="点击关闭"
        >
          <img src={selectedImage} alt="Detailed preview" className="fullscreen-modal__image" />
        </div>
      )}
      <div className="gallery-header">
        <div className="panel-head">
          <h2>输出画廊预览</h2>
        </div>
        <span className="gallery-count">{items.length} visible</span>
      </div>
      {isLoading ? <p className="muted">正在读取渲染输出...</p> : null}
      {!isLoading && items.length === 0 ? (
        <FeedbackPanel title="暂无图片" message="任务完成后，最新输出会出现在这里。" tone="empty" compact />
      ) : null}
      {items.length > 0 ? (
        <div className="gallery-grid">
          {items.map((item, index) => (
            <article key={item.path} className="gallery-item">
              <div className="gallery-item__thumb">
                {item.preview_url ? (
                  <img 
                    src={toBackendUrl(item.preview_url)} 
                    alt={item.name} 
                    className="gallery-item__image"
                    onClick={() => {
                      const url = toBackendUrl(item.preview_url);
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
                <strong style={{ wordBreak: 'break-word', fontSize: '0.9rem', lineHeight: '1.2' }}>
                  {formatDisplayName(item.name)}
                </strong>
                <span>{Math.max(1, Math.round(item.size / 1024))} KB</span>
              </div>
            </article>
          ))}
        </div>
      ) : null}
    </section>
  )
}
