import { useMemo, useState } from 'react'

import { FeedbackPanel } from './FeedbackPanel'
import type { FileListItem } from '../types/api'

type FileSelectionModalProps = {
  title: string
  isOpen: boolean
  onClose: () => void
  items: FileListItem[]
  selectedItems: string[]
  onSelectionChange: (selected: string[]) => void
  error?: Error | null
  emptyMessage?: string
  searchPlaceholder?: string
  formatName?: (name: string) => string
  presets?: Array<{ label: string; filter: (items: FileListItem[]) => string[] }>
  multiSelect?: boolean
}

export function FileSelectionModal({
  title,
  isOpen,
  onClose,
  items,
  selectedItems,
  onSelectionChange,
  error,
  emptyMessage = '没有可用的文件。',
  searchPlaceholder = '搜索文件...',
  formatName = (name) => name,
  presets = [],
  multiSelect = true,
}: FileSelectionModalProps) {
  const [search, setSearch] = useState('')

  const filteredItems = useMemo(() => {
    if (!search.trim()) {
      return items
    }
    const lowerSearch = search.toLowerCase()
    return items.filter((item) => item.name.toLowerCase().includes(lowerSearch))
  }, [items, search])

  const toggleItem = (name: string) => {
    if (!multiSelect) {
      onSelectionChange([name])
      // onClose() // optionally close immediately on single select
      return
    }
    onSelectionChange(
      selectedItems.includes(name)
        ? selectedItems.filter((item) => item !== name)
        : [...selectedItems, name]
    )
  }

  if (!isOpen) {
    return null
  }

  return (
    <div className="fullscreen-modal" onClick={onClose} style={{ cursor: 'default' }}>
      <div 
        className="modal-content" 
        onClick={(e) => e.stopPropagation()}
        style={{
          width: '90vw',
          maxWidth: '1000px',
          height: '85vh',
          background: 'var(--surface)',
          borderRadius: '8px',
          border: '1px solid var(--border)',
          display: 'flex',
          flexDirection: 'column',
          boxShadow: '0 24px 64px rgba(0, 0, 0, 0.4)',
          overflow: 'hidden'
        }}
      >
        <div className="modal-header" style={{ padding: '20px 24px', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h2 style={{ margin: 0, fontSize: '1.4rem' }}>{title} {multiSelect && <span style={{ fontSize: '1rem', color: 'var(--text-muted)', marginLeft: '12px', fontWeight: 'normal' }}>已选 {selectedItems.length} 项</span>}</h2>
          <button type="button" onClick={onClose} style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', fontSize: '1.5rem', cursor: 'pointer', padding: '4px' }}>
            &times;
          </button>
        </div>
        
        <div className="modal-body" style={{ padding: '20px 24px', flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0 }}>
          <div className="file-toolbar" style={{ marginBottom: '20px' }}>
            <input
              type="search"
              className="search-input"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder={searchPlaceholder}
            />
            {multiSelect && (
              <div className="file-toolbar__actions">
                <button type="button" className="theme-toggle" onClick={() => onSelectionChange(items.map((item) => item.name))}>
                  全选
                </button>
                {presets.map((preset) => (
                  <button key={preset.label} type="button" className="theme-toggle" onClick={() => onSelectionChange(preset.filter(items))}>
                    {preset.label}
                  </button>
                ))}
                <button type="button" className="theme-toggle" onClick={() => onSelectionChange([])}>
                  清空
                </button>
              </div>
            )}
          </div>
          
          <div className="file-list" style={{ flex: 1, minHeight: 0, overflowY: 'auto', alignContent: 'start', margin: 0 }}>
            {error instanceof Error ? (
              <FeedbackPanel title="列表读取失败" message={error.message} tone="error" compact />
            ) : null}
            {filteredItems.map((item) => (
              <label
                key={item.path}
                className="file-item"
                onClick={(event) => {
                  event.preventDefault()
                  toggleItem(item.name)
                }}
              >
                <input type={multiSelect ? "checkbox" : "radio"} checked={selectedItems.includes(item.name)} readOnly />
                <span className="file-item__name" title={item.name}>{formatName(item.name)}</span>
              </label>
            ))}
            {!error && items.length === 0 ? (
              <FeedbackPanel title="没有文件" message={emptyMessage} tone="empty" compact />
            ) : null}
            {!error && items.length > 0 && filteredItems.length === 0 ? (
              <FeedbackPanel title="无匹配项" message="没有找到符合搜索条件的文件。" tone="empty" compact />
            ) : null}
          </div>
        </div>

        <div className="modal-footer" style={{ padding: '16px 24px', borderTop: '1px solid var(--border)', display: 'flex', justifyContent: 'flex-end', background: 'color-mix(in oklab, var(--surface-soft) 40%, transparent)' }}>
           <button type="button" className="theme-toggle render-actions--primary" onClick={onClose} style={{ minWidth: '120px' }}>
              完成选择
           </button>
        </div>
      </div>
    </div>
  )
}
